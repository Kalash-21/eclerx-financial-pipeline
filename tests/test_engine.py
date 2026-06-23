import uuid

from validation.engine import compute_text_hash, validate_extraction
from validation.schemas import DocumentType, ValidationStatus


def test_valid_data_returns_valid_status():
    result = validate_extraction(
        extracted_data={
            "company_name": "Microsoft Corp",
            "ticker_symbol": "MSFT",
            "filing_date": "2023-10-25",
            "period_of_report": "2023-09-30",
        },
        doc_type=DocumentType.SEC_10K,
        source_filename="msft_10k.pdf",
    )
    assert result.status == ValidationStatus.VALID
    assert result.is_valid is True
    assert result.schema_data is not None


def test_missing_required_field_returns_invalid():
    result = validate_extraction(
        extracted_data={},
        doc_type=DocumentType.TRADE_CONFIRMATION,
        source_filename="empty.pdf",
    )
    assert result.status == ValidationStatus.INVALID
    assert len(result.missing_required_fields) > 0


def test_every_result_has_valid_uuid():
    result = validate_extraction(
        extracted_data={"company_name": "Test"},
        doc_type=DocumentType.SEC_10K,
        source_filename="test.pdf",
    )
    assert result.doc_id is not None
    uuid.UUID(str(result.doc_id))


def test_text_hash_is_deterministic():
    first = compute_text_hash("sample text")
    second = compute_text_hash("sample text")
    assert first == second
    assert len(first) == 64


def test_text_hash_differs_for_different_text():
    assert compute_text_hash("text one") != compute_text_hash("text two")
