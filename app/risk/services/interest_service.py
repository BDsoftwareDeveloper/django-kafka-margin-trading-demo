from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from core.models import MarginLoan, AuditLog


class InterestAccrualService:

    @staticmethod
    @transaction.atomic
    def accrue_daily_interest():

        today = timezone.now().date()

        loans = (
            MarginLoan.objects
            .select_for_update()
            .filter(status="ACTIVE")
        )

        for loan in loans:

            # -----------------------------------------
            # Skip if no principal
            # -----------------------------------------
            if loan.principal_amount <= 0:
                continue

            # -----------------------------------------
            # Determine accrual start date
            # -----------------------------------------
            last_date = loan.last_accrual_date

            if last_date is None:
                last_date = loan.opened_at.date()

            days_diff = (today - last_date).days

            # Already accrued today
            if days_diff <= 0:
                continue

            daily_rate = (
                loan.interest_rate / Decimal("365")
            )

            total_interest = Decimal("0.00")

            # -----------------------------------------
            # Accrue for missed days
            # -----------------------------------------
            for _ in range(days_diff):

                daily_interest = (
                    loan.principal_amount * daily_rate
                ).quantize(Decimal("0.01"), ROUND_HALF_UP)

                if daily_interest > 0:
                    total_interest += daily_interest

            if total_interest <= 0:
                continue

            # -----------------------------------------
            # Update loan
            # -----------------------------------------
            loan.accrued_interest += total_interest
            loan.last_accrual_date = today
            loan.save(update_fields=[
                "accrued_interest",
                "last_accrual_date",
            ])

            # -----------------------------------------
            # Audit log
            # -----------------------------------------
            AuditLog.log_event(
                event_type="DAILY_INTEREST_ACCRUED",
                client=loan.client,
                details={
                    "loan_id": loan.id,
                    "days": days_diff,
                    "interest_added": str(total_interest),
                },
            )
