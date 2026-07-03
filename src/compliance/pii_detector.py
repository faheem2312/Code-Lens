from presidio_analyzer   import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer   = AnalyzerEngine()
anonymizer = AnonymizerEngine()

SENSITIVE_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "CRYPTO",
    "CREDIT_CARD", "IBAN_CODE", "IP_ADDRESS", "PERSON",
]


def scan_for_pii(text: str) -> dict:
    results = analyzer.analyze(text=text, entities=SENSITIVE_ENTITIES, language="en")
    return {
        "has_pii":  len(results) > 0,
        "findings": [
            {"type": r.entity_type, "score": round(r.score, 2), "start": r.start, "end": r.end}
            for r in results
        ],
    }


def redact_pii(text: str) -> str:
    results = analyzer.analyze(text=text, language="en")
    if not results:
        return text
    return anonymizer.anonymize(text=text, analyzer_results=results).text
