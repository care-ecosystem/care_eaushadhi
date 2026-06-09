import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    FACILITY_ADMIN_ROLE,
    PHARMACIST_ROLE,
)


class EAushadhiPermissions(enum.Enum):
    can_use_eaushadhi_integration = Permission(
        "Can Use eAushadhi Integration In Facility",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
