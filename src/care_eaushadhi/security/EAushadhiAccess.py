from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler

from care_eaushadhi.security.EAushadhiPermissions import EAushadhiPermissions


class EAushadhiAccess(AuthorizationHandler):
    """
    Authorization handler for eAushadhi integration permissions
    """

    def can_use_eaushadhi_integration(self, user, facility):
        """
        Check if the user can use (view/search) eAushadhi integration in the facility
        """
        return self.check_permission_in_facility_organization(
            [EAushadhiPermissions.can_use_eaushadhi_integration.name],
            user,
            facility=facility,
        )

    def can_manage_eaushadhi_integration(self, user, facility):
        """
        Check if the user can manage (create/update) eAushadhi mappings in the facility
        """
        return self.check_permission_in_facility_organization(
            [EAushadhiPermissions.can_manage_eaushadhi_integration.name],
            user,
            facility=facility,
        )

AuthorizationController.register_internal_controller(EAushadhiAccess)
