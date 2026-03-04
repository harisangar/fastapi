# from sqlalchemy import String, Boolean
# from sqlalchemy.orm import Mapped, mapped_column
# from sqlalchemy import Index

# from app.db.models.base_model import BaseModel


# class User(BaseModel):
#     __tablename__ = "users2"

#     # =========================
#     # Auth Fields
#     # =========================
#     email: Mapped[str] = mapped_column(
#         String(255),
#         unique=True,
#         index=True,
#         nullable=False,
#     )

#     hashed_password: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#     )

#     # =========================
#     # Account Status
#     # =========================
#     is_active: Mapped[bool] = mapped_column(
#         Boolean,
#         default=True,
#         nullable=False,
#     )

#     is_verified: Mapped[bool] = mapped_column(
#         Boolean,
#         default=False,
#         nullable=False,
#     )

#     is_superuser: Mapped[bool] = mapped_column(
#         Boolean,
#         default=False,
#         nullable=False,
#     )

#     # =========================
#     # Optional Profile Fields
#     # =========================
#     full_name: Mapped[str | None] = mapped_column(
#         String(255),
#         nullable=True,
#     )

#     # =========================
#     # Indexes (Performance)
#     # =========================
#     __table_args__ = (
#         Index("ix_users_email_active2", "email", "is_active"),
#     )