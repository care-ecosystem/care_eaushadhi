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
        "View and search eAushadhi data",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, PHARMACIST_ROLE, ADMIN_ROLE],
    )
    can_manage_eaushadhi_integration = Permission(
        "Can Manage eAushadhi Integration In Facility",
        "Create and update eAushadhi mappings",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )
