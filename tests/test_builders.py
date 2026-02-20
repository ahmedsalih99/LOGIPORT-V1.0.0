# tests/test_builders.py
import pytest
from documents.builders.invoice import build_ctx

def test_invoice_builder_success():
    ctx = build_ctx("invoice.normal", 1, "ar")
    assert "items" in ctx
    assert "totals" in ctx
    assert ctx["currency"]["code"] == "USD"

def test_invoice_builder_missing_transaction():
    with pytest.raises(ValueError, match="المعاملة غير موجودة"):
        build_ctx("invoice.normal", 99999, "ar")

# tests/test_persist.py
def test_persist_document():
    result = persist_document(
        transaction_id=1,
        doc_code="invoice.normal",
        lang="ar",
        file_path="/path/to/file.pdf"
    )
    assert "document_no" in result
    assert result["seq"] > 0