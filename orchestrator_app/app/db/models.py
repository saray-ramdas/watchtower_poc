from datetime import datetime

from sqlalchemy import DECIMAL, Integer, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CustomerLotteryProfile(Base):
    __tablename__ = "customer_lottery_profile"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False)
    years_in_bank: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
