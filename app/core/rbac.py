from core.models import Permission
from accounts.models import UserRole


class RBACEngine:

    @staticmethod
    def has_permission(user, module_name, action):

        if not user.is_authenticated:
            return False

        try:
            role = user.userrole.role
        except UserRole.DoesNotExist:
            return False

        return Permission.objects.filter(
            role=role,
            module__name=module_name,
            action=action
        ).exists()
