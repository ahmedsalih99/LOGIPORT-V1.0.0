# services/storage_service.py
import os, datetime, re
from pathlib import Path


def _safe_tx(transaction_no: str) -> str:
    """يحوّل رقم المعاملة لاسم مجلد آمن (يستبدل / و \\ والمسافات بـ -)."""
    return re.sub(r"[/\\\s]+", "-", (transaction_no or "").strip()) or "UNKNOWN"


class StorageService:
    """Builds output paths for generated documents."""

    def __init__(self, document_root: str):
        self.root = Path(document_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def build_output_path(
        self,
        transaction_no: str,
        doc_no: str,
        language: str,
        doc_type: str,
        ext: str = "pdf",
    ) -> Path:
        """(legacy) kept for compatibility; uses today's date."""
        today = datetime.date.today()
        safe = _safe_tx(transaction_no)
        out_dir = (
            self.root
            / str(today.year)
            / f"{today.month:02d}"
            / safe
            / doc_no
            / language.lower()
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"{doc_type.lower()}.{ext}"

    # NEW – prefer this:
    def build_output_path_from_doc_no(
        self,
        transaction_no: str,
        doc_no: str,
        language: str,
        doc_type: str,
        ext: str = "pdf",
    ) -> Path:
        """
        Extract YYYY and MM from doc_no of the form PREFIX-YYYYMM-#### and use
        them for the storage path.  Falls back to today's date if parsing fails.
        """
        m = re.search(r"-([0-9]{6})-", doc_no or "")
        if m:
            yyyymm = m.group(1)
            year = int(yyyymm[:4])
            month = int(yyyymm[4:])
        else:
            today = datetime.date.today()
            year, month = today.year, today.month

        safe = _safe_tx(transaction_no)
        out_dir = (
            self.root
            / f"{year}"
            / f"{month:02d}"
            / safe
            / doc_no
            / language.lower()
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"{doc_type.lower()}.{ext}"