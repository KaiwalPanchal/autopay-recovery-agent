"""Customer management and domain logic service."""

from typing import List, Optional, Dict, Any
from .database import db
from .models import Customer, CustomerStatusEnum, RecoveryStateEnum


class CustomerService:
    @staticmethod
    def list_customers(status_filter: Optional[str] = None) -> List[Customer]:
        all_customers = db.get_all_customers()
        if status_filter:
            return [c for c in all_customers if c.status.lower() == status_filter.lower()]
        return all_customers

    @staticmethod
    def get_customer_by_id(customer_id: str) -> Optional[Customer]:
        return db.get_customer(customer_id)

    @staticmethod
    def get_customers_requiring_recovery() -> List[Customer]:
        """Identifies customers who are delinquent or pending recovery."""
        active_delinquent_statuses = {
            CustomerStatusEnum.PAYMENT_FAILED.value,
            CustomerStatusEnum.UNREACHABLE.value,
            CustomerStatusEnum.IN_PROGRESS.value,
        }
        return [c for c in db.get_all_customers() if c.status in active_delinquent_statuses]

    @staticmethod
    def reset_dataset() -> List[Customer]:
        return db.reset_to_seed()


customer_service = CustomerService()
