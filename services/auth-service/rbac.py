import re

# Role → permitted (method, path) pairs
# URI has already been stripped of the /api prefix by nginx ($rbac_uri).
#
# investigator    : POST /evidence          — create new artifact
#                   GET  /evidence/*        — read artifact list & detail
#                   POST /evidence/*/verify — trigger integrity verification
#
# forensic_analyst: POST /evidence          — create new artifact
#                   GET  /evidence/*        — read artifact list & detail
#                   POST /evidence/*/verify — trigger integrity verification
#
# legal_reviewer  : GET  /custody/*         — read custody chain
#                   POST /reports/*         — generate report
#                   GET  /reports/*         — read report
#
# admin           : GET|POST|PATCH /admin/* — system administration only
#                   (no implicit catch-all — admin manages the platform,
#                    not the evidence data directly)

# Rules are evaluated top-to-bottom; first matching (method + pattern) wins.
# More specific patterns must come before broader ones for the same method.
_RULES: list[tuple[str, str, list[str]]] = [
    # POST /evidence — artifact creation (investigator + forensic_analyst)
    ("POST",   r"^/evidence/?$",              ["investigator", "forensic_analyst"]),
    # POST /evidence/*/verify — integrity check (investigator + forensic_analyst)
    ("POST",   r"^/evidence/[^/]+/verify/?$", ["investigator", "forensic_analyst"]),
    # GET  /evidence/* — read access (investigator + forensic_analyst)
    ("GET",    r"^/evidence",                 ["investigator", "forensic_analyst"]),
    # GET  /custody/* — chain-of-custody read (legal_reviewer only)
    ("GET",    r"^/custody",                  ["legal_reviewer"]),
    # POST /reports/* — report generation (legal_reviewer)
    ("POST",   r"^/reports",                  ["legal_reviewer"]),
    # GET  /reports/* — report read (legal_reviewer)
    ("GET",    r"^/reports",                  ["legal_reviewer"]),
    # /admin — user management (admin only)
    ("GET",    r"^/admin",                    ["admin"]),
    ("POST",   r"^/admin",                    ["admin"]),
    ("PATCH",  r"^/admin",                    ["admin"]),
    ("DELETE", r"^/admin",                    ["admin"]),
]


def is_authorized(role: str, method: str, uri: str) -> bool:
    for rule_method, pattern, allowed in _RULES:
        if rule_method == method and re.match(pattern, uri):
            return role in allowed
    return False
