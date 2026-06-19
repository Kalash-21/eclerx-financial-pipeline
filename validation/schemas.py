import re
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    SEC_10K = "sec_10k"
    SEC_10Q = "sec_10q"
    TRADE_CONFIRMATION = "trade_confirmation"
    KYC_FORM = "kyc_form"
    COMPLIANCE_SOP = "compliance_sop"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"


class AssetClass(str, Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    DERIVATIVE = "derivative"
    COMMODITY = "commodity"
    FX = "fx"
    OTHER = "other"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


# ---------------------------------------------------------------------------
# Base Schema
# ---------------------------------------------------------------------------

class BaseDocumentSchema(BaseModel):
    doc_id: UUID = Field(default_factory=uuid4)
    doc_type: DocumentType
    source_filename: str
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_model: str = "gpt-4o-mini"
    extraction_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# SEC Filing Schema
# ---------------------------------------------------------------------------

class SECFilingSchema(BaseDocumentSchema):
    doc_type: DocumentType = DocumentType.SEC_10K
    company_name: str = Field(min_length=1)
    ticker_symbol: Optional[str] = Field(default=None, max_length=10)
    cik_number: Optional[str] = None
    fiscal_year_end: Optional[date] = None
    period_of_report: Optional[date] = None
    filing_date: Optional[date] = None
    total_revenue: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    shares_outstanding: Optional[int] = Field(default=None, ge=0)
    key_risk_factors: list[str] = Field(default_factory=list)

    @field_validator("cik_number")
    @classmethod
    def validate_cik(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.zfill(10)
        if not v.isdigit() or len(v) != 10:
            raise ValueError("CIK number must be exactly 10 digits")
        return v

    @field_validator("period_of_report", "filing_date")
    @classmethod
    def validate_date_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Filing date cannot be in the future")
        return v


# ---------------------------------------------------------------------------
# Trade Confirmation Schema
# ---------------------------------------------------------------------------

class TradeConfirmationSchema(BaseDocumentSchema):
    doc_type: DocumentType = DocumentType.TRADE_CONFIRMATION
    trade_id: str
    cusip: Optional[str] = None
    isin: Optional[str] = None
    counterparty_name: str
    asset_class: AssetClass = AssetClass.EQUITY
    trade_date: date
    settlement_date: Optional[date] = None
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    notional_amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    direction: str = Field(pattern=r"^(BUY|SELL|buy|sell)$")

    @field_validator("cusip")
    @classmethod
    def validate_cusip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.upper().strip()
        if not re.match(r"^[A-Z0-9]{9}$", v):
            raise ValueError("Invalid CUSIP format")
        return v

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.upper().strip()
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", v):
            raise ValueError("Invalid ISIN format")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def validate_settlement_after_trade(self) -> "TradeConfirmationSchema":
        if self.settlement_date is not None and self.settlement_date < self.trade_date:
            raise ValueError("Settlement date cannot precede trade date")
        return self

    @model_validator(mode="after")
    def compute_notional(self) -> "TradeConfirmationSchema":
        if self.notional_amount is None:
            self.notional_amount = self.quantity * self.price
        return self


# ---------------------------------------------------------------------------
# KYC Form Schema
# ---------------------------------------------------------------------------

class KYCFormSchema(BaseDocumentSchema):
    doc_type: DocumentType = DocumentType.KYC_FORM
    customer_name: str = Field(min_length=2)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    country_of_residence: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    id_expiry_date: Optional[date] = None
    address_line_1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source_of_funds: Optional[str] = None
    employment_status: Optional[str] = None
    politically_exposed_person: Optional[bool] = None
    risk_tier: Optional[RiskTier] = None
    sanctions_screened: bool = False
    adverse_media_checked: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        age_days = (date.today() - v).days
        if age_days < 18 * 365:
            raise ValueError("Customer must be at least 18 years old")
        if age_days > 130 * 365:
            raise ValueError("Date of birth is implausibly old")
        return v

    @field_validator("id_expiry_date")
    @classmethod
    def validate_id_not_expired(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("ID document is expired")
        return v


# ---------------------------------------------------------------------------
# Compliance SOP Schema
# ---------------------------------------------------------------------------

class ComplianceSOPSchema(BaseDocumentSchema):
    doc_type: DocumentType = DocumentType.COMPLIANCE_SOP
    policy_name: str
    policy_number: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    owner_department: Optional[str] = None
    approver: Optional[str] = None
    applicable_products: list[str] = Field(default_factory=list)
    applicable_jurisdictions: list[str] = Field(default_factory=list)
    purpose_statement: Optional[str] = Field(default=None, max_length=2000)
    key_procedures: list[str] = Field(default_factory=list)
    escalation_path: Optional[str] = None
    regulatory_references: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    doc_id: UUID
    doc_type: DocumentType
    status: ValidationStatus
    schema_data: Optional[dict] = None
    validation_errors: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    source_filename: str

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID

    @property
    def needs_review(self) -> bool:
        return self.status in (ValidationStatus.INVALID, ValidationStatus.PARTIAL)


# ---------------------------------------------------------------------------
# Schema Registry
# ---------------------------------------------------------------------------

SCHEMA_REGISTRY: dict[DocumentType, type[BaseDocumentSchema]] = {
    DocumentType.SEC_10K: SECFilingSchema,
    DocumentType.SEC_10Q: SECFilingSchema,
    DocumentType.TRADE_CONFIRMATION: TradeConfirmationSchema,
    DocumentType.KYC_FORM: KYCFormSchema,
    DocumentType.COMPLIANCE_SOP: ComplianceSOPSchema,
}
