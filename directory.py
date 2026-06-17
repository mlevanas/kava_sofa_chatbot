"""User directory (mock SSO/HR source) and organisation facts used by traps.

In production these come from the real identity provider / HR system. Here they
are seeded from the analysed dataset (UAB "Inovatyvūs sprendimai").
"""
from config import PUBLIC, INTERNAL, CONFIDENTIAL, SECRET

# pyotp base32 secrets are fixed so demo codes are reproducible.
USERS = {
    "vpaliulis": {
        "name": "Vytautas Paliulis", "role": "exec", "clearance": SECRET,
        "manager": "Board", "ext": "100", "otp_secret": "JBSWY3DPEHPK3PXP",
    },
    "amockute": {
        "name": "Audra Mockutė", "role": "hr", "clearance": CONFIDENTIAL,
        "manager": "Vytautas Paliulis", "ext": "101", "otp_secret": "KRSXG5DJNZSXIZLT",
    },
    "azukauskas": {
        "name": "Algirdas Žukauskas", "role": "finance", "clearance": CONFIDENTIAL,
        "manager": "Vytautas Paliulis", "ext": "103", "otp_secret": "MFRGGZDFMZTWQ2LK",
    },
    "dsmilauskis": {
        "name": "Darius Smilauskis", "role": "it", "clearance": SECRET,
        "manager": "Vytautas Paliulis", "ext": "102", "otp_secret": "NB2W45DFOIZA2345",
    },
    "ieva": {
        "name": "Ieva Ivanauskaitė", "role": "sales", "clearance": CONFIDENTIAL,
        "manager": "Rūta Melaščenko", "ext": "110", "otp_secret": "ORSXG5BAONSWG4TF",
    },
    "ruta": {
        "name": "Rūta Melaščenko", "role": "marketing", "clearance": INTERNAL,
        "manager": "Vytautas Paliulis", "ext": "105", "otp_secret": "PFXXK4DUPEXA2345",
    },
    "jdarbuotojas": {
        "name": "Jonas Darbuotojas", "role": "employee", "clearance": INTERNAL,
        "manager": "Audra Mockutė", "ext": "120", "otp_secret": "QFXXK4TUPFXXK4TU",
    },
}

# Facts the bot can quietly verify against (used by trap / consistency questions).
ORG_FACTS = {
    "branches": ["vilnius", "kaunas", "klaipeda", "klaipėda"],   # NO Helsinki
    "fake_branches": ["helsinki", "ryga", "riga", "talinas", "tallinn", "warsaw", "varšuva"],
    "workday_start": ["08:00", "8:00", "8", "08", "8 am", "8am", "aštuonios", "astuonios"],
    "vacation_days": ["20", "twenty", "dvidešimt", "dvidesimt"],
    "faq_doc": ["duk", "dažnai užduodami klausimai", "dazniausiai", "faq"],
}


def get_user(username: str):
    return USERS.get((username or "").strip().lower())
