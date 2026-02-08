import json
from os import getenv


class Config:
    REFINANCE_API_BASE_URL = getenv("REFINANCE_API_BASE_URL", "http://api:8000")
    FRIDGE_PRESETS = [
        {"amount": 5, "currency": "GEL", "label": "5 GEL"},
    ]
    COFFEE_PRESETS = [
        {"amount": 5, "currency": "GEL", "label": "5 GEL"},
    ]
    TAG_IDS = {
        "fee": 3,
        "deposit": 9,
        "withdrawal": 10,
        "resident": 2,
        "member": 14,
    }
    ENTITY_IDS = {
        "f0": 1,
        "fridge": 141,
        "coffee": 150,
    }
