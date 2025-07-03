from datetime import datetime
from sqlmodel import Field, SQLModel


class EmailVerificationToken(SQLModel, table=True):
    """Table for single-use email verification tokens."""

    __tablename__: str = "email_verification_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(unique=True, max_length=128, index=True)
    issued_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)
    used: bool = Field(default=False, nullable=False)
