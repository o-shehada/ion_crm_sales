
# -*- coding: utf-8 -*-
"""
Single source of truth for commission constants.
Edit these values (Item Group names & rates), redeploy, and you're done.
"""

# ---------------------------
# Item Groups (exact names!)
# ---------------------------

# SALES
SALES_ITEM_GROUPS = {
    "HOME": "Home",
    "HOTSPOT": "Hotspot - Sales",
}

# BA
BA_ITEM_GROUPS = {
    "DEDICATED":    "Dedicated",
    "HOTEL":        "Hotel",
    "ISPS":         "ISPs",
    "ION_SOLUTIONS":"ION Solutions",
    "HOTSPOT":      "Hotspot - BA",
    "ULTRA_MALLS":  "Ultra - Malls",
}

# --------------------------------
# SALES: rates & splits (fractions)
# --------------------------------
SALES_RATES = {
    "HOME":     {"normal": 0.0005, "above": 0.003},  # 0.05%, 0.3%
    "HOTSPOT":  {"normal": 0.01,   "above": 0.06},   # 1%, 6%
}

# Splits (manager/rest). Values must sum to 1.0 per mode.
SALES_SPLITS = {
    "HOME": {
        "normal": {"manager": 0.30, "rest": 0.70},
        "above":  {"manager": 0.30, "rest": 0.70},
    },
    "HOTSPOT": {
        "normal": {"manager": 0.30, "rest": 0.70},
        "above":  {"manager": 0.20, "rest": 0.80},
    },
}

# ------------------------------------
# BA: non–ION Solutions category rates
# ------------------------------------
BA_RATES = {
    "DEDICATED":   {"old": 0.0075,  "new": 0.01,   "upsell": 0.02,  "above": 0.06},
    "ISPS":        {"old": 0.0025,  "new": 0.00125,"upsell": 0.0025,"above": 0.005},
    "HOTEL":       {"old": 0.01,    "new": 0.02,   "upsell": 0.03,  "above": 0.06},
    "HOTSPOT":     {"old": 0.02,    "new": 0.02,   "upsell": 0.03,  "above": 0.06},
    "ULTRA_MALLS": {"old": 0.005,   "new": 0.02,   "upsell": 0.03,  "above": 0.02},
}

# ------------------------------
# BA: ION Solutions role rates
# ------------------------------
ION_ROLE_RATES = {
    "Account Lead Acquisition": 0.01,  # 1%
    "Offer Team":               0.05,  # 5%
    "Execution Team":           0.05,  # 5%
}
ION_ABOVE_ADDON = 0.03  # +3% addon when the person is Above (not a replacement)

# -------------------------
# Global add-ons & bonuses
# -------------------------
FIRST_YEAR_ADDON_RATE = 0.01     # +1% on marked first-year SI (New Lead), split among non AM/SM employees
PROJECT_ACQ_BONUS = 3000.0       # Hotspot & Ultra-Malls, New Lead only, split among ALL employees on the invoice


# -------------------------
# Penalty plan (code config)
# -------------------------
PENALTY_PLANS = {
    # Fully-paid after grace → -50% once, then -10% per cadence block.
    "yearly":    {"grace_days": 90, "cadence_days": 30},  # 3 months, then monthly
    "6mo":       {"grace_days": 42, "cadence_days": 14},  # 6 weeks, then every 2 weeks
    "quarterly": {"grace_days": 21, "cadence_days": 7},   # 3 weeks, then weekly
}
