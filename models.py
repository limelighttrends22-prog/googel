"""Input contracts and bounded reporting periods."""

from datetime import date, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date
    end: date

    @model_validator(mode="after")
    def valid(self):
        if self.end < self.start or (self.end - self.start).days > 365:
            raise ValueError("Use an ordered date range of at most 366 days.")
        return self

    @property
    def days(self):
        return (self.end - self.start).days + 1

    def previous(self):
        return Period(
            start=self.start - timedelta(days=self.days),
            end=self.start - timedelta(days=1),
        )

    def condition(self):
        return f"segments.date BETWEEN '{self.start.isoformat()}' AND '{self.end.isoformat()}'"


class AuditOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    target_cpa: float | None = Field(default=None, gt=0)
    conversion_lag_days: int = Field(default=7, ge=0, le=90)
    tracking_verified: bool = False
    min_clicks: int = Field(default=30, ge=10, le=10000)
    brand_terms: list[str] = Field(default_factory=list, max_length=30)
    irrelevant_terms: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_terms(self):
        for term in self.brand_terms + self.irrelevant_terms:
            if not term.strip() or len(term) > 100:
                raise ValueError("Terms must contain 1–100 characters.")
        return self


class AlertRule(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    metric: Literal[
        "cost", "clicks", "conversions", "cpa", "roas", "ctr", "conversion_rate"
    ]
    operator: Literal["gt", "lt"]
    threshold: float = Field(ge=0)
