from passlib.context import CryptContext

# =========================
# Password Hashing Context
# =========================
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


# =========================
# Hash Password
# =========================
def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2.
    """
    return pwd_context.hash(password)


# =========================
# Verify Password
# =========================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


# =========================
# Check if Rehash Needed
# =========================
def needs_rehash(hashed_password: str) -> bool:
    """
    Detect if hash algorithm settings changed.
    Allows seamless upgrades later.
    """
    return pwd_context.needs_update(hashed_password)