import re

# Role → permitted (method, path) pairs
# URI has already been stripped of the /api prefix by nginx ($rbac_uri).
#
# investigator    : POST /evidence          — upload artifact
#                   GET  /evidence/*        — own artifacts only (enforced in domain service)
#                   POST /evidence/*/verify — verify own artifacts
#
# forensic_analyst: POST /evidence          — upload artifact
#                   GET  /evidence/*        — assigned cases only (enforced in domain service)
#                   POST /evidence/*/verify — verify artifacts in assigned cases
#
# legal_reviewer  : GET  /evidence/*        — assigned cases, limited fields (domain service)
#                   POST /evidence/*/verify — verify artifacts in assigned cases
#                   GET  /custody/*         — custody timeline
#                   POST /reports/*         — generate report
#                   GET  /reports/*         — read report
#
# admin           : GET|POST|PATCH|DELETE /admin/* — user + case management only
#                   GET /evidence → 403 (no rule matches)

# Rules are evaluated top-to-bottom; first matching (method + pattern) wins.
# More specific patterns must come before broader ones for the same method.
_RULES: list[tuple[str, str, list[str]]] = [
    # POST /evidence — upload (investigator + forensic_analyst)
    ("POST",   r"^/evidence/?$",                    ["investigator", "forensic_analyst"]),
    # POST /evidence/*/verify — verification (investigator + forensic_analyst + legal_reviewer)
    ("POST",   r"^/evidence/[^/]+/verify/?$",       ["investigator", "forensic_analyst", "legal_reviewer"]),
    # GET /evidence/*/download — file download (investigator + forensic_analyst only)
    ("GET",    r"^/evidence/[^/]+/download/?$",     ["investigator", "forensic_analyst"]),
    # GET /evidence/* — metadata read (all non-admin; fine-grained control in domain service)
    ("GET",    r"^/evidence",                       ["investigator", "forensic_analyst", "legal_reviewer"]),
    # GET /cases — case list for upload dropdown
    ("GET",    r"^/cases",                          ["investigator", "forensic_analyst", "legal_reviewer"]),
    # GET /custody/* — chain-of-custody (legal_reviewer only)
    ("GET",    r"^/custody",                        ["legal_reviewer"]),
    # POST/GET /reports/* — audit reports (legal_reviewer only)
    ("POST",   r"^/reports",                        ["legal_reviewer"]),
    ("GET",    r"^/reports",                        ["legal_reviewer"]),
    # GET /ledger/* — immutable ledger viewer (legal_reviewer only)
    ("GET",    r"^/ledger",                         ["legal_reviewer"]),
    # /admin — user + case management (admin only)
    ("GET",    r"^/admin",                          ["admin"]),
    ("POST",   r"^/admin",                          ["admin"]),
    ("PATCH",  r"^/admin",                          ["admin"]),
    ("DELETE", r"^/admin",                          ["admin"]),
]


def is_authorized(role: str, method: str, uri: str) -> bool:
    for rule_method, pattern, allowed in _RULES:
        if rule_method == method and re.match(pattern, uri):
            return role in allowed
    return False
