"""
Pydantic data models for the INGRES groundwater data schema.
These enforce strict typing and domain constraints on all ingested data.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class WellMetadata(BaseModel):
    """Represents a groundwater monitoring well station (CGWB/NWIC)."""
    well_id: str = Field(..., description="Unique station code, e.g. GW_RJ_001")
    state: str = Field(..., min_length=2)
    district: str
    block: str = Field(default="")
    latitude: float = Field(..., ge=6.0, le=38.0,
                            description="Decimal degrees — India bounds")
    longitude: float = Field(..., ge=68.0, le=98.0,
                             description="Decimal degrees — India bounds")
    well_type: Literal["open_well", "piezometer", "borewell", "dug_well"]
    aquifer_type: Optional[Literal["unconfined", "confined", "semi-confined"]] = None
    depth_mbgl: Optional[float] = Field(
        None, ge=0, description="Total depth in meters below ground level"
    )
    installation_year: Optional[int] = Field(None, ge=1950, le=2025)
    data_source: str = "CGWB-NWIC"

    @field_validator("state")
    @classmethod
    def title_case_state(cls, v: str) -> str:
        return v.strip().title()


class GroundwaterLevel(BaseModel):
    """A single water-level measurement record."""
    record_id: str
    well_id: str
    measurement_date: date
    season: Literal["pre_monsoon", "post_monsoon", "rabi", "kharif"]
    depth_to_water_mbgl: Optional[float] = Field(
        None, description="Depth to water table in mbgl; None = missing/incomplete"
    )
    water_level_mbsl: Optional[float] = Field(
        None, description="Water level in metres below sea level"
    )
    measurement_method: Literal["manual", "telemetry", "estimated"] = "manual"
    data_quality_flag: Literal["good", "suspect", "missing", "estimated"] = "good"
    remarks: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_level(self) -> "GroundwaterLevel":
        if self.depth_to_water_mbgl is None and self.water_level_mbsl is None:
            # Acceptable — marks an incomplete record
            self.data_quality_flag = "missing"
        return self


class GroundwaterQuality(BaseModel):
    """Chemical quality parameters for a groundwater sample."""
    record_id: str
    well_id: str
    sample_date: date
    ph: Optional[float] = Field(None, ge=0.0, le=14.0)
    tds_mg_l: Optional[float] = Field(None, ge=0, description="Total Dissolved Solids mg/L")
    nitrate_mg_l: Optional[float] = Field(None, ge=0)
    fluoride_mg_l: Optional[float] = Field(None, ge=0)
    arsenic_ug_l: Optional[float] = Field(None, ge=0)
    iron_mg_l: Optional[float] = Field(None, ge=0)
    hardness_mg_l: Optional[float] = Field(None, ge=0)
    potability: Optional[Literal["potable", "non_potable", "marginal", "unknown"]] = None
    lab_id: Optional[str] = None

    @model_validator(mode="after")
    def derive_potability(self) -> "GroundwaterQuality":
        """Auto-derive potability using BIS 10500:2012 limits if not provided."""
        if self.potability is not None:
            return self
        violations = []
        if self.tds_mg_l is not None and self.tds_mg_l > 500:
            violations.append("tds")
        if self.fluoride_mg_l is not None and self.fluoride_mg_l > 1.5:
            violations.append("fluoride")
        if self.nitrate_mg_l is not None and self.nitrate_mg_l > 45:
            violations.append("nitrate")
        if self.arsenic_ug_l is not None and self.arsenic_ug_l > 10:
            violations.append("arsenic")
        if violations:
            self.potability = "non_potable"
        elif all(v is None for v in [self.tds_mg_l, self.fluoride_mg_l,
                                      self.nitrate_mg_l, self.arsenic_ug_l]):
            self.potability = "unknown"
        else:
            self.potability = "potable"
        return self


class AssessmentUnit(BaseModel):
    """GEC-2015 groundwater assessment unit (block/taluk level)."""
    unit_id: str
    state: str
    district: str
    block_taluk: str
    annual_gw_recharge_mcm: Optional[float] = Field(
        None, ge=0, description="Million Cubic Metres per year"
    )
    extractable_gw_mcm: Optional[float] = Field(None, ge=0)
    total_extraction_mcm: Optional[float] = Field(None, ge=0)
    stage_of_extraction_pct: Optional[float] = Field(
        None, ge=0, description=">100 = over-exploited"
    )
    category: Optional[Literal[
        "safe", "semi_critical", "critical", "over_exploited", "saline"
    ]] = None
    assessment_year: int = Field(..., ge=2000, le=2025)
    methodology: str = "GEC-2015"

    @model_validator(mode="after")
    def derive_category(self) -> "AssessmentUnit":
        """Auto-derive category from stage_of_extraction_pct if not provided."""
        if self.category is not None or self.stage_of_extraction_pct is None:
            return self
        pct = self.stage_of_extraction_pct
        if pct > 100:
            self.category = "over_exploited"
        elif pct > 90:
            self.category = "critical"
        elif pct > 70:
            self.category = "semi_critical"
        else:
            self.category = "safe"
        return self

