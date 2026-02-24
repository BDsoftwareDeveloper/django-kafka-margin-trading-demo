from rest_framework.permissions import BasePermission
from core.rbac import RBACEngine


class RBACPermission(BasePermission):

    module = None

    ACTION_MAP = {
        "list": "VIEW",
        "retrieve": "VIEW",
        "create": "CREATE",
        "update": "UPDATE",
        "partial_update": "UPDATE",
        "destroy": "DELETE",
        "force_sell": "FORCE_SELL",
        "loan_eligibility": "VIEW",
    }

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        action = self.ACTION_MAP.get(view.action)

        if not action:
            return False

        return RBACEngine.has_permission(
            request.user,
            self.module,
            action
        )


class ClientPermission(RBACPermission):
    module = "CLIENT"


class InstrumentPermission(RBACPermission):
    module = "INSTRUMENT"


class PortfolioPermission(RBACPermission):
    module = "PORTFOLIO"


class MarginLoanPermission(RBACPermission):
    module = "MARGIN_LOAN"


class AuditPermission(RBACPermission):
    module = "AUDIT"
