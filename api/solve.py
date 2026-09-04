import os
import re
import json
import ast
import operator as op
from http.server import BaseHTTPRequestHandler

# =========================================================
# COMMERCE AI V2
# CBSE CLASS 12 ACCOUNTANCY + ECONOMICS SOLVER
# =========================================================


# =========================================================
# BASIC HELPERS
# =========================================================

def normalize(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("₹", " ")
    text = text.replace("rs.", " ")
    text = text.replace("Rs.", " ")
    text = text.replace("Rs", " ")
    text = text.replace("INR", " ")
    text = text.replace(",", "")
    text = text.replace("×", "*")
    text = text.replace("÷", "/")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return text.lower().strip()


def clean_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return None


def format_number(value):
    if value is None:
        return "0"

    try:
        value = float(value)

        if abs(value - round(value)) < 0.000001:
            value = int(round(value))
        else:
            value = round(value, 2)

        return f"{value:,}"

    except:
        return str(value)


def money(value):
    return "₹" + format_number(value)


def format_decimal(value, places=2):
    try:
        return f"{float(value):.{places}f}"
    except:
        return str(value)


def percentage(value):
    try:
        return f"{float(value):.2f}%"
    except:
        return str(value)


def all_numbers(text):
    text = str(text).replace(",", "")

    nums = re.findall(
        r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?",
        text
    )

    return [float(x) for x in nums]


def first_number(text):
    nums = all_numbers(text)
    return nums[0] if nums else None


def safe_div(a, b):
    try:
        if b == 0:
            return None
        return a / b
    except:
        return None


def gcd(a, b):
    a = abs(int(a))
    b = abs(int(b))

    while b:
        a, b = b, a % b

    return a


def simplify_ratio(values):
    values = [
        int(round(float(x)))
        for x in values
    ]

    if not values:
        return ""

    non_zero = [
        abs(x) for x in values if x != 0
    ]

    if not non_zero:
        return ":".join(
            map(str, values)
        )

    g = non_zero[0]

    for x in non_zero[1:]:
        g = gcd(g, x)

    if g == 0:
        return ":".join(
            map(str, values)
        )

    return ":".join(
        str(int(x / g))
        for x in values
    )


def fraction_text(num, den):
    if den == 0:
        return "undefined"

    return f"{num}/{den}"


# =========================================================
# RATIO / FRACTION EXTRACTION
# =========================================================

def parse_fraction(s):
    if not s:
        return None

    s = str(s).strip()

    m = re.search(
        r"(\d+)\s*/\s*(\d+)",
        s
    )

    if m:
        return float(m.group(1)) / float(m.group(2))

    m = re.search(
        r"(\d+)\s*:\s*(\d+)",
        s
    )

    if m:
        return float(m.group(1)) / float(m.group(2))

    return None


def extract_ratio(text):
    n = normalize(text)

    patterns = [

        r"ratio\s*(?:of|is|=|:)?\s*(\d+)\s*:\s*(\d+)",

        r"sharing\s+(?:profits?|profit.*?losses?)?\s*(?:in\s+)?(?:the\s+)?ratio\s*(?:of|is|=|:)?\s*(\d+)\s*:\s*(\d+)",

        r"profits?.*?ratio.*?(\d+)\s*:\s*(\d+)",

        r"ratio.*?(\d+)\s*:\s*(\d+)"
    ]

    for p in patterns:

        m = re.search(p, n)

        if m:
            return [
                int(m.group(1)),
                int(m.group(2))
            ]

    return None


def extract_multi_ratio(text, context=None):
    n = normalize(text)

    candidates = re.findall(
        r"(\d+(?:\s*:\s*\d+){1,5})",
        n
    )

    ratios = []

    for item in candidates:

        nums = [
            int(x)
            for x in re.findall(
                r"\d+",
                item
            )
        ]

        if len(nums) >= 2:

            # Ignore obvious percentages/dates
            if all(x <= 100 for x in nums):
                ratios.append(nums)

    if context:
        context = normalize(context)

        for item in re.findall(
            r"(\d+(?:\s*:\s*\d+){1,5})",
            context
        ):

            nums = [
                int(x)
                for x in re.findall(
                    r"\d+",
                    item
                )
            ]

            if len(nums) >= 2:
                ratios.append(nums)

    return ratios


def extract_share(text):
    n = normalize(text)

    patterns = [

        r"(?:for|gets?|receives?|admit(?:ted)?\s+.*?for)"
        r"\s*(?:a\s*)?(\d+)\s*/\s*(\d+)"
        r"(?:st|nd|rd|th)?\s*(?:share)?",

        r"(\d+)\s*/\s*(\d+)"
        r"(?:st|nd|rd|th)?\s*share",

        r"(\d+)\s*/\s*(\d+)"
        r"(?:st|nd|rd|th)?"
    ]

    for p in patterns:

        m = re.search(p, n)

        if m:

            num = float(m.group(1))
            den = float(m.group(2))

            if den != 0:
                return num / den

    return None


def extract_percentage(text):
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        str(text)
    )

    return float(m.group(1)) if m else None


# =========================================================
# MONEY EXTRACTION
# =========================================================

def extract_labeled_number(text, labels):
    text = str(text)

    for label in labels:

        pattern = (
            rf"{label}"
            rf"\s*(?:=|is|of|amount|amounting\s+to)?"
            rf"\s*(?:₹|rs\.?|inr)?"
            rf"\s*([\d,]+(?:\.\d+)?)"
        )

        m = re.search(
            pattern,
            text,
            re.I
        )

        if m:
            return clean_number(
                m.group(1)
            )

    return None


def extract_amount_after(text, phrases):
    text = str(text)

    for phrase in phrases:

        pattern = (
            rf"{phrase}"
            rf"\s*(?:=|is|of|amounting\s+to|worth)?"
            rf"\s*(?:₹|rs\.?|inr)?"
            rf"\s*([\d,]+(?:\.\d+)?)"
        )

        m = re.search(
            pattern,
            text,
            re.I
        )

        if m:
            return clean_number(
                m.group(1)
            )

    return None


# =========================================================
# SAFE MATH
# =========================================================

_ALLOWED_BIN = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}

_ALLOWED_UNARY = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def safe_math(expression):

    try:

        expression = expression.replace(
            ",",
            ""
        )

        tree = ast.parse(
            expression,
            mode="eval"
        )

        def calc(node):

            if isinstance(
                node,
                ast.Expression
            ):
                return calc(node.body)

            if isinstance(
                node,
                ast.Constant
            ):

                if isinstance(
                    node.value,
                    (int, float)
                ):
                    return node.value

                raise ValueError()

            if isinstance(
                node,
                ast.BinOp
            ):

                fn = _ALLOWED_BIN.get(
                    type(node.op)
                )

                if not fn:
                    raise ValueError()

                return fn(
                    calc(node.left),
                    calc(node.right)
                )

            if isinstance(
                node,
                ast.UnaryOp
            ):

                fn = _ALLOWED_UNARY.get(
                    type(node.op)
                )

                if not fn:
                    raise ValueError()

                return fn(
                    calc(node.operand)
                )

            raise ValueError()

        return calc(tree)

    except:
        return None


# =========================================================
# GOODWILL — AVERAGE PROFIT
# =========================================================

def solve_goodwill_average(text):

    n = normalize(text)

    if "average profit" not in n:
        return None

    profits = []

    m = re.search(
        r"profits?\s*(?:are|were|of)?\s*"
        r"([\d,\s]+(?:and|,)\s*[\d,\s]+"
        r"(?:and|,)?[\d,\s]*)",
        text,
        re.I
    )

    if m:
        profits = all_numbers(
            m.group(1)
        )

    if not profits:

        nums = all_numbers(text)

        if len(nums) >= 3:
            profits = nums[:3]

    years = extract_labeled_number(
        text,
        [
            r"years?['’]? purchase",
            r"years? purchase"
        ]
    )

    if years is None:

        m = re.search(
            r"(\d+)\s*(?:years?|year)"
            r".*?(?:purchase|goodwill)",
            n
        )

        if m:
            years = float(
                m.group(1)
            )

    if not profits or years is None:
        return None

    avg = sum(profits) / len(profits)

    goodwill = avg * years

    return f"""
DETAILED SOLUTION — GOODWILL BY AVERAGE PROFIT METHOD

GIVEN:
Profits = {", ".join(money(x) for x in profits)}
Years' Purchase = {format_number(years)}

STEP 1: Calculate Average Profit

Average Profit
= Total Profits / Number of Years

= ({' + '.join(money(x) for x in profits)})
  / {format_number(len(profits))}

= {money(avg)}

STEP 2: Calculate Goodwill

Formula:
Goodwill = Average Profit × Years' Purchase

= {money(avg)} × {format_number(years)}

= {money(goodwill)}

FINAL ANSWER:
Goodwill = {money(goodwill)}
"""


# =========================================================
# GOODWILL — SUPER PROFIT
# =========================================================

def solve_goodwill_super(text):

    n = normalize(text)

    if "super profit" not in n:
        return None

    avg = extract_labeled_number(
        text,
        ["average profit"]
    )

    normal = extract_labeled_number(
        text,
        ["normal profit"]
    )

    years = extract_labeled_number(
        text,
        [
            r"years?['’]? purchase",
            r"years? purchase"
        ]
    )

    if (
        avg is None
        or normal is None
        or years is None
    ):
        return None

    super_profit = avg - normal

    goodwill = super_profit * years

    return f"""
DETAILED SOLUTION — GOODWILL BY SUPER PROFIT METHOD

GIVEN:
Average Profit = {money(avg)}
Normal Profit = {money(normal)}
Years' Purchase = {format_number(years)}

STEP 1: Super Profit

Formula:
Super Profit
= Average Profit - Normal Profit

= {money(avg)} - {money(normal)}

= {money(super_profit)}

STEP 2: Goodwill

Formula:
Goodwill
= Super Profit × Years' Purchase

= {money(super_profit)} × {format_number(years)}

= {money(goodwill)}

FINAL ANSWER:
Super Profit = {money(super_profit)}
Goodwill = {money(goodwill)}
"""


# =========================================================
# GOODWILL — CAPITALISATION
# =========================================================

def solve_goodwill_capitalisation(text):

    n = normalize(text)

    if (
        "capitalisation" not in n
        and "capitalization" not in n
    ):
        return None

    avg = extract_labeled_number(
        text,
        ["average profit"]
    )

    normal_rate = extract_labeled_number(
        text,
        [
            "normal rate",
            "normal rate of return"
        ]
    )

    net_assets = extract_labeled_number(
        text,
        [
            "capital employed",
            "net assets"
        ]
    )

    if avg is None or normal_rate is None:
        return None

    capitalised = safe_div(
        avg * 100,
        normal_rate
    )

    if capitalised is None:
        return None

    goodwill = None

    if net_assets is not None:
        goodwill = (
            capitalised
            - net_assets
        )

    result = f"""
DETAILED SOLUTION — CAPITALISATION METHOD

GIVEN:
Average Profit = {money(avg)}
Normal Rate of Return = {format_number(normal_rate)}%

STEP 1: Capitalised Value

Formula:
Capitalised Value
= Average Profit × 100 / Normal Rate

= {money(avg)} × 100 / {format_number(normal_rate)}

= {money(capitalised)}
"""

    if net_assets is not None:

        result += f"""
STEP 2: Goodwill

Goodwill
= Capitalised Value - Net Assets

= {money(capitalised)} - {money(net_assets)}

= {money(goodwill)}

FINAL ANSWER:
Goodwill = {money(goodwill)}
"""

    else:

        result += """
Net Assets were not provided.
Therefore goodwill cannot be completed.
"""

    return result


# =========================================================
# SUPER PROFIT
# =========================================================

def solve_super_profit(text):

    n = normalize(text)

    if "super profit" not in n:
        return None

    avg = extract_labeled_number(
        text,
        ["average profit"]
    )

    normal = extract_labeled_number(
        text,
        ["normal profit"]
    )

    if avg is None or normal is None:
        return None

    sp = avg - normal

    return f"""
DETAILED SOLUTION — SUPER PROFIT

GIVEN:
Average Profit = {money(avg)}
Normal Profit = {money(normal)}

Formula:
Super Profit
= Average Profit - Normal Profit

= {money(avg)} - {money(normal)}

= {money(sp)}

FINAL ANSWER:
Super Profit = {money(sp)}
"""


# =========================================================
# ADVANCED ADMISSION OF PARTNER — V2
# =========================================================

def solve_admission(text):

    n = normalize(text)

    if (
        "admit" not in n
        and "admission" not in n
    ):
        return None

    # -----------------------------------------------------
    # 1. FIND OLD PARTNERS + OLD RATIO
    # -----------------------------------------------------

    ratio_match = re.search(
        r"(?:sharing|share).*?"
        r"(?:ratio|profits?).*?"
        r"(\d+(?:\s*:\s*\d+){1,5})",
        n
    )

    if not ratio_match:

        ratio_match = re.search(
            r"ratio\s*(?:of|is|=|:)?\s*"
            r"(\d+(?:\s*:\s*\d+){1,5})",
            n
        )

    if not ratio_match:
        return None

    old_ratio = [
        int(x)
        for x in re.findall(
            r"\d+",
            ratio_match.group(1)
        )
    ]

    if len(old_ratio) < 2:
        return None

    # -----------------------------------------------------
    # 2. FIND PARTNER NAMES
    # -----------------------------------------------------

    partners_match = re.search(
        r"([A-Z](?:\s*,\s*[A-Z])*(?:\s+and\s+[A-Z])?)"
        r"\s+are\s+partners",
        text
    )

    old_names = []

    if partners_match:

        old_names = re.findall(
            r"[A-Z]",
            partners_match.group(1)
        )

    if len(old_names) != len(old_ratio):

        # Fallback: assume A, B, C...
        old_names = [
            chr(
                ord("A") + i
            )
            for i in range(
                len(old_ratio)
            )
        ]

    # -----------------------------------------------------
    # 3. FIND NEW PARTNER
    # -----------------------------------------------------

    new_partner = None

    m = re.search(
        r"\badmit\s+([A-Z])\b",
        text,
        re.I
    )

    if m:
        new_partner = m.group(1).upper()

    if not new_partner:

        m = re.search(
            r"\badmission\s+of\s+([A-Z])\b",
            text,
            re.I
        )

        if m:
            new_partner = m.group(1).upper()

    if not new_partner:
        new_partner = chr(
            ord("A")
            + len(old_ratio)
        )

    # -----------------------------------------------------
    # 4. NEW PARTNER SHARE
    # -----------------------------------------------------

    new_share = extract_share(text)

    if new_share is None:
        return None

    old_total = sum(old_ratio)

    old_shares = [
        x / old_total
        for x in old_ratio
    ]

    remaining = 1 - new_share

    # -----------------------------------------------------
    # 5. ACQUISITION / SACRIFICE RATIO
    # -----------------------------------------------------

    acquisition_ratio = None

    acquisition_patterns = [
        r"acquires?.*?"
        r"share.*?"
        r"ratio\s*(?:of|is|=|:)?\s*"
        r"(\d+(?:\s*:\s*\d+){1,5})",

        r"acquisition.*?"
        r"ratio\s*(?:of|is|=|:)?\s*"
        r"(\d+(?:\s*:\s*\d+){1,5})",

        r"from\s+"
        r".*?"
        r"ratio\s*(?:of|is|=|:)?\s*"
        r"(\d+(?:\s*:\s*\d+){1,5})"
    ]

    for p in acquisition_patterns:

        m = re.search(
            p,
            n
        )

        if m:

            acquisition_ratio = [
                int(x)
                for x in re.findall(
                    r"\d+",
                    m.group(1)
                )
            ]

            if len(
                acquisition_ratio
            ) == len(old_ratio):

                break

            acquisition_ratio = None

    # -----------------------------------------------------
    # 6. CALCULATE NEW RATIO
    # -----------------------------------------------------

    sacrifices = []

    if acquisition_ratio:

        acq_total = sum(
            acquisition_ratio
        )

        for i in range(
            len(old_ratio)
        ):

            sacrifice = (
                new_share
                * acquisition_ratio[i]
                / acq_total
            )

            sacrifices.append(
                sacrifice
            )

        new_shares = [
            old_shares[i]
            - sacrifices[i]
            for i in range(
                len(old_ratio)
            )
        ]

    else:

        # If no acquisition ratio is given,
        # use old ratio for distributing remaining share.

        new_shares = [
            remaining * x
            for x in old_shares
        ]

        sacrifices = [
            old_shares[i]
            - new_shares[i]
            for i in range(
                len(old_ratio)
            )
        ]

    new_shares.append(
        new_share
    )

    # -----------------------------------------------------
    # 7. FINAL AGREED RATIO
    # -----------------------------------------------------

    final_ratio = None

    final_patterns = [
        r"after\s+admission.*?"
        r"(?:share|ratio).*?"
        r"(\d+(?:\s*:\s*\d+){1,5})",

        r"future\s+profits?.*?"
        r"(\d+(?:\s*:\s*\d+){1,5})",

        r"new\s+ratio.*?"
        r"(\d+(?:\s*:\s*\d+){1,5})"
    ]

    for p in final_patterns:

        m = re.search(
            p,
            n
        )

        if m:

            candidate = [
                int(x)
                for x in re.findall(
                    r"\d+",
                    m.group(1)
                )
            ]

            if len(candidate) == len(
                old_ratio
            ) + 1:

                final_ratio = candidate
                break

    # -----------------------------------------------------
    # 8. GOODWILL
    # -----------------------------------------------------

    goodwill_value = None

    goodwill_patterns = [
        r"goodwill\s+of\s+(?:the\s+)?firm",
        r"firm\s+goodwill",
        r"goodwill"
    ]

    for label in goodwill_patterns:

        m = re.search(
            label
            + r"\s*(?:=|is|of|valued\s+at)?"
            + r"\s*(?:₹|rs\.?|inr)?"
            + r"\s*([\d,]+(?:\.\d+)?)",
            text,
            re.I
        )

        if m:

            goodwill_value = clean_number(
                m.group(1)
            )

            break

    # -----------------------------------------------------
    # 9. GOODWILL PREMIUM ACTUALLY BROUGHT
    # -----------------------------------------------------

    premium = None

    premium_patterns = [

        r"goodwill\s+premium.*?"
        r"(?:brings?|brought|brings\s+in).*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",

        r"(?:brings?|brought).*?"
        r"goodwill.*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",

        r"premium\s+for\s+goodwill.*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)"
    ]

    for p in premium_patterns:

        m = re.search(
            p,
            text,
            re.I
        )

        if m:

            premium = clean_number(
                m.group(1)
            )

            break

    # -----------------------------------------------------
    # 10. CAPITAL OF NEW PARTNER
    # -----------------------------------------------------

    new_capital = None

    capital_patterns = [

        rf"{new_partner}.*?"
        r"brings?.*?"
        r"capital.*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",

        r"capital.*?"
        r"brings?.*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",

        r"capital.*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)"
    ]

    for p in capital_patterns:

        m = re.search(
            p,
            text,
            re.I
        )

        if m:

            new_capital = clean_number(
                m.group(1)
            )

            break

    # -----------------------------------------------------
    # 11. DETAILED OUTPUT
    # -----------------------------------------------------

    result = """
DETAILED SOLUTION — ADMISSION OF A PARTNER
================================================
"""

    result += """
STEP 1: OLD PROFIT-SHARING RATIO
---------------------------------
"""

    result += (
        "Old Partners = "
        + " : ".join(old_names)
        + "\n"
    )

    result += (
        "Old Ratio = "
        + ":".join(
            str(x)
            for x in old_ratio
        )
        + "\n"
    )

    result += (
        f"Total Ratio = {old_total}\n\n"
    )

    for i, name in enumerate(
        old_names
    ):

        result += (
            f"{name}'s Old Share "
            f"= {old_ratio[i]}/{old_total}"
            f" = {format_decimal(old_shares[i], 4)}"
            f"\n"
        )

    result += f"""

STEP 2: {new_partner}'S SHARE
-----------------------------
{new_partner} is admitted for:

= {format_decimal(new_share, 4)}
= {percentage(new_share * 100)}

Remaining share of old partners:

= 1 - {format_decimal(new_share, 4)}
= {format_decimal(remaining, 4)}
"""

    # -----------------------------------------------------
    # SACRIFICE
    # -----------------------------------------------------

    if acquisition_ratio:

        result += f"""

STEP 3: ACQUISITION / SACRIFICING RATIO
----------------------------------------

{new_partner} acquires his/her share from
the old partners in the ratio:

{" : ".join(
    str(x) for x in acquisition_ratio
)}

Therefore sacrificing ratio:

{" : ".join(
    str(x) for x in acquisition_ratio
)}
"""

    else:

        result += """

STEP 3: SACRIFICE
-----------------
No specific acquisition ratio was given.

Therefore sacrifice is calculated from:
Old Share - New Share
"""

    result += """

STEP 4: NEW PROFIT-SHARING RATIO
--------------------------------
"""

    for i, name in enumerate(
        old_names
    ):

        result += (
            f"{name}'s New Share "
            f"= Old Share - Sacrifice\n"
            f"= {format_decimal(old_shares[i],4)}"
            f" - {format_decimal(sacrifices[i],4)}"
            f"\n"
            f"= {format_decimal(new_shares[i],4)}\n\n"
        )

    result += (
        f"{new_partner}'s New Share "
        f"= {format_decimal(new_share,4)}\n\n"
    )

    ratio_values = [
        round(
            x * 1000000
        )
        for x in new_shares
    ]

    calculated_new_ratio = simplify_ratio(
        ratio_values
    )

    result += (
        "NEW PROFIT-SHARING RATIO = "
        + calculated_new_ratio
        + "\n"
    )

    # -----------------------------------------------------
    # SACRIFICING RATIO
    # -----------------------------------------------------

    sac_values = [
        round(
            x * 1000000
        )
        for x in sacrifices
    ]

    sacrifice_ratio = simplify_ratio(
        sac_values
    )

    result += (
        "\nSACRIFICING RATIO = "
        + sacrifice_ratio
        + "\n"
    )

    # -----------------------------------------------------
    # FINAL AGREED RATIO
    # -----------------------------------------------------

    if final_ratio:

        result += f"""

STEP 5: FINAL AGREED PROFIT-SHARING RATIO
-----------------------------------------

The question separately states:

FINAL AGREED RATIO
= {":".join(map(str, final_ratio))}

IMPORTANT:
This is treated separately from the
initial admission ratio calculation.
"""

    # -----------------------------------------------------
    # GOODWILL
    # -----------------------------------------------------

    if goodwill_value is not None:

        required_goodwill = (
            goodwill_value
            * new_share
        )

        result += f"""

STEP 6: GOODWILL
----------------

Goodwill of Firm
= {money(goodwill_value)}

{new_partner}'s share
= {format_decimal(new_share,4)}

{new_partner}'s share of goodwill

= {money(goodwill_value)}
  × {format_decimal(new_share,4)}

= {money(required_goodwill)}
"""

        if premium is not None:

            difference = (
                premium
                - required_goodwill
            )

            result += f"""

Actual Goodwill Premium brought by
{new_partner} = {money(premium)}

Required Goodwill Premium
= {money(required_goodwill)}

Difference
= {money(premium)}
  - {money(required_goodwill)}

= {money(abs(difference))}
"""

            if difference > 0:

                result += f"""

Therefore:

EXCESS PREMIUM = {money(difference)}

Only {money(required_goodwill)}
is treated as goodwill premium.

The excess {money(difference)}
is NOT distributed as goodwill.
It is treated as additional capital.
"""

            elif difference < 0:

                result += f"""

Therefore:

SHORTFALL IN PREMIUM = {money(abs(difference))}

Goodwill premium required
= {money(required_goodwill)}

Premium actually brought
= {money(premium)}

Shortfall
= {money(abs(difference))}
"""

            else:

                result += """

The goodwill premium brought is
exactly equal to the required amount.
"""

    elif premium is not None:

        result += f"""

STEP 6: GOODWILL PREMIUM
------------------------

Goodwill Premium brought
= {money(premium)}

It is distributed among sacrificing
partners in their sacrificing ratio.
"""

    # -----------------------------------------------------
    # GOODWILL DISTRIBUTION
    # -----------------------------------------------------

    if premium is not None:

        goodwill_to_distribute = premium

        if goodwill_value is not None:

            required = (
                goodwill_value
                * new_share
            )

            goodwill_to_distribute = min(
                premium,
                required
            )

        total_sacrifice = sum(
            sacrifices
        )

        if total_sacrifice > 0:

            result += """

GOODWILL DISTRIBUTION
---------------------
"""

            for i, name in enumerate(
                old_names
            ):

                amount = (
                    goodwill_to_distribute
                    * sacrifices[i]
                    / total_sacrifice
                )

                result += (
                    f"{name}'s share of goodwill "
                    f"= {money(amount)}\n"
                )

    # -----------------------------------------------------
    # REVALUATION
    # -----------------------------------------------------

    if (
        "revaluation" in n
        or "appreciated" in n
        or "depreciated" in n
        or "reduced" in n
        or "provision" in n
        or "unrecorded asset" in n
        or "unrecorded liability" in n
    ):

        reval = calculate_advanced_revaluation(
            text
        )

        if reval:

            result += "\n\n" + reval

    # -----------------------------------------------------
    # RESERVE
    # -----------------------------------------------------

    reserve = extract_labeled_number(
        text,
        [
            "general reserve",
            "reserve"
        ]
    )

    if reserve is not None:

        result += f"""

STEP: GENERAL RESERVE
---------------------

General Reserve = {money(reserve)}

Old ratio:
{" : ".join(map(str, old_ratio))}

Distribution:

"""

        total_old = sum(old_ratio)

        for i, name in enumerate(
            old_names
        ):

            amount = (
                reserve
                * old_ratio[i]
                / total_old
            )

            result += (
                f"{name} = {money(amount)}\n"
            )

    # -----------------------------------------------------
    # CAPITAL CONSISTENCY
    # -----------------------------------------------------

    if new_capital is not None:

        result += f"""

STEP: NEW PARTNER'S CAPITAL
---------------------------

{new_partner}'s Capital
= {money(new_capital)}
"""

        capital_share_match = re.search(
            r"capital.*?"
            r"(\d+)\s*/\s*(\d+)"
            r".*?(?:total\s+capital|capital)",
            n
        )

        if capital_share_match:

            num = float(
                capital_share_match.group(1)
            )

            den = float(
                capital_share_match.group(2)
            )

            if num != 0:

                total_capital = (
                    new_capital
                    * den
                    / num
                )

                result += f"""

If {new_partner}'s capital represents
{num}/{den} of total capital:

Total Capital
= {money(new_capital)}
  × {format_number(den)}
  / {format_number(num)}

= {money(total_capital)}
"""

                if final_ratio:

                    final_total = sum(
                        final_ratio
                    )

                    ideal_new_capital = (
                        total_capital
                        * final_ratio[-1]
                        / final_total
                    )

                    result += f"""

According to the final ratio
{":".join(map(str, final_ratio))}:

Ideal capital of {new_partner}
= {money(total_capital)}
  × {final_ratio[-1]}
  / {final_total}

= {money(ideal_new_capital)}
"""

                    if abs(
                        ideal_new_capital
                        - new_capital
                    ) > 0.01:

                        difference = (
                            new_capital
                            - ideal_new_capital
                        )

                        result += f"""

⚠️ CAPITAL ADJUSTMENT REQUIRED

Actual {new_partner}'s Capital
= {money(new_capital)}

Ideal {new_partner}'s Capital
= {money(ideal_new_capital)}

Difference
= {money(abs(difference))}

Therefore the given capital and final
profit-sharing ratio cannot both be
accepted without a capital adjustment.
"""

    # -----------------------------------------------------
    # JOURNAL ENTRIES
    # -----------------------------------------------------

    result += """

STEP: JOURNAL ENTRIES
=====================
"""

    if new_capital is not None and premium is not None:

        result += f"""

1. For capital and goodwill premium brought in cash

Bank A/c Dr.                         {money(new_capital + premium)}
      To {new_partner}'s Capital A/c              {money(new_capital)}
      To Premium for Goodwill A/c                 {money(premium)}

(Being capital and goodwill premium brought
in cash by the new partner)
"""

    elif new_capital is not None:

        result += f"""

1. For capital brought in cash

Bank A/c Dr.                         {money(new_capital)}
      To {new_partner}'s Capital A/c              {money(new_capital)}

(Being capital brought in cash)
"""

    if premium is not None:

        total_sacrifice = sum(
            sacrifices
        )

        goodwill_to_distribute = premium

        if goodwill_value is not None:

            goodwill_required = (
                goodwill_value
                * new_share
            )

            goodwill_to_distribute = min(
                premium,
                goodwill_required
            )

        if total_sacrifice > 0:

            result += f"""

2. Distribution of goodwill premium

Premium for Goodwill A/c Dr.       {money(goodwill_to_distribute)}
"""

            for i, name in enumerate(
                old_names
            ):

                amount = (
                    goodwill_to_distribute
                    * sacrifices[i]
                    / total_sacrifice
                )

                if amount > 0:

                    result += (
                        f"      To {name}'s Capital A/c"
                        f"                 {money(amount)}\n"
                    )

            result += """
(Being goodwill premium distributed among
sacrificing partners)
"""

    # -----------------------------------------------------
    # FINAL ANSWER
    # -----------------------------------------------------

    result += """

================================================
FINAL ANSWER
================================================

Initial New Ratio
= """ + calculated_new_ratio + """

Sacrificing Ratio
= """ + sacrifice_ratio + "\n"

    if final_ratio:

        result += (
            "Final Agreed Ratio\n"
            "= "
            + ":".join(
                map(str, final_ratio)
            )
            + "\n"
        )

    if goodwill_value is not None:

        result += (
            "\nFirm Goodwill = "
            + money(goodwill_value)
            + "\n"
        )

        result += (
            f"{new_partner}'s Goodwill Share = "
            + money(
                goodwill_value
                * new_share
            )
            + "\n"
        )

    return result


# =========================================================
# ADVANCED REVALUATION ENGINE
# =========================================================

def calculate_advanced_revaluation(text):

    n = normalize(text)

    gains = []
    losses = []

    # -----------------------------------------------------
    # APPRECIATION BY PERCENTAGE
    # -----------------------------------------------------

    m = re.search(
        r"land\s*(?:&|and)\s*building"
        r"\s*(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+)"
        r".*?"
        r"appreciated\s+by\s+(\d+(?:\.\d+)?)\s*%",
        text,
        re.I
    )

    if m:

        old = clean_number(
            m.group(1)
        )

        pct = clean_number(
            m.group(2)
        )

        amount = old * pct / 100

        gains.append(
            ("Land & Building", amount)
        )

    # -----------------------------------------------------
    # MACHINERY DEPRECIATION %
    # -----------------------------------------------------

    m = re.search(
        r"machinery\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+)"
        r".*?"
        r"(?:depreciated|depreciation)"
        r"\s*(?:by)?\s*"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
        re.I
    )

    if m:

        old = clean_number(
            m.group(1)
        )

        pct = clean_number(
            m.group(2)
        )

        amount = old * pct / 100

        losses.append(
            ("Machinery", amount)
        )

    # -----------------------------------------------------
    # STOCK REDUCED BY AMOUNT
    # -----------------------------------------------------

    m = re.search(
        r"stock\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"[\d,]+"
        r".*?"
        r"reduced\s+by\s+"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        text,
        re.I
    )

    if m:

        amount = clean_number(
            m.group(1)
        )

        losses.append(
            ("Stock", amount)
        )

    # -----------------------------------------------------
    # DEBTORS PROVISION
    # -----------------------------------------------------

    m = re.search(
        r"debtors?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+)"
        r".*?"
        r"provision\s*"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
        re.I
    )

    if m:

        debtors = clean_number(
            m.group(1)
        )

        pct = clean_number(
            m.group(2)
        )

        amount = debtors * pct / 100

        losses.append(
            ("Provision for Doubtful Debts",
             amount)
        )

    # -----------------------------------------------------
    # UNRECORDED ASSET
    # -----------------------------------------------------

    m = re.search(
        r"unrecorded\s+asset"
        r".*?"
        r"(?:valued|value)"
        r"\s*(?:at|of)?\s*"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        text,
        re.I
    )

    if m:

        amount = clean_number(
            m.group(1)
        )

        gains.append(
            ("Unrecorded Asset", amount)
        )

    # -----------------------------------------------------
    # UNRECORDED LIABILITY
    # -----------------------------------------------------

    m = re.search(
        r"unrecorded\s+liability"
        r".*?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        text,
        re.I
    )

    if m:

        amount = clean_number(
            m.group(1)
        )

        losses.append(
            ("Unrecorded Liability", amount)
        )

    # -----------------------------------------------------
    # GENERIC INCREASE / DECREASE
    # -----------------------------------------------------

    generic_gain = re.finditer(
        r"(\b[a-z][a-z &]+)"
        r"\s+(?:was\s+)?"
        r"(?:increased|appreciated)"
        r"\s+by\s+"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        text,
        re.I
    )

    for m in generic_gain:

        name = m.group(1).strip()

        # Don't duplicate known items
        if not any(
            name.lower()
            in x[0].lower()
            for x in gains
        ):

            amount = clean_number(
                m.group(2)
            )

            gains.append(
                (name.title(), amount)
            )

    generic_loss = re.finditer(
        r"(\b[a-z][a-z &]+)"
        r"\s+(?:was\s+)?"
        r"(?:decreased|reduced|depreciated)"
        r"\s+by\s+"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)",
        text,
        re.I
    )

    for m in generic_loss:

        name = m.group(1).strip()

        if not any(
            name.lower()
            in x[0].lower()
            for x in losses
        ):

            amount = clean_number(
                m.group(2)
            )

            losses.append(
                (name.title(), amount)
            )

    if not gains and not losses:
        return None

    total_gain = sum(
        x[1] for x in gains
    )

    total_loss = sum(
        x[1] for x in losses
    )

    result_value = (
        total_gain
        - total_loss
    )

    result = """
REVALUATION ACCOUNT
===================

REVALUATION GAINS
-----------------
"""

    for name, amount in gains:

        result += (
            f"{name} = {money(amount)}\n"
        )

    result += (
        f"\nTotal Revaluation Gains "
        f"= {money(total_gain)}\n"
    )

    result += """

REVALUATION LOSSES
------------------
"""

    for name, amount in losses:

        result += (
            f"{name} = {money(amount)}\n"
        )

    result += (
        f"\nTotal Revaluation Losses "
        f"= {money(total_loss)}\n"
    )

    result += f"""

Revaluation Result
= Total Gains - Total Losses

= {money(total_gain)}
  - {money(total_loss)}

= {money(abs(result_value))}
"""

    if result_value >= 0:

        result += (
            f"\nREVALUATION PROFIT "
            f"= {money(result_value)}\n"
        )

    else:

        result += (
            f"\nREVALUATION LOSS "
            f"= {money(abs(result_value))}\n"
        )

    return result


# =========================================================
# SIMPLE REVALUATION
# =========================================================

def solve_revaluation(text):

    n = normalize(text)

    if (
        "revaluation" not in n
        and "revalued" not in n
    ):
        return None

    result = calculate_advanced_revaluation(
        text
    )

    return result


# =========================================================
# ACCOUNTING RATIOS
# =========================================================

def solve_ratio(text):

    n = normalize(text)

    # CURRENT RATIO
    if "current ratio" in n:

        ca = extract_labeled_number(
            text,
            [
                "current assets",
                "current asset"
            ]
        )

        cl = extract_labeled_number(
            text,
            [
                "current liabilities",
                "current liability"
            ]
        )

        if ca is not None and cl is not None:

            r = safe_div(
                ca,
                cl
            )

            return f"""
DETAILED SOLUTION — CURRENT RATIO

Formula:
Current Ratio
= Current Assets / Current Liabilities

= {money(ca)} / {money(cl)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Current Ratio = {format_decimal(r)} : 1
"""

    # QUICK RATIO
    if "quick ratio" in n:

        ca = extract_labeled_number(
            text,
            ["current assets"]
        )

        inv = extract_labeled_number(
            text,
            [
                "inventory",
                "inventories"
            ]
        )

        prepaid = extract_labeled_number(
            text,
            [
                "prepaid expenses",
                "prepaid expense"
            ]
        )

        cl = extract_labeled_number(
            text,
            [
                "current liabilities"
            ]
        )

        if ca is not None and cl is not None:

            quick_assets = ca

            if inv is not None:
                quick_assets -= inv

            if prepaid is not None:
                quick_assets -= prepaid

            r = safe_div(
                quick_assets,
                cl
            )

            return f"""
DETAILED SOLUTION — QUICK RATIO

Formula:
Quick Assets
= Current Assets - Inventory
  - Prepaid Expenses

= {money(ca)}
  - {money(inv or 0)}
  - {money(prepaid or 0)}

= {money(quick_assets)}

Quick Ratio
= Quick Assets / Current Liabilities

= {money(quick_assets)}
  / {money(cl)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Quick Ratio = {format_decimal(r)} : 1
"""

    # DEBT EQUITY
    if (
        "debt equity" in n
        or "debt-equity" in n
    ):

        debt = extract_labeled_number(
            text,
            [
                "long term debt",
                "long-term debt",
                "debt"
            ]
        )

        equity = extract_labeled_number(
            text,
            [
                "shareholders funds",
                "shareholders' funds",
                "equity"
            ]
        )

        if debt is not None and equity is not None:

            r = safe_div(
                debt,
                equity
            )

            return f"""
DETAILED SOLUTION — DEBT EQUITY RATIO

Formula:
Debt Equity Ratio
= Long-term Debt / Shareholders' Funds

= {money(debt)} / {money(equity)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Debt Equity Ratio = {format_decimal(r)} : 1
"""

    # GP RATIO
    if "gross profit ratio" in n:

        gp = extract_labeled_number(
            text,
            ["gross profit"]
        )

        sales = extract_labeled_number(
            text,
            [
                "revenue from operations",
                "sales"
            ]
        )

        if gp is not None and sales is not None: 
