import os
import re
import json
import ast
import operator
from http.server import BaseHTTPRequestHandler

from openai import OpenAI


# =========================================================
# BASIC HELPERS
# =========================================================

def normalize(text):
    return str(text or "").replace(",", "").replace("₹", " ").strip()


def clean_number(n):
    try:
        n = float(n)
        if n.is_integer():
            return int(n)
        return round(n, 2)
    except Exception:
        return n


def format_number(n):
    try:
        n = float(n)
        if n.is_integer():
            return f"{int(n):,}"
        return f"{n:,.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(n)


def money(n):
    return f"₹{format_number(n)}"


def format_decimal(n):
    try:
        return f"{float(n):.4f}"
    except Exception:
        return str(n)


def percentage(n):
    try:
        return f"{float(n):.2f}%"
    except Exception:
        return str(n)


def all_numbers(text):
    text = normalize(text)
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    return [float(x) for x in matches]


def first_number(text, default=None):
    nums = all_numbers(text)
    return nums[0] if nums else default


def safe_div(a, b):
    if b == 0:
        return 0
    return a / b


def fraction_text(n, d):
    if d == 0:
        return "0"
    return f"{int(n)}/{int(d)}"


# =========================================================
# RATIO HELPERS
# =========================================================

def gcd(a, b):
    a = abs(int(a))
    b = abs(int(b))

    while b:
        a, b = b, a % b

    return a


def simplify_ratio(values):
    values = [int(round(float(x))) for x in values]

    if not values:
        return values

    g = values[0]

    for x in values[1:]:
        g = gcd(g, x)

    if g == 0:
        return values

    return [x // g for x in values]


def parse_fraction(value):
    value = str(value).strip()

    if "/" in value:
        a, b = value.split("/", 1)

        try:
            return float(a) / float(b)
        except Exception:
            return None

    try:
        return float(value)
    except Exception:
        return None


def extract_ratio(text):
    """
    Extract first two-number ratio such as:
    5:3
    2 : 1
    """

    m = re.search(r"(\d+)\s*:\s*(\d+)", text)

    if not m:
        return None

    return [int(m.group(1)), int(m.group(2))]


def extract_ratios(text):
    """
    Extract all ratios such as:
    5:3:2
    2:2:1
    4:3:2:1
    """

    matches = re.findall(
        r"(\d+(?:\s*:\s*\d+)+)",
        text
    )

    result = []

    for match in matches:
        parts = re.split(r"\s*:\s*", match)

        try:
            result.append([int(x) for x in parts])
        except Exception:
            pass

    return result


def extract_percentage(text):
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        text
    )

    if not m:
        return None

    return float(m.group(1))


def extract_share(text):
    """
    Finds fractions like:
    1/5 share
    1/4th share
    1/5th
    """

    m = re.search(
        r"(\d+)\s*/\s*(\d+)\s*(?:st|nd|rd|th)?\s*(?:share)?",
        text,
        re.I
    )

    if not m:
        return None

    return safe_div(
        float(m.group(1)),
        float(m.group(2))
    )


# =========================================================
# MONEY EXTRACTION
# =========================================================

def extract_labeled_number(text, labels):
    """
    Finds a number near a label.
    """

    if isinstance(labels, str):
        labels = [labels]

    for label in labels:

        pattern = (
            rf"{re.escape(label)}"
            rf".{{0,100}}?"
            rf"(?:₹|rs\.?|inr)?\s*"
            rf"([\d,]+(?:\.\d+)?)"
        )

        m = re.search(
            pattern,
            text,
            re.I | re.S
        )

        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except Exception:
                pass

    return None


def extract_amount_after(text, phrase):
    """
    Example:
    'capital of ₹2,50,000'
    """

    pattern = (
        rf"{re.escape(phrase)}"
        rf"\s*(?:is|of|=|:)?\s*"
        rf"(?:₹|rs\.?|inr)?\s*"
        rf"([\d,]+(?:\.\d+)?)"
    )

    m = re.search(
        pattern,
        text,
        re.I
    )

    if not m:
        return None

    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return None


def extract_goodwill_premium(text):
    """
    IMPORTANT:
    Specifically extracts the amount that belongs to
    'goodwill premium'.

    Prevents D's capital from being accidentally read
    as goodwill premium.
    """

    patterns = [

        # ₹1,00,000 as goodwill premium
        r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"
        r"\s*(?:as|towards|for)\s+goodwill\s+premium",

        # goodwill premium of ₹1,00,000
        r"goodwill\s+premium"
        r"\s*(?:of|=|:)?\s*"
        r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",

        # premium for goodwill ₹1,00,000
        r"premium\s+for\s+goodwill"
        r"\s*(?:of|=|:)?\s*"
        r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            text,
            re.I
        )

        if m:
            try:
                return float(
                    m.group(1).replace(",", "")
                )
            except Exception:
                pass

    return None


# =========================================================
# SAFE MATH
# =========================================================

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_math_node(node):

    if isinstance(node, ast.Constant):

        if isinstance(node.value, (int, float)):
            return node.value

        raise ValueError("Invalid constant")

    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.BinOp):

        op_type = type(node.op)

        if op_type not in _ALLOWED_BINOPS:
            raise ValueError("Operator not allowed")

        left = _eval_math_node(node.left)
        right = _eval_math_node(node.right)

        return _ALLOWED_BINOPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):

        op_type = type(node.op)

        if op_type not in _ALLOWED_UNARYOPS:
            raise ValueError("Operator not allowed")

        value = _eval_math_node(node.operand)

        return _ALLOWED_UNARYOPS[op_type](value)

    raise ValueError("Invalid expression")


def safe_math(expression):

    expression = str(expression)

    expression = expression.replace(",", "")
    expression = expression.replace("×", "*")
    expression = expression.replace("÷", "/")

    expression = re.sub(
        r"[^0-9+\-*/().% ]",
        "",
        expression
    )

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )

        return _eval_math_node(tree.body)

    except Exception:
        return None


# =========================================================
# GOODWILL SOLVERS
# =========================================================

def solve_goodwill_average(profits, years):

    if not profits or not years:
        return None

    avg = sum(profits) / len(profits)

    return avg * years


def solve_goodwill_super(
    average_profit,
    normal_profit,
    years
):

    super_profit = average_profit - normal_profit

    return super_profit * years


def solve_goodwill_capitalisation(
    average_profit,
    normal_rate,
    capital
):

    if normal_rate == 0:
        return None

    capitalised_value = (
        average_profit * 100 / normal_rate
    )

    return capitalised_value - capital


# =========================================================
# SUPER PROFIT
# =========================================================

def solve_super_profit(text):

    avg_profit = extract_labeled_number(
        text,
        [
            "average profit",
            "average profits"
        ]
    )

    normal_profit = extract_labeled_number(
        text,
        [
            "normal profit"
        ]
    )

    years = extract_labeled_number(
        text,
        [
            "years purchase",
            "year purchase"
        ]
    )

    if (
        avg_profit is None
        or normal_profit is None
        or years is None
    ):
        return None

    super_profit = avg_profit - normal_profit

    goodwill = super_profit * years

    return (
        "GOODWILL — SUPER PROFIT METHOD\n\n"
        f"Average Profit = {money(avg_profit)}\n"
        f"Normal Profit = {money(normal_profit)}\n\n"
        f"Super Profit = Average Profit − Normal Profit\n"
        f"= {money(avg_profit)} − {money(normal_profit)}\n"
        f"= {money(super_profit)}\n\n"
        f"Goodwill = Super Profit × Years' Purchase\n"
        f"= {money(super_profit)} × {format_number(years)}\n"
        f"= {money(goodwill)}"
    )


# =========================================================
# ADMISSION OF PARTNER
# =========================================================

def solve_admission(text):

    lower = text.lower()

    if not any(
        word in lower
        for word in [
            "admit",
            "admission",
            "admitted"
        ]
    ):
        return None

    # -----------------------------------------------------
    # STEP 1 — OLD RATIO
    # -----------------------------------------------------

    ratios = extract_ratios(text)

    old_ratio = None

    # Prefer a 3-person ratio such as 5:3:2
    for ratio in ratios:

        if len(ratio) == 3:
            old_ratio = ratio
            break

    # Fallback
    if old_ratio is None:
        for ratio in ratios:

            if len(ratio) >= 2:
                old_ratio = ratio
                break

    if old_ratio is None:
        return None

    # -----------------------------------------------------
    # STEP 2 — INCOMING PARTNER SHARE
    # -----------------------------------------------------

    incoming_share = extract_share(text)

    if incoming_share is None:
        # Try "20%" if fraction wasn't found
        pct = extract_percentage(text)

        if pct is not None:
            incoming_share = pct / 100

    if incoming_share is None:
        return None

    # -----------------------------------------------------
    # STEP 3 — ACQUISITION / SACRIFICE RATIO
    # -----------------------------------------------------

    acquisition_ratio = None

    # Search specifically around "from A, B and C"
    m = re.search(
        r"from\s+[ABC](?:\s*,\s*[ABC])*(?:\s+and\s+[ABC])?"
        r".{0,120}?"
        r"(?:ratio|share)\s*"
        r"(\d+(?:\s*:\s*\d+)+)",
        text,
        re.I | re.S
    )

    if m:
        parts = re.split(
            r"\s*:\s*",
            m.group(1)
        )

        try:
            acquisition_ratio = [
                int(x) for x in parts
            ]
        except Exception:
            acquisition_ratio = None

    # Better general fallback:
    if acquisition_ratio is None:

        for ratio in ratios:

            if (
                len(ratio) == len(old_ratio)
                and ratio != old_ratio
            ):
                acquisition_ratio = ratio
                break

    # -----------------------------------------------------
    # STEP 4 — NEW RATIO BEFORE FINAL AGREED RATIO
    # -----------------------------------------------------

    old_total = sum(old_ratio)

    new_partner_units = incoming_share

    sacrificed_units = []

    if acquisition_ratio is not None:

        acquisition_total = sum(
            acquisition_ratio
        )

        for x in acquisition_ratio:

            sacrificed_units.append(
                incoming_share
                * x
                / acquisition_total
            )

    else:

        # Equal sacrifice fallback
        equal = incoming_share / len(old_ratio)

        sacrificed_units = [
            equal
            for _ in old_ratio
        ]

    old_shares = [
        x / old_total
        for x in old_ratio
    ]

    new_old_shares = [
        old_shares[i] - sacrificed_units[i]
        for i in range(len(old_ratio))
    ]

    # Convert into common denominator
    from fractions import Fraction

    fractions = [
        Fraction(x).limit_denominator(1000)
        for x in new_old_shares
    ]

    incoming_fraction = Fraction(
        incoming_share
    ).limit_denominator(1000)

    denominator = 1

    for f in fractions + [incoming_fraction]:

        denominator = (
            denominator * f.denominator
            // gcd(
                denominator,
                f.denominator
            )
        )

    new_units = [
        int(f * denominator)
        for f in fractions
    ]

    new_units.append(
        int(incoming_fraction * denominator)
    )

    new_units = simplify_ratio(
        new_units
    )

    # -----------------------------------------------------
    # STEP 5 — FINAL AGREED RATIO
    # -----------------------------------------------------

    final_ratio = None

    for ratio in ratios:

        if len(ratio) == len(old_ratio) + 1:
            final_ratio = ratio
            break

    # -----------------------------------------------------
    # STEP 6 — GOODWILL
    # -----------------------------------------------------

    goodwill_value = extract_labeled_number(
        text,
        [
            "goodwill of firm",
            "firm's goodwill",
            "firm goodwill",
            "goodwill valued"
        ]
    )

    goodwill_due = None

    if goodwill_value is not None:
        goodwill_due = (
            goodwill_value
            * incoming_share
        )

    premium_brought = extract_goodwill_premium(
        text
    )

    # -----------------------------------------------------
    # STEP 7 — CAPITAL BROUGHT BY INCOMING PARTNER
    # -----------------------------------------------------

    incoming_capital = None

    # Specific pattern:
    # "D brings ₹2,50,000 as capital"
    m = re.search(
        r"brings?\s+"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)"
        r"\s+as\s+capital",
        text,
        re.I
    )

    if m:

        incoming_capital = float(
            m.group(1).replace(",", "")
        )

    if incoming_capital is None:

        # Capital of D
        m = re.search(
            r"\bD\b.{0,100}?"
            r"(?:capital)"
            r".{0,30}?"
            r"(?:₹|rs\.?|inr)?\s*"
            r"([\d,]+(?:\.\d+)?)",
            text,
            re.I | re.S
        )

        if m:

            try:
                incoming_capital = float(
                    m.group(1).replace(",", "")
                )
            except Exception:
                pass

    # -----------------------------------------------------
    # STEP 8 — REVALUATION
    # -----------------------------------------------------

    land_value = None
    land_appreciation = None

    m = re.search(
        r"land\s*&?\s*building"
        r".{0,100}?"
        r"([\d,]+)"
        r".{0,50}?"
        r"appreciated\s+by\s+"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
        re.I | re.S
    )

    if m:

        land_value = float(
            m.group(1).replace(",", "")
        )

        land_appreciation = (
            land_value
            * float(m.group(2))
            / 100
        )

    machinery_value = None
    machinery_depreciation = None

    m = re.search(
        r"machinery"
        r".{0,100}?"
        r"([\d,]+)"
        r".{0,50}?"
        r"depreciated\s+by\s+"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
        re.I | re.S
    )

    if m:

        machinery_value = float(
            m.group(1).replace(",", "")
        )

        machinery_depreciation = (
            machinery_value
            * float(m.group(2))
            / 100
        )

    stock_value = None
    stock_reduction = None

    m = re.search(
        r"stock"
        r".{0,80}?"
        r"([\d,]+)"
        r".{0,50}?"
        r"reduced\s+by\s+"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+)",
        text,
        re.I | re.S
    )

    if m:

        stock_value = float(
            m.group(1).replace(",", "")
        )

        stock_reduction = float(
            m.group(2).replace(",", "")
        )

    debtors_value = None
    debtor_provision = None

    m = re.search(
        r"debtors"
        r".{0,80}?"
        r"([\d,]+)"
        r".{0,80}?"
        r"provision\s+"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
        re.I | re.S
    )

    if m:

        debtors_value = float(
            m.group(1).replace(",", "")
        )

        debtor_provision = (
            debtors_value
            * float(m.group(2))
            / 100
        )

    unrecorded_asset_value = None
    unrecorded_asset_final = None

    m = re.search(
        r"unrecorded\s+asset"
        r".{0,100}?"
        r"([\d,]+)"
        r".{0,100}?"
        r"(?:valued\s+at|value\s+of)"
        r"\s*(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+)",
        text,
        re.I | re.S
    )

    if m:

        unrecorded_asset_value = float(
            m.group(1).replace(",", "")
        )

        unrecorded_asset_final = float(
            m.group(2).replace(",", "")
        )

    unrecorded_liability = None

    m = re.search(
        r"unrecorded\s+liability"
        r".{0,80}?"
        r"([\d,]+)"
        r".{0,40}?"
        r"recorded",
        text,
        re.I | re.S
    )

    if m:

        unrecorded_liability = float(
            m.group(1).replace(",", "")
        )

    # -----------------------------------------------------
    # STEP 9 — REVALUATION PROFIT
    # -----------------------------------------------------

    revaluation_profit = 0

    if land_appreciation:
        revaluation_profit += land_appreciation

    if machinery_depreciation:
        revaluation_profit -= machinery_depreciation

    if stock_reduction:
        revaluation_profit -= stock_reduction

    if debtor_provision:
        revaluation_profit -= debtor_provision

    if unrecorded_asset_final:
        revaluation_profit += unrecorded_asset_final

    if unrecorded_liability:
        revaluation_profit -= unrecorded_liability

    # -----------------------------------------------------
    # STEP 10 — GENERAL RESERVE
    # -----------------------------------------------------

    general_reserve = extract_labeled_number(
        text,
        [
            "general reserve",
            "reserve"
        ]
    )

    # Avoid picking unrelated reserve if no actual reserve
    if general_reserve is not None:

        if general_reserve <= 0:
            general_reserve = None

    # -----------------------------------------------------
    # STEP 11 — D CAPITAL REPRESENTS FRACTION
    # -----------------------------------------------------

    capital_fraction = None

    m = re.search(
        r"D['’]?\s*s?\s*capital"
        r".{0,120}?"
        r"represents\s+"
        r"(\d+)\s*/\s*(\d+)"
        r"\s*(?:th|st|nd|rd)?"
        r"\s*(?:of\s+)?"
        r"(?:the\s+)?total\s+capital",
        text,
        re.I | re.S
    )

    if m:

        capital_fraction = safe_div(
            float(m.group(1)),
            float(m.group(2))
        )

    # -----------------------------------------------------
    # BUILD RESULT
    # -----------------------------------------------------

    result = []

    result.append(
        "DETAILED SOLUTION — ADMISSION OF A PARTNER"
    )

    result.append("")

    # OLD RATIO
    result.append(
        "STEP 1 — OLD PROFIT-SHARING RATIO"
    )

    result.append(
        f"Old Ratio = {' : '.join(map(str, old_ratio))}"
    )

    result.append(
        f"Total parts = {old_total}"
    )

    old_names = ["A", "B", "C"]

    for i, ratio_part in enumerate(old_ratio):

        if i < len(old_names):

            share = ratio_part / old_total

            result.append(
                f"{old_names[i]}'s share "
                f"= {ratio_part}/{old_total} "
                f"= {percentage(share * 100)}"
            )

    result.append("")

    # INCOMING SHARE
    result.append(
        "STEP 2 — INCOMING PARTNER'S SHARE"
    )

    result.append(
        f"D's share = {fraction_text("
            int(round(incoming_share * 100)),
            100
        )}"
        f" = {percentage(incoming_share * 100)}"
    )

    result.append("")

    # SACRIFICE
    result.append(
        "STEP 3 — SACRIFICE MADE BY OLD PARTNERS"
    )

    if acquisition_ratio is not None:

        result.append(
            "D acquires his share from A, B and C "
            f"in the ratio "
            f"{' : '.join(map(str, acquisition_ratio))}."
        )

        result.append("")

        for i, sacrifice in enumerate(
            sacrificed_units
        ):

            if i < len(old_names):

                result.append(
                    f"{old_names[i]}'s sacrifice "
                    f"= D's share × "
                    f"{acquisition_ratio[i]}"
                    f"/{sum(acquisition_ratio)}"
                )

                result.append(
                    f"= {percentage(sacrifice * 100)}"
                )

    result.append("")

    # NEW RATIO
    result.append(
        "STEP 4 — NEW RATIO BEFORE FINAL AGREED RATIO"
    )

    names = ["A", "B", "C", "D"]

    ratio_text = " : ".join(
        map(str, new_units)
    )

    result.append(
        f"New Ratio = {ratio_text}"
    )

    for i, share in enumerate(
        new_old_shares + [incoming_share]
    ):

        if i < len(names):

            result.append(
                f"{names[i]}'s new share "
                f"= {percentage(share * 100)}"
            )

    result.append("")

    # SACRIFICING RATIO
    result.append(
        "STEP 5 — SACRIFICING RATIO"
    )

    if acquisition_ratio is not None:

        sacrifice_ratio = simplify_ratio(
            acquisition_ratio
        )

        result.append(
            "Sacrificing Ratio = "
            + " : ".join(
                map(str, sacrifice_ratio)
            )
        )

    else:

        result.append(
            "Sacrificing Ratio = "
            + " : ".join(
                map(str, [1] * len(old_ratio))
            )
        )

    result.append("")

    # GOODWILL
    result.append(
        "STEP 6 — GOODWILL"
    )

    if goodwill_value is not None:

        result.append(
            f"Goodwill of firm = "
            f"{money(goodwill_value)}"
        )

        result.append(
            f"D's goodwill = "
            f"{money(goodwill_value)} × "
            f"{fraction_text("
                int(round(incoming_share * 100)),
                100
            )}"
        )

        result.append(
            f"= {money(goodwill_due)}"
        )

        result.append("")

        if premium_brought is not None:

            result.append(
                f"Premium actually brought by D "
                f"= {money(premium_brought)}"
            )

            if premium_brought > goodwill_due:

                excess = (
                    premium_brought
                    - goodwill_due
                )

                result.append(
                    f"Excess premium = "
                    f"{money(premium_brought)} − "
                    f"{money(goodwill_due)}"
                )

                result.append(
                    f"= {money(excess)}"
                )

                result.append(
                    "The excess amount is treated as "
                    "additional capital."
                )

            elif premium_brought < goodwill_due:

                shortfall = (
                    goodwill_due
                    - premium_brought
                )

                result.append(
                    f"Shortfall = "
                    f"{money(goodwill_due)} − "
                    f"{money(premium_brought)}"
                )

                result.append(
                    f"= {money(shortfall)}"
                )

            else:

                result.append(
                    "Premium brought = goodwill due. "
                    "There is no excess or shortfall."
                )

        # GOODWILL DISTRIBUTION
        if acquisition_ratio is not None:

            result.append("")

            result.append(
                "Goodwill Premium Distribution:"
            )

            total_acq = sum(
                acquisition_ratio
            )

            for i, x in enumerate(
                acquisition_ratio
            ):

                if i < len(old_names):

                    amount = (
                        goodwill_due
                        * x
                        / total_acq
                    )

                    result.append(
                        f"{old_names[i]} "
                        f"= {money(amount)}"
                    )

    result.append("")

    # REVALUATION
    result.append(
        "STEP 7 — REVALUATION ACCOUNT"
    )

    if land_value is not None:

        result.append(
            f"Land & Building increase "
            f"= {money(land_appreciation)}"
        )

    if machinery_depreciation is not None:

        result.append(
            f"Machinery depreciation "
            f"= {money(machinery_depreciation)}"
        )

    if stock_reduction is not None:

        result.append(
            f"Stock reduction "
            f"= {money(stock_reduction)}"
        )

    if debtor_provision is not None:

        result.append(
            f"Provision for debtors "
            f"= {money(debtor_provision)}"
        )

    if unrecorded_asset_final is not None:

        result.append(
            f"Unrecorded asset recognised "
            f"= {money(unrecorded_asset_final)}"
        )

    if unrecorded_liability is not None:

        result.append(
            f"Unrecorded liability "
            f"= {money(unrecorded_liability)}"
        )

    result.append("")

    if revaluation_profit >= 0:

        result.append(
            f"Net Revaluation Profit "
            f"= {money(revaluation_profit)}"
        )

    else:

        result.append(
            f"Net Revaluation Loss "
            f"= {money(abs(revaluation_profit))}"
        )

    # DISTRIBUTE REVALUATION
    if old_ratio:

        result.append("")

        result.append(
            "Revaluation Profit/Loss "
            "distributed in old ratio:"
        )

        for i, part in enumerate(old_ratio):

            if i < len(old_names):

                amount = (
                    revaluation_profit
                    * part
                    / old_total
                )

                result.append(
                    f"{old_names[i]} "
                    f"= {money(amount)}"
                )

    # RESERVE
    if general_reserve is not None:

        result.append("")

        result.append(
            "STEP 8 — GENERAL RESERVE"
        )

        result.append(
            f"General Reserve = "
            f"{money(general_reserve)}"
        )

        result.append(
            "Distributed among old partners "
            "in old ratio:"
        )

        for i, part in enumerate(old_ratio):

            if i < len(old_names):

                amount = (
                    general_reserve
                    * part
                    / old_total
                )

                result.append(
                    f"{old_names[i]} "
                    f"= {money(amount)}"
                )

    # CAPITALS
    result.append("")

    result.append(
        "STEP 9 — CAPITAL ACCOUNTS"
    )

    old_capitals = []

    for name in ["A", "B", "C"]:

        cap = None

        # Find "<name>'s capital"
        m = re.search(
            rf"\b{name}\b['’]?\s*s?\s*capital"
            rf".{{0,50}}?"
            rf"(?:₹|rs\.?|inr)?\s*"
            rf"([\d,]+(?:\.\d+)?)",
            text,
            re.I | re.S
        )

        if m:

            try:
                cap = float(
                    m.group(1).replace(",", "")
                )
            except Exception:
                pass

        if cap is None:

            # "A's capital are ₹4,00,000"
            m = re.search(
                rf"\b{name}\b"
                rf".{{0,100}}?"
                rf"(?:capital)"
                rf".{{0,100}}?"
                rf"(?:₹|rs\.?|inr)?\s*"
                rf"([\d,]+(?:\.\d+)?)",
                text,
                re.I | re.S
            )

            if m:

                try:
                    cap = float(
                        m.group(1).replace(",", "")
                    )
                except Exception:
                    pass

        old_capitals.append(cap)

    # Specific pattern for capitals:
    # "A, B and C ... capitals are ₹4,00,000,
    # ₹3,00,000 and ₹2,00,000 respectively."
    if any(x is None for x in old_capitals):

        m = re.search(
            r"capitals?\s+(?:are|being)"
            r".{0,150}?"
            r"(?:₹|rs\.?|inr)?\s*([\d,]+)"
            r".{0,40}?"
            r"(?:₹|rs\.?|inr)?\s*([\d,]+)"
            r".{0,40}?"
            r"(?:₹|rs\.?|inr)?\s*([\d,]+)"
            r"\s+respectively",
            text,
            re.I | re.S
        )

        if m:

            old_capitals = [
                float(
                    m.group(i).replace(",", "")
                )
                for i in range(1, 4)
            ]

    # Capital table
    if all(
        x is not None
        for x in old_capitals
    ):

        result.append("")

        result.append(
            "Old Capitals:"
        )

        for i, cap in enumerate(
            old_capitals
        ):

            result.append(
                f"{old_names[i]} = {money(cap)}"
            )

        result.append("")

        result.append(
            "Adjusted Capitals before final "
            "capital adjustment:"
        )

        adjusted = []

        for i, cap in enumerate(
            old_capitals
        ):

            reserve_share = 0

            if general_reserve is not None:

                reserve_share = (
                    general_reserve
                    * old_ratio[i]
                    / old_total
                )

            reval_share = (
                revaluation_profit
                * old_ratio[i]
                / old_total
            )

            goodwill_credit = 0

            if (
                goodwill_due is not None
                and acquisition_ratio is not None
            ):

                goodwill_credit = (
                    goodwill_due
                    * acquisition_ratio[i]
                    / sum(acquisition_ratio)
                )

            adjusted_capital = (
                cap
                + reserve_share
                + reval_share
                + goodwill_credit
            )

            adjusted.append(
                adjusted_capital
            )

            result.append(
                f"{old_names[i]} = "
                f"{money(cap)} + "
                f"{money(reserve_share)} + "
                f"{money(reval_share)} + "
                f"{money(goodwill_credit)}"
                f" = {money(adjusted_capital)}"
            )

        if incoming_capital is not None:

            result.append(
                f"D = {money(incoming_capital)}"
            )

        # FINAL CAPITAL
        if (
            incoming_capital is not None
            and capital_fraction is not None
        ):

            total_new_capital = safe_div(
                incoming_capital,
                capital_fraction
            )

            result.append("")

            result.append(
                "STEP 10 — TOTAL NEW CAPITAL"
            )

            result.append(
                f"D's capital = "
                f"{money(incoming_capital)}"
            )

            result.append(
                f"D's capital represents "
                f"{percentage(capital_fraction * 100)} "
                f"of total capital."
            )

            result.append(
                f"Total New Capital = "
                f"{money(incoming_capital)} ÷ "
                f"{format_decimal(capital_fraction)}"
            )

            result.append(
                f"= {money(total_new_capital)}"
            )

            # Final capital according to final ratio
            if final_ratio is not None:

                total_parts = sum(final_ratio)

                result.append("")

                result.append(
                    "STEP 11 — CAPITALS ACCORDING "
                    "TO FINAL RATIO"
                )

                ideal_caps = []

                for i, part in enumerate(
                    final_ratio
                ):

                    ideal = (
                        total_new_capital
                        * part
                        / total_parts
                    )

                    ideal_caps.append(
                        ideal
                    )

                    result.append(
                        f"{names[i]} = "
                        f"{money(ideal)}"
                    )

                # Compare D capital
                if len(ideal_caps) == 4:

                    d_ideal = ideal_caps[3]

                    difference = (
                        incoming_capital
                        - d_ideal
                    )

                    result.append("")

                    if abs(difference) > 0.01:

                        result.append(
                            "IMPORTANT — CAPITAL "
                            "INCONSISTENCY"
                        )

                        if difference > 0:

                            result.append(
                                f"D has brought "
                                f"{money(difference)} "
                                f"more than the amount "
                                f"required by the final "
                                f"ratio."
                            )

                            result.append(
                                f"Required D capital = "
                                f"{money(d_ideal)}"
                            )

                            result.append(
                                f"Actual D capital = "
                                f"{money(incoming_capital)}"
                            )

                            result.append(
                                f"Excess = "
                                f"{money(difference)}"
                            )

                        else:

                            result.append(
                                f"D needs to bring "
                                f"{money(abs(difference))} "
                                f"more capital."
                            )

                    else:

                        result.append(
                            "D's capital agrees with "
                            "the final capital ratio."
                        )

                    # Adjusted capital comparison
                    adjusted_with_d = adjusted + [
                        incoming_capital
                    ]

                    result.append("")

                    result.append(
                        "CAPITAL ADJUSTMENT:"
                    )

                    for i in range(4):

                        diff = (
                            ideal_caps[i]
                            - adjusted_with_d[i]
                        )

                        if abs(diff) < 0.01:

                            result.append(
                                f"{names[i]}: "
                                "No adjustment"
                            )

                        elif diff > 0:

                            result.append(
                                f"{names[i]} brings "
                                f"{money(diff)}"
                            )

                        else:

                            result.append(
                                f"{names[i]} withdraws "
                                f"{money(abs(diff))}"
                            )

    # FINAL AGREED RATIO
    if final_ratio is not None:

        result.append("")

        result.append(
            "STEP 12 — FINAL AGREED RATIO"
        )

        result.append(
            "Final Ratio = "
            + " : ".join(
                map(str, final_ratio)
            )
        )

        result.append(
            "This final ratio is different from "
            "the admission ratio calculated above, "
            "so the capital/profit-sharing adjustment "
            "must be handled separately."
        )

    # JOURNAL ENTRIES
    result.append("")

    result.append(
        "STEP 13 — IMPORTANT JOURNAL ENTRIES"
    )

    result.append("")

    result.append(
        "1. For cash brought by D:"
    )

    if incoming_capital is not None:

        result.append(
            f"Bank A/c Dr. {money(incoming_capital)}"
        )

        result.append(
            f"    To D's Capital A/c "
            f"{money(incoming_capital)}"
        )

    if premium_brought is not None:

        result.append("")

        result.append(
            "2. For goodwill premium brought by D:"
        )

        result.append(
            f"Bank A/c Dr. {money(premium_brought)}"
        )

        result.append(
            "    To Premium for Goodwill A/c "
            f"{money(premium_brought)}"
        )

        if (
            goodwill_due is not None
            and acquisition_ratio is not None
        ):

            result.append("")

            result.append(
                "3. Distribution of goodwill "
                "premium to sacrificing partners:"
            )

            total_acq = sum(
                acquisition_ratio
            )

            for i, x in enumerate(
                acquisition_ratio
            ):

                amount = (
                    goodwill_due
                    * x
                    / total_acq
                )

                result.append(
                    f"Premium for Goodwill A/c Dr. "
                    f"{money(amount)}"
                )

                result.append(
                    f"    To {old_names[i]}'s Capital A/c "
                    f"{money(amount)}"
                )

    if revaluation_profit != 0:

        result.append("")

        result.append(
            "4. Revaluation profit/loss is "
            "transferred to old partners' "
            "capital accounts in old ratio."
        )

    if general_reserve is not None:

        result.append("")

        result.append(
            "5. General Reserve A/c Dr. "
            f"{money(general_reserve)}"
        )

        result.append(
            "    To A's Capital A/c"
        )

        result.append(
            "    To B's Capital A/c"
        )

        result.append(
            "    To C's Capital A/c"
        )

    return "\n".join(result)


# =========================================================
# ACCOUNTING RATIOS
# =========================================================

def solve_accounting_ratio(text):

    lower = text.lower()

    if "current ratio" in lower:

        current_assets = extract_labeled_number(
            text,
            [
                "current assets"
            ]
        )

        current_liabilities = extract_labeled_number(
            text,
            [
                "current liabilities"
            ]
        )

        if (
            current_assets is not None
            and current_liabilities is not None
        ):

            ratio = safe_div(
                current_assets,
                current_liabilities
            )

            return (
                "CURRENT RATIO\n\n"
                f"Current Assets = "
                f"{money(current_assets)}\n"
                f"Current Liabilities = "
                f"{money(current_liabilities)}\n\n"
                f"Current Ratio = "
                f"{money(current_assets)} ÷ "
                f"{money(current_liabilities)}\n"
                f"= {format_decimal(ratio)} : 1"
            )

    return None


# =========================================================
# SHARE CAPITAL
# =========================================================

def solve_share_capital(text):

    lower = text.lower()

    if (
        "share capital" not in lower
        and "shares" not in lower
    ):
        return None

    nums = all_numbers(text)

    if len(nums) < 2:
        return None

    return None


# =========================================================
# DEBENTURES
# =========================================================

def solve_debentures(text):

    lower = text.lower()

    if "debenture" not in lower:
        return None

    return None


# =========================================================
# CASH FLOW
# =========================================================

def solve_cash_flow(text):

    lower = text.lower()

    if (
        "cash flow" not in lower
        and "cash from operating" not in lower
    ):
        return None

    return None


# =========================================================
# BASIC MATH
# =========================================================

def solve_basic_math(text):

    cleaned = str(text).strip()

    # Don't hijack accounting questions
    if any(
        word in cleaned.lower()
        for word in [
            "partner",
            "goodwill",
            "capital account",
            "revaluation",
            "debenture",
            "balance sheet",
            "accounting",
            "profit sharing"
        ]
    ):
        return None

    # Look for simple mathematical expression
    m = re.search(
        r"(?<!\w)"
        r"(\d+(?:\.\d+)?"
        r"(?:\s*[+\-×x*/÷]\s*"
        r"\d+(?:\.\d+)?)+)"
        r"(?!\w)",
        cleaned,
        re.I
    )

    if not m:
        return None

    expression = m.group(1)

    answer = safe_math(expression)

    if answer is None:
        return None

    return (
        "SOLUTION\n\n"
        f"{expression}\n"
        f"= {format_number(answer)}"
    )


# =========================================================
# LOCAL SOLVER
# =========================================================

def local_solve(text):

    if not text:
        return None

    # Admission first because it is more specific
    result = solve_admission(text)

    if result:
        return result

    result = solve_super_profit(text)

    if result:
        return result

    result = solve_accounting_ratio(text)

    if result:
        return result

    result = solve_share_capital(text)

    if result:
        return result

    result = solve_debentures(text)

    if result:
        return result

    result = solve_cash_flow(text)

    if result:
        return result

    result = solve_basic_math(text)

    if result:
        return result

    return None


# =========================================================
# OPENAI SOLVER
# =========================================================

def solve_with_ai(question, image=None):

    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return (
            "OPENAI_API_KEY is not configured "
            "on the server."
        )

    client = OpenAI(
        api_key=api_key
    )

    system_prompt = """
You are Commerce AI, an expert Class 11/12
Accountancy and Economics solver.

Solve questions step-by-step.

For Accountancy:
- Show formulas.
- Show calculations.
- Use correct profit-sharing ratios.
- Handle admission/retirement of partners.
- Handle goodwill.
- Handle revaluation.
- Handle reserves.
- Handle capital accounts.
- Handle balance sheet.
- Show journal entries when asked.

Never skip information given in the question.

If the question contains multiple partners such as
A, B, C and D, carefully distinguish:
- old ratio
- incoming partner share
- sacrificing ratio
- new ratio
- final agreed ratio
- capital ratio

Give the final answer clearly.
"""

    user_content = []

    if question:
        user_content.append(
            {
                "type": "text",
                "text": question
            }
        )

    if image:

        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": image
                }
            }
        )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content


# =========================================================
# HTTP HANDLER
# =========================================================

class handler(BaseHTTPRequestHandler):

    def _send_json(
        self,
        status,
        data
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "POST, OPTIONS"
        )

        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):

        self._send_json(
            200,
            {
                "ok": True
            }
        )

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw_body = self.rfile.read(
                content_length
            )

            data = json.loads(
                raw_body.decode("utf-8")
            )

            question = (
                data.get("question")
                or ""
            ).strip()

            image = data.get("image")

            if not question and not image:

                self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": "Please enter a question or upload an image."
                    }
                )

                return

            # -------------------------------------------------
            # LOCAL SOLVER FIRST
            # -------------------------------------------------

            local_answer = None

            if question:

                try:
                    local_answer = local_solve(
                        question
                    )
                except Exception:
                    local_answer = None

            if local_answer:

                self._send_json(
                    200,
                    {
                        "ok": True,
                        "answer": local_answer,
                        "source": "local"
                    }
                )

                return

            # -------------------------------------------------
            # AI FALLBACK
            # -------------------------------------------------

            try:

                answer = solve_with_ai(
                    question,
                    image
                )

                self._send_json(
                    200,
                    {
                        "ok": True,
                        "answer": answer,
                        "source": "ai"
                    }
                )

            except Exception as e:

                error_text = str(e)

                # OpenAI credits exhausted
                if (
                    "credit_balance_exhausted"
                    in error_text
                    or "insufficient_quota"
                    in error_text
                    or "429" in error_text
                ):

                    self._send_json(
                        200,
                        {
                            "ok": False,
                            "error":
                                "AI credits are exhausted. "
                                "Simple calculations can still be solved locally."
                        }
                    )

                    return

                self._send_json(
                    500,
                    {
                        "ok": False,
                        "error": error_text
                    }
                )

        except Exception as e:

            self._send_json(
                500,
                {
                    "ok": False,
                    "error": str(e)
                }
    )
