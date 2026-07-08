"""
PII detection — lazy loaded to reduce memory footprint on free tier.
"""
_analyzer   = None
_anonymizer = None

SENSITIVE_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "CRYPTO",
    "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS", "PERSON",
]


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        _analyzer = AnalyzerEngine()
    return _analyzer


def get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def scan_for_pii(text: str) -> dict:
    results = get_analyzer().analyze(
        text=text, entities=SENSITIVE_ENTITIES, language="en"
    )
    return {
        "has_pii":  len(results) > 0,
        "findings": [
            {"type": r.entity_type, "score": round(r.score, 2)}
            for r in results
        ],
    }


def redact_pii(text: str) -> str:
    results = get_analyzer().analyze(text=text, language="en")
    if not results:
        return text
    return get_anonymizer().anonymize(text=text, analyzer_results=results).text