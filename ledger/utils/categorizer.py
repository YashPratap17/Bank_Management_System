"""
Keyword-based transaction categorizer.

Checks the combined text of description + recipient name against simple keyword
lists to assign one of the seven supported spending categories. All matching is
case-insensitive. The first matching category wins (ordered by specificity).
Falls back to "Other" when nothing matches.
"""


# Map category name → set of trigger keywords (all lowercase).
_RULES = [
    ("Food",          {"canteen", "food", "mess", "zomato", "swiggy",
                       "restaurant", "pizza", "burger"}),
    ("Transport",     {"bus", "metro", "uber", "ola", "auto", "petrol",
                       "fuel", "travel", "train", "ticket"}),
    ("Shopping",      {"amazon", "flipkart", "myntra", "mall", "clothes",
                       "shoes", "shop", "store"}),
    ("Entertainment", {"movie", "netflix", "spotify", "game", "pub",
                       "party", "concert"}),
    ("Bills",         {"bill", "electricity", "rent", "recharge", "wifi",
                       "internet", "mobile"}),
    ("Education",     {"book", "course", "exam", "library", "notes",
                       "print", "xerox"}),
]


def categorize_transaction(description: str = "",
                           recipient: str = "",
                           amount=None) -> str:
    """
    Return a category string for a transaction.

    Args:
        description: The free-text description entered by the user.
        recipient:   Optional recipient name or account string (used for
                     transfer context, e.g. "Zomato delivery").
        amount:      Unused for now; reserved for future amount-based rules.

    Returns:
        One of: Food | Transport | Shopping | Entertainment | Bills |
                Education | Other
    """
    haystack = f"{description} {recipient}".lower()

    for category, keywords in _RULES:
        for keyword in keywords:
            if keyword in haystack:
                return category

    return "Other"
