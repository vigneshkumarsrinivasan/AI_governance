"""Framework-specific parsers. Each exposes ``parse(raw: bytes, manifest_entry: dict) -> ParsedFramework``."""

from aegis_app.regulatory.parsers.base import (
    ParsedFramework, ParsedNode, ParsedRequirement, ParsedDefinition, sha256_text,
)

__all__ = [
    "ParsedFramework", "ParsedNode", "ParsedRequirement", "ParsedDefinition",
    "sha256_text", "get_parser",
]

_ROUTES = {
    "mitre_atlas": ("aegis_app.regulatory.parsers.mitre_atlas", "parse"),
    "nist_oscal": ("aegis_app.regulatory.parsers.nist_oscal", "parse"),
    "owasp_llm": ("aegis_app.regulatory.parsers.owasp_llm", "parse"),
    "nist_csf": ("aegis_app.regulatory.parsers.nist_cprt", "parse"),
    "nist_ssdf": ("aegis_app.regulatory.parsers.nist_cprt", "parse"),
    "nist_ai_rmf": ("aegis_app.regulatory.parsers.nist_ai_rmf", "parse"),
    "eu_docx": ("aegis_app.regulatory.parsers.eu_docx", "parse"),
    "nist_ai_rmf_pdf": ("aegis_app.regulatory.parsers.nist_pdf", "parse_ai_rmf"),
    "nist_ai_600_1_pdf": ("aegis_app.regulatory.parsers.nist_pdf", "parse_ai_600_1"),
    "owasp_pdf": ("aegis_app.regulatory.parsers.owasp_pdf", "parse"),
    "uk_pdf": ("aegis_app.regulatory.parsers.pdf_legal", "parse_uk_code"),
    "dpdp_pdf": ("aegis_app.regulatory.parsers.pdf_legal", "parse_dpdp_rules"),
    "aiverify": ("aegis_app.regulatory.parsers.aiverify", "parse"),
}


def get_parser(name: str):
    if name not in _ROUTES:
        raise KeyError(f"no parser registered for {name!r} (blocked / not yet implemented)")
    mod_name, fn = _ROUTES[name]
    import importlib
    return getattr(importlib.import_module(mod_name), fn)


def parser_available(name: str) -> bool:
    return name in _ROUTES
