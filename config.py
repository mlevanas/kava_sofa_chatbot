"""Central configuration for the classification-aware internal chatbot."""
import os

# ---- Classification levels (ordered) -------------------------------------
PUBLIC, INTERNAL, CONFIDENTIAL, SECRET = 0, 1, 2, 3
LEVEL_NAMES = {
    PUBLIC: "Public",
    INTERNAL: "Internal",
    CONFIDENTIAL: "Confidential",
    SECRET: "Strictly confidential",
}

# ---- Per-document classification --------------------------------------------
# Maps document basename -> (level, allowed_roles_for_confidential).
# Roles: finance, hr, sales, marketing, it, exec, employee.
# For PUBLIC/INTERNAL docs the role set is ignored (open to all cleared users).
ALL_CONF_ROLES = {"exec"}  # exec + SECRET clearance can always read confidential
CLASSIFICATION = {
    # Public
    "Techninis_produkto_aprasymas.docx": (PUBLIC, None),
    "Straipsnio ištrauka sentimento analizei.docx": (PUBLIC, None),
    # Internal
    "Vidinės tvarkos_Inovatyvūs sprendimai.pdf": (INTERNAL, None),
    "DUK (DAŽNAI UŽDUODAMI KLAUSIMAI).docx": (INTERNAL, None),
    "Darbuotojo žinynas.docx": (INTERNAL, None),
    "IT Saugumo taisyklės.docx": (INTERNAL, None),
    "VERSLO ATVEJO ANALIZĖ.docx": (INTERNAL, None),
    # Confidential
    "Klientų atsiliepimų duomenų bazė.xlsx": (CONFIDENTIAL, {"sales", "exec"}),
    "Susitikimo_transkripcija_klientu_portalas.docx": (CONFIDENTIAL, {"sales", "marketing", "it", "exec"}),
    "Sutartis nr. 1.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "Sutartis Nr. 2.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "Sutartis 3.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "saskaita_1_standartine.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "saskaita_2_netvarkinga.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "saskaita_3_angliska.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "saskaita_4_be_pvm.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "saskaita_5_atvirkstinis_pvm.pdf": (CONFIDENTIAL, {"finance", "exec"}),
    "ekomercijos_pardavimai_.csv": (CONFIDENTIAL, {"finance", "sales", "exec"}),
}
DEFAULT_LEVEL = INTERNAL  # anything not explicitly listed

# ---- Paths ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.environ.get("DATASET_DIR", os.path.join(BASE_DIR, "data"))
AUDIT_LOG = os.environ.get("AUDIT_LOG", os.path.join(BASE_DIR, "audit.log"))

# ---- LLM --------------------------------------------------------------------
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_CONTEXT_CHUNKS = 6

# ---- Risk thresholds --------------------------------------------------------
RISK_MEDIUM = 3   # ask a trap / verification question
RISK_HIGH = 6     # lock session + escalate

# Risk points per signal
PTS_PROMPT_INJECTION = 4
PTS_REPEAT_AFTER_DENIAL = 3
PTS_SENSITIVE_IDENTIFIER = 3
PTS_ROLE_MISMATCH = 2
PTS_ABOVE_CLEARANCE = 2
PTS_TRAP_FAIL = 4
PTS_CANARY_BLUFF = 5

SECURITY_CONTACT = "IT Security — Darius Smilauskis (ext. 102)"
SESSION_IDLE_SECONDS = 600
