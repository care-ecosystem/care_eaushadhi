from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler

from care_eaushadhi.security.EAushadhiPermissions import EAushadhiPermissions


class EAushadhiAccess(AuthorizationHandler):
    """
    Check if the user has permission to use eAushadhi integration in the facility
    """

    def can_use_eaushadhi_integration(self, user, facility):
        return self.check_permission_in_facility_organization(
            [EAushadhiPermissions.can_use_eaushadhi_integration.name],
            user,
            facility=facility,
        )

AuthorizationController.register_internal_controller(EAushadhiAccess)
