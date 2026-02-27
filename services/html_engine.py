# services/html_engine.py
from __future__ import annotations
from typing import Dict
from jinja2 import Environment, FileSystemLoader
from documents import TEMPLATES_DIR
from documents.registry import resolve_template
# استخدام الأسماء الكانونية من exceptions.py مباشرةً
from .exceptions import TemplateNotFoundError, HtmlRenderError
# alias للتوافق مع الكود القديم الذي قد يستخدم الاسم القصير
TemplateNotFound = TemplateNotFoundError

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_html(doc_code: str, lang: str, ctx: Dict) -> str:
    try:
        spec = resolve_template(doc_code, lang)
    except FileNotFoundError as e:
        raise TemplateNotFoundError(doc_code=doc_code, lang=lang) from e

    try:
        template_rel = spec.path.relative_to(TEMPLATES_DIR).as_posix()
    except Exception as e:
        raise HtmlRenderError(f"Invalid template path for {doc_code} [{lang}]: {e}") from e

    try:
        tpl = _env.get_template(template_rel)
        merge_ctx = dict(ctx)

        # آمنة حتى لو ما فيه خاصية extra
        extra = getattr(spec, "extra", None)
        if isinstance(extra, dict):
            merge_ctx.update(extra)

        return tpl.render(**merge_ctx)
    except HtmlRenderError:
        raise
    except Exception as e:
        raise HtmlRenderError(f"Jinja2 render failed for {template_rel}: {e}") from e
