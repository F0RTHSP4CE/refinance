"""Application constants"""

# Common currencies list (ISO 4217)
# Default currency is GEL (Georgian Lari)
CURRENCIES = [
    ("GEL", "GEL - Georgian Lari"),
    ("USD", "USD - US Dollar"),
    ("EUR", "EUR - Euro"),
    ("BTC", "BTC - Bitcoin"),
    ("ETH", "ETH - Ethereum"),
    ("USDT", "USDT - Tether"),
]

DEFAULT_CURRENCY = "GEL"

# Allow custom currency entry for backward compatibility
ALLOW_CUSTOM_CURRENCY = True
