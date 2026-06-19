import pytest
from pydantic import ValidationError
from datetime import date, timedelta
from decimal import Decimal

from validation.schemas import (
    DocumentType,
    SECFilingSchema,
    TradeConfirmationSchema,
    KYCFormSchema,
    ValidationStatus,
)


class TestSECFilingSchema:

    def test_valid_10k_passes(self):
        schema = SECFilingSchema(
            doc_type=DocumentType.SEC_10K,
            source_filename="apple_10k.pdf",
            company_name="Apple Inc.",
            ticker_symbol="AAPL",
            cik_number="320193",
        )
        assert schema.company_name == "Apple Inc."
        assert schema.cik_number == "0000320193"

    def test_future_filing_date_rejected(self):
        future_date = (date.today() + timedelta(days=30)).isoformat()
        with pytest.raises(ValidationError) as exc_info:
            SECFilingSchema(
                doc_type=DocumentType.SEC_10K,
                source_filename="apple_10k.pdf",
                company_name="Apple Inc.",
                filing_date=future_date,
            )
        assert "future" in str(exc_info.value).lower()

    def test_invalid_cik_non_numeric_rejected(self):
        with pytest.raises(ValidationError):
            SECFilingSchema(
                doc_type=DocumentType.SEC_10K,
                source_filename="apple_10k.pdf",
                company_name="Apple Inc.",
                cik_number="NOTANUMBER",
            )


class TestTradeConfirmationSchema:

    def _valid_trade_data(self) -> dict:
        return {
            "doc_type": DocumentType.TRADE_CONFIRMATION,
            "source_filename": "trade.pdf",
            "trade_id": "TRD-001",
            "cusip": "037833100",
            "counterparty_name": "Goldman Sachs",
            "asset_class": "equity",
            "trade_date": "2024-01-15",
            "settlement_date": "2024-01-17",
            "quantity": "1000",
            "price": "185.50",
            "currency": "USD",
            "direction": "BUY",
        }

    def test_valid_trade_passes(self):
        schema = TradeConfirmationSchema(**self._valid_trade_data())
        assert schema.cusip == "037833100"
        assert schema.notional_amount == Decimal("185500.00")

    def test_invalid_cusip_too_short_rejected(self):
        data = self._valid_trade_data()
        data["cusip"] = "1234"
        with pytest.raises(ValidationError) as exc_info:
            TradeConfirmationSchema(**data)
        assert "CUSIP" in str(exc_info.value)

    def test_invalid_isin_format_rejected(self):
        data = self._valid_trade_data()
        data["isin"] = "NOTANISIN"
        with pytest.raises(ValidationError):
            TradeConfirmationSchema(**data)

    def test_settlement_before_trade_date_rejected(self):
        data = self._valid_trade_data()
        data["settlement_date"] = "2024-01-10"
        with pytest.raises(ValidationError) as exc_info:
            TradeConfirmationSchema(**data)
        assert "settlement" in str(exc_info.value).lower()

    def test_negative_quantity_rejected(self):
        data = self._valid_trade_data()
        data["quantity"] = "-100"
        with pytest.raises(ValidationError):
            TradeConfirmationSchema(**data)

    def test_invalid_direction_rejected(self):
        data = self._valid_trade_data()
        data["direction"] = "HOLD"
        with pytest.raises(ValidationError):
            TradeConfirmationSchema(**data)


class TestKYCFormSchema:

    def test_underage_customer_rejected(self):
        dob = (date.today() - timedelta(days=16 * 365)).isoformat()
        with pytest.raises(ValidationError) as exc_info:
            KYCFormSchema(
                doc_type=DocumentType.KYC_FORM,
                source_filename="kyc.pdf",
                customer_name="Young Person",
                date_of_birth=dob,
            )
        assert "18" in str(exc_info.value)

    def test_expired_id_rejected(self):
        expired_date = (date.today() - timedelta(days=30)).isoformat()
        with pytest.raises(ValidationError) as exc_info:
            KYCFormSchema(
                doc_type=DocumentType.KYC_FORM,
                source_filename="kyc.pdf",
                customer_name="John Doe",
                id_type="passport",
                id_number="P123456789",
                id_expiry_date=expired_date,
            )
        assert "expired" in str(exc_info.value).lower()

    def test_valid_kyc_passes(self):
        schema = KYCFormSchema(
            doc_type=DocumentType.KYC_FORM,
            source_filename="kyc.pdf",
            customer_name="Jane Smith",
            date_of_birth="1985-06-15",
            nationality="United States",
        )
        assert schema.customer_name == "Jane Smith"
        assert schema.sanctions_screened == False
