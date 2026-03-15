from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.models.all_models import (
    Notice, NoticeAttachment, NoticeDelivery, DeliveryChannel, 
    DeliveryStatus, Case, Meeting, MeetingStatus, Document, PartyType
)
from app.schemas.schemas import NoticeCreate
import uuid
from datetime import datetime, timedelta
import logging
from typing import List, Optional
import os
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class NoticeService:
    @staticmethod
    async def _send_whatsapp(target: str, key: str, notice_id: uuid.UUID):
        # Implementation for WhatsApp
        logger.info(f"[WHATSAPP] Notice {notice_id} dispatched to {target} using key {key[:4]}...")
        return True

    @staticmethod
    async def _send_sms(target: str, key: str, notice_id: uuid.UUID):
        # Implementation for SMS
        logger.info(f"[SMS] Notice {notice_id} dispatched to {target} using key {key[:4]}...")
        return True

    @staticmethod
    def _send_email_sync(target: str, subject: str, body: str):
        host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        sender = os.getenv("SMTP_FROM", user)

        if not user or not password:
            logger.error("SMTP credentials not configured")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = target
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(host, port)
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    @classmethod
    async def _send_email(cls, target: str, key: str, notice_id: uuid.UUID, content: dict, notice_no: int):
        # Full Implementation for Email
        subject = f"Legal Notice Update - #{notice_no}"
        body = f"Hello,\n\nA legal notice (N-{notice_no}) has been generated for your case.\n\n"
        if content.get("custom_message"):
            body += f"Message: {content['custom_message']}\n\n"
        if content.get("portal_link"):
            body += f"View Details: {content['portal_link']}\n"
        if content.get("meeting_url"):
            body += f"Meeting Link: {content['meeting_url']}\n"
        
        body += "\nThank you."
        
        # Run sync smtplib in a thread
        return await asyncio.to_thread(cls._send_email_sync, target, subject, body)

    @staticmethod
    async def dispatch_notice(db: AsyncSession, notice: Notice, case: Case, delivery_channels: List[DeliveryChannel]):
        # Mocking delivery logic - in future use os.getenv("TWILIO_SID"), etc.
        import os
        whatsapp_key = os.getenv("WHATSAPP_API_KEY", "mock_key")
        sms_key = os.getenv("SMS_API_KEY", "mock_key")
        email_key = os.getenv("EMAIL_API_KEY", "mock_key")

        applicants = [p for p in case.parties if p.party_type == PartyType.applicant]
        for applicant in applicants:
            for channel in delivery_channels:
                target = applicant.email if channel == DeliveryChannel.email else (applicant.phone or applicant.phone_2)
                
                if not target:
                    logger.warning(f"No target address for channel {channel} for party {applicant.name}")
                    continue

                success = False
                if channel == DeliveryChannel.whatsapp:
                    success = await NoticeService._send_whatsapp(target, whatsapp_key, notice.id)
                elif channel == DeliveryChannel.sms:
                    success = await NoticeService._send_sms(target, sms_key, notice.id)
                elif channel == DeliveryChannel.email:
                    success = await NoticeService._send_email(target, email_key, notice.id, notice.content, notice.notice_no)

                delivery = NoticeDelivery(
                    notice_id=notice.id,
                    channel=channel,
                    to_address=target,
                    status=DeliveryStatus.sent if success else DeliveryStatus.failed,
                    sent_at=datetime.utcnow() if success else None,
                    provider_message_id=str(uuid.uuid4()) if success else None
                )
                db.add(delivery)
                logger.info(f"Dispatched notice {notice.id} via {channel} to {target}. Status: {'Sent' if success else 'Failed'}")

    @classmethod
    async def create_notice(cls, db: AsyncSession, notice_in: NoticeCreate, current_user_id: uuid.UUID) -> Notice:
        # 1. Fetch case and parties
        case_res = await db.execute(
            select(Case).where(Case.id == notice_in.case_id).options(selectinload(Case.parties))
        )
        case = case_res.scalar_one_or_none()
        if not case:
            raise Exception("Case not found")

        # 1b. Auto-calculate notice number (User requested separate numbering)
        from sqlalchemy import func
        notice_count_res = await db.execute(
            select(func.count(Notice.id)).where(Notice.case_id == notice_in.case_id)
        )
        next_notice_no = notice_count_res.scalar() + 1

        # 2. Content Generation Logic
        notice_content = notice_in.content or {}
        
        if notice_in.include_portal_link:
            portal_token = str(uuid.uuid4())
            portal_link = f"http://localhost:5173/portal/{portal_token}"
            notice_content.update({
                "portal_token": portal_token,
                "portal_link": portal_link
            })

        if notice_in.include_meeting_link:
            meeting_id = uuid.uuid4()
            meeting_url = f"http://localhost:5173/meeting/{meeting_id}"
            notice_content.update({
                "meeting_id": str(meeting_id),
                "meeting_url": meeting_url
            })
            
            # Create meeting record
            meeting = Meeting(
                id=meeting_id,
                case_id=case.id,
                created_by=current_user_id,
                scheduled_at=datetime.utcnow() + timedelta(days=7),
                meet_url=meeting_url,
                portal_url=notice_content.get("portal_link"),
                status=MeetingStatus.scheduled,
                notes=f"Virtual hearing for Notice N-{notice_in.notice_no}. {notice_content.get('custom_message', '')}"
            )
            db.add(meeting)

        # 3. Create Notice
        notice = Notice(
            case_id=notice_in.case_id,
            notice_no=next_notice_no, # Use auto-calculated number
            notice_type=notice_in.notice_type,
            content=notice_content,
            created_by=current_user_id,
            status="draft"
        )
        db.add(notice)
        await db.flush()

        # 4. Handle Attachments
        if notice_in.attachment_ids:
            for doc_id in notice_in.attachment_ids:
                attachment = NoticeAttachment(
                    notice_id=notice.id,
                    document_id=doc_id
                )
                db.add(attachment)

        # 5. Handle Delivery
        await cls.dispatch_notice(db, notice, case, notice_in.delivery_channels)

        await db.commit()
        
        # Load relationships for response
        res = await db.execute(
            select(Notice)
            .where(Notice.id == notice.id)
            .options(
                selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
                selectinload(Notice.case),
                selectinload(Notice.deliveries)
            )
        )
        return res.scalar_one()

    @classmethod
    async def resend_notice(cls, db: AsyncSession, notice_id: uuid.UUID, channel: Optional[DeliveryChannel] = None) -> Notice:
        notice_res = await db.execute(
            select(Notice).where(Notice.id == notice_id).options(
                selectinload(Notice.case).selectinload(Case.parties),
                selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
                selectinload(Notice.deliveries)
            )
        )
        notice = notice_res.scalar_one_or_none()
        if not notice:
            raise Exception("Notice not found")
        
        if channel:
            channels = [channel]
        else:
            # We assume original channels should be used or we could take them as input
            # For simple resend, we'll re-dispatch to all channels that were previously attempted or just use default.
            # Let's get unique channels from previous deliveries
            delivery_res = await db.execute(select(NoticeDelivery.channel).where(NoticeDelivery.notice_id == notice_id).distinct())
            channels = [r[0] for r in delivery_res.all()]
            if not channels:
                channels = [DeliveryChannel.sms] # Fallback

        await cls.dispatch_notice(db, notice, notice.case, channels)
        await db.commit()
        
        # Return refreshed notice with attachments
        res = await db.execute(
            select(Notice)
            .where(Notice.id == notice.id)
            .options(
                selectinload(Notice.attachments).selectinload(NoticeAttachment.document),
                selectinload(Notice.case),
                selectinload(Notice.deliveries)
            )
        )
        return res.scalar_one()

notice_service = NoticeService()
