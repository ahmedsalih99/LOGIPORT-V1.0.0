# LOGIPORT Documents Seed

This package provides a minimal, production-ready scaffold for the Documents system:

- `services/`:
  - `document_service.py`: high-level pipeline (context build → render HTML → PDF/HTML output).
  - `pdf_service.py`: uses WeasyPrint if available; otherwise writes `.html` as a preview.
  - `template_resolver.py`: picks correct template by doc type/language/variant.
  - `numbering_service.py`: generates unified doc_no per group.
  - `storage_service.py`: builds consistent output paths under `documents/output/`.
  - `tafqit_service.py`: placeholder for amount-in-words (replace with real tafqit).

- `documents/templates/`:
  - `common/base.css`: shared print styles.
  - `invoice/{ar,en,tr}/invoice.html`
  - `packing_list/{ar,en,tr}/packing_list.html`

- `documents/generator.py`: runnable demo. Adjust paths/imports for your project and run:

```bash
cd documents
python generator.py
```

## Integrating with your app
- Point `templates_root` to your `documents/templates`.
- Point `document_root` to your configured `document_path` in Settings.
- Replace the mock `transaction` dict with a DB-backed mapper that fetches:
  - exporter/importer/intermediary
  - items (description by language, unit, quantity, weights, pricing, totals)

## Notes
- If `weasyprint` is not installed, files are saved as `.html`. Set `prefer_pdf=True` to produce PDFs.
- Extend `TemplateResolver` to support more variants (foreign, syrian, intermediary) by adding templates.
- Replace `TafqitService` with your multilingual tafqit implementation.