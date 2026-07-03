import sys, os
sys.path.insert(0, os.getcwd())

from src.compliance.pii_detector import scan_for_pii, redact_pii

test_code = """
def send_notification():
    email = "faheem@gmail.com"
    phone = "+91-9876543210"
    return email, phone
"""

result = scan_for_pii(test_code)
print("PII found:", result["has_pii"])
print("Findings:")
for f in result["findings"]:
    print(f"  {f['type']}  score={f['score']}")

print()
print("Redacted output:")
print(redact_pii(test_code))
