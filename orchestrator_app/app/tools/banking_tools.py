from typing import Optional

from sqlalchemy.orm import Session

from ..db.models import CustomerLotteryProfile


def get_customer_by_user_id(db: Session, user_id: str) -> Optional[CustomerLotteryProfile]:
	"""
	Retrieve a CustomerLotteryProfile by user_id. Returns None if not found.
	"""
	return (
		db.query(CustomerLotteryProfile)
		.filter(CustomerLotteryProfile.user_id == user_id)
		.first()
	)


def get_customer_balance_by_user_id(db: Session, user_id: str) -> Optional[float]:
	"""
	Retrieve the customer's savings balance by user_id.
	"""
	customer = get_customer_by_user_id(db, user_id)
	if customer is None:
		return None
	return float(customer.balance)


def get_customer_years_in_bank_by_user_id(db: Session, user_id: str) -> Optional[int]:
	"""
	Retrieve the customer's years in bank by user_id.
	"""
	customer = get_customer_by_user_id(db, user_id)
	if customer is None:
		return None
	return customer.years_in_bank

