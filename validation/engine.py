import hashlib
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from validation.schemas import (
    BaseDocumentSchema,
    DocumentType,
    SCHEMA_REGISTRY,
    ValidationResult,
    ValidationStatus,
)


def validate_extraction(
    extracted_data: dict[str, Any],
    doc_type: DocumentType,
    source_filename: str,
) -> ValidationResult:
    schema_class = SCHEMA_REGISTRY.get(doc_type)

    if schema_class is None:
        return ValidationResult(
            doc_id=uuid4(),
            doc_type=doc_type,
            status=ValidationStatus.INVALID,
            validation_errors=[f"No schema registered for doc_type: {doc_type}"],
            source_filename=source_filename,
        )

    merged = {**extracted_data, "doc_type": doc_type.value, "source_filename": source_filename}

    try:
        instance = schema_class.model_validate(merged)
        return ValidationResult(
            doc_id=instance.doc_id,
            doc_type=doc_type,
            status=ValidationStatus.VALID,
            schema_data=instance.model_dump(mode="json"),
            source_filename=source_filename,
        )
    except ValidationError as exc:
        errors: list[str] = []
        missing_required: list[str] = []

        for error in exc.errors():
            field_path = " → ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"{field_path}: {msg}")
            if error["type"] == "missing":
                missing_required.append(field_path)

        if not missing_required and len(errors) <= 3:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.INVALID

        return ValidationResult(
            doc_id=uuid4(),
            doc_type=doc_type,
            status=status,
            validation_errors=errors,
            missing_required_fields=missing_required,
            source_filename=source_filename,
        )


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
