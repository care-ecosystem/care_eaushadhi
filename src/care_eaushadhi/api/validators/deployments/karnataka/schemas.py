"""Pydantic schemas for the Karnataka HMIS instinward API.

CONFIRMED — holds for every row across multiple sample responses
OBSERVED — only one value seen so far; treated as free-form
GUESS — extrapolated from field name; not yet validated against data
"""

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)



InwardNo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^INI/WH/\d{4}-\d{2}/\d{6}/\d+$",
    ),
]

InstituteId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$"),
]
"""6-digit zero-padded institute identifier. CONFIRMED."""

UnitPackStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^\d+(?:[xX]\d+[a-zA-Z]*)+$",
    ),
]
"""Multi-dimensional pack size notation. OBSERVED: all samples use "1x10x10"."""

DrugId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^(?:[DM]\d{5}|\d+\.\d+\.\d+)$",
    ),
]
"""Drug identifier in two formats. CONFIRMED across samples."""

BatchNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
]
"""Batch number. OBSERVED: free-form string with length bounds."""

NonEmptyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
"""Non-empty string."""


# =========================================================================
# Enumerations
# =========================================================================

class InstituteType(str, Enum):
    """Karnataka public-health facility classifications."""

    # ---- CONFIRMED ----
    CHC = "CHC"  # Community Health Centre
    TLH = "TLH"  # Taluk Hospital

    # ---- GUESS (plausible but unverified) ----
    PHC = "PHC"  # Primary Health Centre
    DH = "DH"  # District Hospital
    SDH = "SDH"  # Sub-divisional Hospital
    GH = "GH"  # General Hospital
    SC = "SC"  # Sub-Centre
    UPHC = "UPHC"  # Urban PHC
    UCHC = "UCHC"  # Urban CHC
    WH = "WH"  # Warehouse
    DLH = "DLH"  # District Level Hospital


class YesNo(str, Enum):
    """YES/NO flag for NotofStandard field."""

    YES = "YES"
    NO = "NO"

    def as_bool(self) -> bool:
        """Convert to Python boolean."""
        return self is YesNo.YES


class InventoryItem(BaseModel):
    """A single inwarded stock line item from Karnataka eAushadhi API."""

    sl_no: int = Field(alias="Sl_No", ge=1)
    inwardno: InwardNo
    instituteid: InstituteId
    institute_name: NonEmptyStr = Field(alias="Institute_name")
    institute_type: InstituteType = Field(alias="InstituteType")
    receipt_date: date = Field(alias="Receipt_Date")
    batch_number: BatchNumber = Field(alias="Batch_number")
    mfg_date: date = Field(alias="Mfg_date")
    exp_date: date = Field(alias="Exp_date")
    quantity_in_pack: int = Field(alias="Quantity_In_Pack", ge=0)
    unit_pack: UnitPackStr = Field(alias="UnitPack")
    quantity_in_units: int = Field(alias="Quantity_In_Units", ge=0)
    available_quantity: int = Field(alias="Available_quantity", ge=0)
    warehouse_name: NonEmptyStr = Field(alias="Warehouse_name")
    drug_id: DrugId = Field(alias="Drug_id")
    drug_name: NonEmptyStr = Field(alias="Drug_name")
    not_of_standard: YesNo = Field(alias="NotofStandard")
    dose: NonEmptyStr = Field(alias="Dose")

    model_config = {
        "populate_by_name": True,
        "str_strip_whitespace": True,
        "use_enum_values": False,
    }

    @field_validator("drug_name", "dose", "institute_name", mode="before")
    @classmethod
    def _collapse_whitespace(cls, v: object) -> object:
        """Collapse \\r\\n and runs of spaces in source data."""
        if isinstance(v, str):
            return " ".join(v.split())
        return v

    @model_validator(mode="after")
    def _check_inwardno_matches_institute(self) -> "InventoryItem":
        """CONFIRMED: inwardno institute segment must equal instituteid."""
        segments = self.inwardno.split("/")
        if len(segments) >= 4 and segments[3] != self.instituteid:
            msg = (
                f"inwardno institute segment {segments[3]!r} does not match "
                f"instituteid {self.instituteid!r}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_dates(self) -> "InventoryItem":
        """Validate date ordering: mfg_date < exp_date, receipt_date >= mfg_date."""
        if self.mfg_date >= self.exp_date:
            msg = (
                f"Mfg_date {self.mfg_date} must be before "
                f"Exp_date {self.exp_date}"
            )
            raise ValueError(msg)

        if self.receipt_date < self.mfg_date:
            msg = (
                f"Receipt_Date {self.receipt_date} cannot be before "
                f"Mfg_date {self.mfg_date}"
            )
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def _check_quantities(self) -> "InventoryItem":
        """Validate quantity relationships: available <= in_pack, units = pack * units_per_pack."""
        if self.available_quantity > self.quantity_in_pack:
            msg = (
                f"Available_quantity ({self.available_quantity}) cannot exceed "
                f"Quantity_In_Pack ({self.quantity_in_pack})"
            )
            raise ValueError(msg)

        expected = self.quantity_in_pack * self.units_per_pack
        if expected != self.quantity_in_units:
            msg = (
                f"Quantity_In_Units ({self.quantity_in_units}) does not match "
                f"Quantity_In_Pack ({self.quantity_in_pack}) * units_per_pack "
                f"({self.units_per_pack}) = {expected}"
            )
            raise ValueError(msg)

        return self

    @property
    def units_per_pack(self) -> int:
        """Product of numeric components in UnitPack.

        Examples:
          - "1x10x10" -> 100
          - "1x1" -> 1
          - "10x5ml" -> 50 (ml is stripped)
        """
        total = 1
        for chunk in self.unit_pack.replace("X", "x").split("x"):
            digits = "".join(c for c in chunk if c.isdigit())
            if digits:
                total *= int(digits)
        return total

    @property
    def is_expired(self) -> bool:
        """Check if item has passed its expiry date."""
        return self.exp_date < date.today()


class InwardRequest(BaseModel):
    """Request body for eAushadhi instinward endpoint."""

    inward_date: date = Field(alias="InwardDate")

    model_config = {"populate_by_name": True}

    @field_validator("inward_date", mode="before")
    @classmethod
    def _parse_ddmmyyyy(cls, v: object) -> object:
        """Parse DD/MM/YYYY format from string."""
        if isinstance(v, str):
            from datetime import datetime

            return datetime.strptime(v, "%d/%m/%Y").date()
        return v

    def serialize(self) -> dict[str, str]:
        """Render body in the format the API expects."""
        return {"InwardDate": self.inward_date.strftime("%d/%m/%Y")}