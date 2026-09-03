import os
import re
import ast
import operator
import math
import json
from http.server import BaseHTTPRequestHandler


# ============================================================
# COMMERCE AI - MASTER ACCOUNTANCY SOLVER
# ============================================================
# Local engine + AI fallback
#
# PARTNERSHIP
# - Profit sharing ratio
# - Average profit
# - Weighted average profit
# - Normal profit
# - Super profit
# - Goodwill
# - Capitalisation method
# - Interest on capital
# - Interest on drawings
# - Partner salary
# - Partner commission
# - Guarantee
# - Admission
# - Sacrificing ratio
# - Retirement
# - Gaining ratio
# - Revaluation
# - Past adjustment
# - Dissolution
#
# COMPANY ACCOUNTS
# - Share issue
# - Premium
# - Oversubscription
# - Calls
# - Forfeiture
# - Reissue
# - Debentures
#
# FINANCIAL RATIOS
# - Current ratio
# - Quick ratio
# - Debt equity
# - Total assets to debt
# - Proprietary
# - Interest coverage
# - Debt to capital employed
# - Inventory turnover
# - Receivables turnover
# - Payables turnover
# - Fixed asset turnover
# - Net asset turnover
# - Working capital turnover
# - Gross profit ratio
# - Operating ratio
# - Operating profit ratio
# - Net profit ratio
# - ROI
#
# CASH FLOW
# - Basic indirect method
# ============================================================


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize(text):
    if not text:
        return ""

    text = str(text)

    replacements = {
        "₹": " rupees ",
        "Rs.": " rupees ",
        "Rs": " rupees ",
        "rs.": " rupees ",
        "rs": " rupees ",
        "×": "*",
        "÷": "/",
        "−": "-",
        "–": "-",
        "—": "-",
        "’": "'",
        "“": '"',
        "”": '"',
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    return text.lower()


def clean_number(value):
    if value is None:
        return None

    try:
        value = str(value)
        value = value.replace(",", "")
        value = value.replace("₹", "")
        value = value.replace("rupees", "")
        value = value.replace("rs.", "")
        value = value.replace("rs", "")
        value = value.replace("%", "")
        return float(value.strip())
    except Exception:
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

    except Exception:
        return str(value)


def money(value):
    return "₹" + format_number(value)


def format_decimal(value):
    if value is None:
        return "0"

    try:
        value = float(value)

        if abs(value - round(value)) < 0.000001:
            return str(int(round(value)))

        return str(round(value, 2))

    except Exception:
        return str(value)


def percentage(value):
    return f"{format_decimal(value)}%"


def all_numbers(text):
    text = normalize(text)

    matches = re.findall(
        r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?",
        text
    )

    result = []

    for x in matches:
        n = clean_number(x)
        if n is not None:
            result.append(n)

    return result


def first_number(text):
    nums = all_numbers(text)
    return nums[0] if nums else None


def safe_div(a, b):
    if b == 0:
        return None
    return a / b


def simplify_ratio(a, b):
    if a is None or b is None:
        return "0 : 0"

    try:
        a = float(a)
        b = float(b)

        if abs(a) < 0.000001 and abs(b) < 0.000001:
            return "0 : 0"

        if abs(a) < 0.000001:
            return "0 : 1"

        if abs(b) < 0.000001:
            return "1 : 0"

        scale = 1000000

        ai = round(a * scale)
        bi = round(b * scale)

        g = math.gcd(abs(ai), abs(bi))

        if g == 0:
            return f"{format_decimal(a)} : {format_decimal(b)}"

        return f"{ai // g} : {bi // g}"

    except Exception:
        return f"{format_decimal(a)} : {format_decimal(b)}"


# ============================================================
# NUMBER EXTRACTION
# ============================================================

NUMBER_PATTERN = r"(?:\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)"


def extract_percentage(text, default=None):
    t = normalize(text)

    m = re.search(
        rf"({NUMBER_PATTERN})\s*(?:%|percent|per cent)",
        t
    )

    if m:
        return clean_number(m.group(1))

    return default


def extract_years_purchase(text):
    t = normalize(text)

    m = re.search(
        rf"({NUMBER_PATTERN})\s*(?:years?|yrs?)\s*(?:purchase|p\.?a\.?)",
        t
    )

    if m:
        return clean_number(m.group(1))

    if "years purchase" in t:
        m = re.search(
            rf"({NUMBER_PATTERN})\s*years?",
            t
        )

        if m:
            return clean_number(m.group(1))

    return None


def extract_labeled_number(text, labels):
    t = normalize(text)

    for label in labels:

        # Example:
        # capital employed = 100000
        # current assets 200000
        pattern = (
            rf"{re.escape(label)}"
            rf"\s*(?:is|was|of|=|:)?"
            rf"\s*(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
        )

        m = re.search(pattern, t)

        if m:
            return clean_number(m.group(1))

        # More flexible:
        # capital employed of ₹1,00,000
        pattern = (
            rf"{re.escape(label)}"
            rf"\D{{0,40}}"
            rf"(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
        )

        m = re.search(pattern, t)

        if m:
            return clean_number(m.group(1))

    return None


# ============================================================
# IMPORTANT AMOUNT EXTRACTION
# ============================================================

def extract_amount_after(text, phrases):
    """
    Safely extracts amounts.

    Handles:
    ₹40,000 as goodwill premium
    40,000 as goodwill premium
    brings ₹40,000 as goodwill premium
    goodwill premium = ₹40,000
    goodwill premium of ₹40,000

    IMPORTANT:
    It does NOT accidentally take 1/5 or another nearby number.
    """

    t = normalize(text)

    # --------------------------------------------------------
    # Pattern 1:
    # brings rupees 40000 as goodwill premium
    # --------------------------------------------------------

    for phrase in phrases:

        pattern = (
            rf"(?:brings?|brought|pays?|paid|contributes?|"
            rf"contributed|receives?|received)"
            rf"\s+(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
            rf"\s+(?:as\s+)?"
            rf"{re.escape(phrase)}"
        )

        m = re.search(pattern, t)

        if m:
            return clean_number(m.group(1))

    # --------------------------------------------------------
    # Pattern 2:
    # goodwill premium of ₹40,000
    # goodwill premium = ₹40,000
    # --------------------------------------------------------

    for phrase in phrases:

        pattern = (
            rf"{re.escape(phrase)}"
            rf"\s*(?:is|was|of|=|:)?"
            rf"\s*(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
        )

        m = re.search(pattern, t)

        if m:
            return clean_number(m.group(1))

    # --------------------------------------------------------
    # Pattern 3:
    # ₹40,000 as goodwill premium
    # --------------------------------------------------------

    for phrase in phrases:

        pattern = (
            rf"(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
            rf"\s+as\s+"
            rf"{re.escape(phrase)}"
        )

        m = re.search(pattern, t)

        if m:
            return clean_number(m.group(1))

    return None


# ============================================================
# RATIO / FRACTION EXTRACTION
# ============================================================

def extract_ratio(text):
    t = normalize(text)

    # Prefer explicit profit-sharing ratio
    patterns = [
        r"sharing\s+profits?\s+in\s+(?:the\s+)?ratio\s+(\d+)\s*:\s*(\d+)",
        r"profit\s+sharing\s+ratio\s*(?:is|=|of)?\s*(\d+)\s*:\s*(\d+)",
        r"sharing\s+ratio\s*(?:is|=|of)?\s*(\d+)\s*:\s*(\d+)",
        r"ratio\s*(?:is|=|of)?\s*(\d+)\s*:\s*(\d+)",
        r"(\d+)\s*:\s*(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, t)

        if m:
            return (
                float(m.group(1)),
                float(m.group(2))
            )

    return None


def extract_all_ratios(text):
    t = normalize(text)

    matches = re.findall(
        r"(\d+)\s*:\s*(\d+)",
        t
    )

    return [
        (float(a), float(b))
        for a, b in matches
    ]


def extract_fraction(text):
    t = normalize(text)

    # 1/5
    m = re.search(
        r"(\d+)\s*/\s*(\d+)",
        t
    )

    if m:
        a = float(m.group(1))
        b = float(m.group(2))

        if b != 0:
            return a / b

    words = {
        "one half": 1 / 2,
        "one third": 1 / 3,
        "one fourth": 1 / 4,
        "one quarter": 1 / 4,
        "one fifth": 1 / 5,
        "one sixth": 1 / 6,
        "one seventh": 1 / 7,
        "one eighth": 1 / 8,
        "one ninth": 1 / 9,
        "one tenth": 1 / 10,

        "two fifth": 2 / 5,
        "two fifths": 2 / 5,
        "three fifth": 3 / 5,
        "three fifths": 3 / 5,
    }

    for word, value in words.items():
        if word in t:
            return value

    return None


# ============================================================
# PROFIT SERIES
# ============================================================

def extract_profit_series(text):
    t = normalize(text)

    profits = []

    patterns = [
        rf"(?:first|1st)\s*year\D{{0,30}}({NUMBER_PATTERN})",
        rf"(?:second|2nd)\s*year\D{{0,30}}({NUMBER_PATTERN})",
        rf"(?:third|3rd)\s*year\D{{0,30}}({NUMBER_PATTERN})",
        rf"(?:fourth|4th)\s*year\D{{0,30}}({NUMBER_PATTERN})",
        rf"(?:fifth|5th)\s*year\D{{0,30}}({NUMBER_PATTERN})",
    ]

    for pattern in patterns:

        m = re.search(pattern, t)

        if m:
            n = clean_number(m.group(1))

            if n is not None:
                profits.append(n)

    if len(profits) >= 2:
        return profits

    # Example:
    # profits were 10000, 12000, 15000, 18000
    m = re.search(
        r"(?:profits?|profit for the years?)"
        r"\D{0,60}"
        r"((?:\d[\d,]*(?:\.\d+)?\D*){2,})",
        t
    )

    if m:
        nums = all_numbers(m.group(1))

        if len(nums) >= 2:
            return nums

    return []


def extract_average_profit(text):
    return extract_labeled_number(
        text,
        [
            "average profit",
            "average profits",
            "avg profit",
            "avg profits",
        ]
    )


def extract_normal_profit(text):
    return extract_labeled_number(
        text,
        [
            "normal profit",
            "normal profits",
        ]
    )


def extract_super_profit(text):
    return extract_labeled_number(
        text,
        [
            "super profit",
            "super profits",
        ]
    )


def extract_capital_employed(text):
    return extract_labeled_number(
        text,
        [
            "capital employed",
            "capital employed of",
            "capital invested",
            "total capital employed",
        ]
    )


# ============================================================
# SAFE BASIC MATH
# ============================================================

_ALLOWED_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_math(expression):

    expression = expression.replace("^", "**")

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )
    except Exception:
        return None

    def evaluate(node):

        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError()

        if isinstance(node, ast.BinOp):

            op = _ALLOWED_BIN.get(
                type(node.op)
            )

            if not op:
                raise ValueError()

            left = evaluate(node.left)
            right = evaluate(node.right)

            if (
                isinstance(node.op, ast.Pow)
                and abs(right) > 20
            ):
                raise ValueError()

            return op(left, right)

        if isinstance(node, ast.UnaryOp):

            op = _ALLOWED_UNARY.get(
                type(node.op)
            )

            if not op:
                raise ValueError()

            return op(
                evaluate(node.operand)
            )

        raise ValueError()

    try:
        return evaluate(tree)

    except Exception:
        return None


def basic_math_solver(text):

    expression = text.strip()

    expression = expression.replace(
        ",",
        ""
    )

    expression = expression.replace(
        "₹",
        ""
    )

    expression = expression.replace(
        "×",
        "*"
    )

    expression = expression.replace(
        "÷",
        "/"
    )

    if not re.fullmatch(
        r"[\d\s+\-*/().^]+",
        expression
    ):
        return None

    result = safe_math(
        expression
    )

    if result is None:
        return None

    return (
        "### Answer\n\n"
        f"**{format_number(result)}**"
    )


# ============================================================
# GOODWILL - AVERAGE PROFIT
# ============================================================

def solve_average_profit_goodwill(text):

    t = normalize(text)

    if "goodwill" not in t:
        return None

    if "average profit" not in t:
        return None

    if "super profit" in t:
        return None

    avg = extract_average_profit(t)

    profits = extract_profit_series(t)

    if avg is None and len(profits) >= 2:
        avg = sum(profits) / len(profits)

    years = extract_years_purchase(t)

    if avg is None or years is None:
        return None

    goodwill = avg * years

    return "\n".join([
        "### Goodwill — Average Profit Method",
        "",
        f"Average Profit = {money(avg)}",
        f"Years' Purchase = {format_decimal(years)}",
        "",
        "Goodwill = Average Profit × Years' Purchase",
        f"= {money(avg)} × {format_decimal(years)}",
        f"= **{money(goodwill)}**",
    ])


# ============================================================
# SUPER PROFIT
# ============================================================

def solve_super_profit(text):

    t = normalize(text)

    if "super profit" not in t:
        return None

    avg = extract_average_profit(t)

    if avg is None:
        profits = extract_profit_series(t)

        if profits:
            avg = sum(profits) / len(profits)

    normal = extract_normal_profit(t)

    if normal is None:

        capital = extract_capital_employed(t)
        rate = extract_percentage(t)

        if (
            capital is not None
            and rate is not None
        ):
            normal = capital * rate / 100

    if avg is None or normal is None:
        return None

    super_profit = avg - normal

    lines = [
        "### Super Profit",
        "",
        f"Average Profit = {money(avg)}",
        f"Normal Profit = {money(normal)}",
        "",
        "Super Profit = Average Profit − Normal Profit",
        f"= {money(avg)} − {money(normal)}",
        f"= **{money(super_profit)}**",
    ]

    years = extract_years_purchase(t)

    if (
        years is not None
        and "goodwill" in t
    ):

        goodwill = (
            super_profit
            * years
        )

        lines += [
            "",
            "### Goodwill — Super Profit Method",
            "",
            "Goodwill = Super Profit × Years' Purchase",
            f"= {money(super_profit)} × {format_decimal(years)}",
            f"= **{money(goodwill)}**",
        ]

    return "\n".join(lines)


# ============================================================
# CAPITALISATION
# ============================================================

def solve_capitalisation_goodwill(text):

    t = normalize(text)

    if (
        "capitalisation" not in t
        and "capitalization" not in t
    ):
        return None

    if "goodwill" not in t:
        return None

    avg = extract_average_profit(t)
    rate = extract_percentage(t)
    capital = extract_capital_employed(t)

    if avg is None:

        profits = extract_profit_series(t)

        if profits:
            avg = sum(profits) / len(profits)

    if avg is None or rate is None:
        return None

    capitalised_value = (
        avg * 100 / rate
    )

    if capital is not None:

        goodwill = (
            capitalised_value
            - capital
        )

        return "\n".join([
            "### Goodwill — Capitalisation Method",
            "",
            f"Average Profit = {money(avg)}",
            f"Normal Rate = {percentage(rate)}",
            "",
            "Capitalised Value = Average Profit × 100 / Normal Rate",
            f"= {money(avg)} × 100 / {format_decimal(rate)}",
            f"= {money(capitalised_value)}",
            "",
            "Goodwill = Capitalised Value − Actual Capital Employed",
            f"= {money(capitalised_value)} − {money(capital)}",
            f"= **{money(goodwill)}**",
        ])

    return "\n".join([
        "### Capitalised Value",
        "",
        "Capitalised Value = Average Profit × 100 / Normal Rate",
        f"= **{money(capitalised_value)}**",
    ])


# ============================================================
# NORMAL PROFIT
# ============================================================

def solve_normal_profit_question(text):

    t = normalize(text)

    if "normal profit" not in t:
        return None

    capital = extract_capital_employed(t)
    rate = extract_percentage(t)

    if capital is None or rate is None:
        return None

    result = capital * rate / 100

    return "\n".join([
        "### Normal Profit",
        "",
        "Normal Profit = Capital Employed × Normal Rate / 100",
        f"= {money(capital)} × {format_decimal(rate)} / 100",
        f"= **{money(result)}**",
    ])


# ============================================================
# WEIGHTED AVERAGE
# ============================================================

def solve_weighted_average_profit(text):

    t = normalize(text)

    if "weighted average" not in t:
        return None

    profits = extract_profit_series(t)

    if len(profits) < 2:
        return None

    weights = []

    for m in re.finditer(
        rf"(?:weight|weights?)\D{{0,20}}({NUMBER_PATTERN})",
        t
    ):

        n = clean_number(m.group(1))

        if n is not None:
            weights.append(n)

    if len(weights) != len(profits):
        weights = list(
            range(
                1,
                len(profits) + 1
            )
        )

    weighted_total = sum(
        p * w
        for p, w in zip(
            profits,
            weights
        )
    )

    weight_total = sum(weights)

    avg = (
        weighted_total
        / weight_total
    )

    return "\n".join([
        "### Weighted Average Profit",
        "",
        "Weighted Average Profit = Σ(Profit × Weight) / ΣWeight",
        f"= {money(weighted_total)} / {format_decimal(weight_total)}",
        f"= **{money(avg)}**",
    ])


# ============================================================
# INTEREST ON CAPITAL
# ============================================================

def solve_interest_on_capital(text):

    t = normalize(text)

    if "interest on capital" not in t:
        return None

    capital = extract_labeled_number(
        t,
        [
            "capital",
            "opening capital",
            "capital account",
            "capital invested",
        ]
    )

    rate = extract_percentage(t)

    if capital is None or rate is None:
        return None

    interest = (
        capital
        * rate
        / 100
    )

    return "\n".join([
        "### Interest on Capital",
        "",
        "Interest = Capital × Rate / 100",
        f"= {money(capital)} × {format_decimal(rate)} / 100",
        f"= **{money(interest)}**",
    ])


# ============================================================
# INTEREST ON DRAWINGS
# ============================================================

def solve_interest_on_drawings(text):

    t = normalize(text)

    if "interest on drawings" not in t:
        return None

    drawings = extract_labeled_number(
        t,
        [
            "drawings",
            "drawing",
            "amount of drawings",
            "drawings made",
        ]
    )

    rate = extract_percentage(t)

    if drawings is None or rate is None:
        return None

    months = extract_labeled_number(
        t,
        [
            "months",
            "month",
        ]
    )

    if (
        months is not None
        and months <= 12
    ):

        interest = (
            drawings
            * rate
            / 100
            * months
            / 12
        )

        return "\n".join([
            "### Interest on Drawings",
            "",
            "Interest = Drawings × Rate × Time / 100",
            f"= {money(drawings)} × {format_decimal(rate)} × {format_decimal(months)}/12",
            f"= **{money(interest)}**",
        ])

    interest = (
        drawings
        * rate
        / 100
    )

    return "\n".join([
        "### Interest on Drawings",
        "",
        "Interest = Drawings × Rate / 100",
        f"= {money(drawings)} × {format_decimal(rate)} / 100",
        f"= **{money(interest)}**",
    ])


# ============================================================
# PARTNER SALARY / COMMISSION
# ============================================================

def solve_partner_salary_commission(text):

    t = normalize(text)

    if "partner" not in t:
        return None

    if (
        "salary" not in t
        and "commission" not in t
    ):
        return None

    lines = []

    salary = extract_labeled_number(
        t,
        [
            "partner salary",
            "salary to partner",
            "salary",
        ]
    )

    if salary is not None:
        lines.append(
            f"Partner Salary = **{money(salary)}**"
        )

    commission = extract_labeled_number(
        t,
        [
            "partner commission",
            "commission",
        ]
    )

    rate = extract_percentage(t)

    profit = extract_labeled_number(
        t,
        [
            "profit before commission",
            "profit before charging commission",
            "net profit",
            "profit",
        ]
    )

    if (
        commission is None
        and rate is not None
        and profit is not None
        and "commission" in t
    ):

        commission = (
            profit
            * rate
            / 100
        )

    if commission is not None:
        lines.append(
            f"Partner Commission = **{money(commission)}**"
        )

    if not lines:
        return None

    return (
        "### Partner Salary / Commission\n\n"
        + "\n".join(lines)
    )


# ============================================================
# ADMISSION OF PARTNER
# ============================================================

def solve_admission(text):

    t = normalize(text)

    admission_words = [
        "admitted",
        "admission",
        "new partner",
        "admit c",
        "admit a",
        "admit b",
    ]

    if not any(
        x in t
        for x in admission_words
    ):
        return None

    old_ratio = extract_ratio(t)

    if old_ratio is None:
        return None

    old_a, old_b = old_ratio

    old_total = (
        old_a
        + old_b
    )

    # --------------------------------------------------------
    # NEW PARTNER SHARE
    # --------------------------------------------------------

    new_share = extract_fraction(t)

    if new_share is None:

        m = re.search(
            r"for\s+(\d+)\s*/\s*(\d+)\s+share",
            t
        )

        if m:
            new_share = (
                float(m.group(1))
                / float(m.group(2))
            )

    if new_share is None:
        return None

    remaining = (
        1
        - new_share
    )

    # --------------------------------------------------------
    # CHECK WHETHER OLD PARTNERS SHARE EQUALLY
    # --------------------------------------------------------

    equal_old = any(
        phrase in t
        for phrase in [
            "share the future profits equally",
            "share future profits equally",
            "future profits equally",
            "share equally after",
            "equally after c",
            "equally after admission",
            "future profit equally",
        ]
    )

    if equal_old:

        new_a = (
            remaining / 2
        )

        new_b = (
            remaining / 2
        )

    else:

        new_a = (
            old_a
            / old_total
            * remaining
        )

        new_b = (
            old_b
            / old_total
            * remaining
        )

    new_c = new_share

    # --------------------------------------------------------
    # NEW RATIO
    # --------------------------------------------------------

    scale = 100000

    A = round(
        new_a * scale
    )

    B = round(
        new_b * scale
    )

    C = round(
        new_c * scale
    )

    g = math.gcd(
        math.gcd(
            abs(A),
            abs(B)
        ),
        abs(C)
    )

    if g:
        A //= g
        B //= g
        C //= g

    # --------------------------------------------------------
    # SACRIFICE
    # --------------------------------------------------------

    old_a_share = (
        old_a
        / old_total
    )

    old_b_share = (
        old_b
        / old_total
    )

    sacrifice_a = (
        old_a_share
        - new_a
    )

    sacrifice_b = (
        old_b_share
        - new_b
    )

    # Remove tiny floating point errors
    if abs(sacrifice_a) < 0.000001:
        sacrifice_a = 0

    if abs(sacrifice_b) < 0.000001:
        sacrifice_b = 0

    # --------------------------------------------------------
    # GOODWILL PREMIUM
    # --------------------------------------------------------

    # FIRST priority:
    # "C brings ₹40,000 as goodwill premium"
    goodwill_premium = None

    direct_patterns = [
        r"(?:brings?|brought|pays?|paid)"
        r"\s+(?:rupees\s*)?"
        rf"({NUMBER_PATTERN})"
        r"\s+as\s+goodwill\s+premium",

        r"(?:brings?|brought|pays?|paid)"
        r"\s+(?:rupees\s*)?"
        rf"({NUMBER_PATTERN})"
        r"\s+goodwill\s+premium",
    ]

    for pattern in direct_patterns:

        m = re.search(
            pattern,
            t
        )

        if m:
            goodwill_premium = clean_number(
                m.group(1)
            )
            break

    # SECOND priority:
    # goodwill premium = ₹40,000
    if goodwill_premium is None:

        goodwill_premium = extract_amount_after(
            t,
            [
                "goodwill premium",
                "premium for goodwill",
            ]
        )

    # --------------------------------------------------------
    # FIRM GOODWILL VALUATION
    # --------------------------------------------------------

    goodwill_valuation = None

    valuation_patterns = [
        rf"goodwill\s+of\s+the\s+firm\s+is\s+valued\s+at"
        rf"\s+(?:rupees\s*)?({NUMBER_PATTERN})",

        rf"goodwill\s+is\s+valued\s+at"
        rf"\s+(?:rupees\s*)?({NUMBER_PATTERN})",

        rf"goodwill\s+valued\s+at"
        rf"\s+(?:rupees\s*)?({NUMBER_PATTERN})",
    ]

    for pattern in valuation_patterns:

        m = re.search(
            pattern,
            t
        )

        if m:
            goodwill_valuation = clean_number(
                m.group(1)
            )
            break

    # If premium not directly given,
    # calculate from firm's goodwill valuation.
    if (
        goodwill_premium is None
        and goodwill_valuation is not None
    ):

        goodwill_premium = (
            goodwill_valuation
            * new_share
        )

    # --------------------------------------------------------
    # CAPITAL BROUGHT BY NEW PARTNER
    # --------------------------------------------------------

    capital = None

    # VERY IMPORTANT:
    # Capture "₹1,00,000 as capital"
    capital_patterns = [
        rf"(?:brings?|brought|contributes?|contributed)"
        rf"\s+(?:rupees\s*)?"
        rf"({NUMBER_PATTERN})"
        r"\s+as\s+capital",

        rf"(?:capital)"
        rf"\s*(?:is|of|=|:)?"
        rf"\s+(?:rupees\s*)?"
        rf"({NUMBER_PATTERN})",
    ]

    for pattern in capital_patterns:

        m = re.search(
            pattern,
            t
        )

        if m:
            candidate = clean_number(
                m.group(1)
            )

            # Don't accidentally use goodwill amount
            if (
                goodwill_premium is None
                or abs(
                    candidate
                    - goodwill_premium
                ) > 0.000001
            ):
                capital = candidate
                break

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    lines = [
        "### Admission of New Partner",
        "",
        f"Old Ratio = {format_decimal(old_a)} : {format_decimal(old_b)}",
        f"New Partner's Share = {percentage(new_share * 100)}",
        "",
        f"Remaining Share = 1 − {format_decimal(new_share)}",
        f"= {format_decimal(remaining)}",
        "",
    ]

    if equal_old:

        lines += [
            "A and B share the remaining profit equally.",
            "",
            f"A's New Share = {format_decimal(remaining)} / 2",
            f"= {format_decimal(new_a)}",
            "",
            f"B's New Share = {format_decimal(remaining)} / 2",
            f"= {format_decimal(new_b)}",
            "",
        ]

    else:

        lines += [
            "Remaining profit is distributed between A and B in their old ratio.",
            "",
            f"A's New Share = {format_decimal(new_a)}",
            f"B's New Share = {format_decimal(new_b)}",
            "",
        ]

    lines += [
        "### New Profit Sharing Ratio",
        f"A : B : C = **{A} : {B} : {C}**",
        "",
        "### Sacrificing Ratio",
        f"A sacrifices = {format_decimal(sacrifice_a)}",
        f"B sacrifices = {format_decimal(sacrifice_b)}",
    ]

    if (
        sacrifice_a == 0
        and sacrifice_b == 0
    ):
        sacrifice_ratio = "0 : 0"

    elif sacrifice_b == 0:
        sacrifice_ratio = "1 : 0"

    elif sacrifice_a == 0:
        sacrifice_ratio = "0 : 1"

    else:
        sacrifice_ratio = simplify_ratio(
            sacrifice_a,
            sacrifice_b
        )

    lines.append(
        f"Sacrificing Ratio = **{sacrifice_ratio}**"
    )

    # --------------------------------------------------------
    # GOODWILL
    # --------------------------------------------------------

    if goodwill_premium is not None:

        lines += [
            "",
            "### Goodwill",
            f"Goodwill Premium brought by C = **{money(goodwill_premium)}**",
        ]

        if (
            sacrifice_a > 0
            and sacrifice_b > 0
        ):

            total_sacrifice = (
                sacrifice_a
                + sacrifice_b
            )

            a_credit = (
                goodwill_premium
                * sacrifice_a
                / total_sacrifice
            )

            b_credit = (
                goodwill_premium
                * sacrifice_b
                / total_sacrifice
            )

            lines += [
                "",
                f"A's share of goodwill = **{money(a_credit)}**",
                f"B's share of goodwill = **{money(b_credit)}**",
            ]

        elif sacrifice_a > 0:

            a_credit = goodwill_premium

            lines += [
                "",
                f"Entire goodwill premium goes to A = **{money(a_credit)}**",
            ]

        elif sacrifice_b > 0:

            b_credit = goodwill_premium

            lines += [
                "",
                f"Entire goodwill premium goes to B = **{money(b_credit)}**",
            ]

        # ----------------------------------------------------
        # JOURNAL ENTRIES
        # ----------------------------------------------------

        if capital is not None:

            total_bank = (
                capital
                + goodwill_premium
            )

            lines += [
                "",
                "### Journal Entries",
                "",
                f"**Bank A/c Dr. ₹{format_number(total_bank)}**",
                "",
                f"    To C's Capital A/c ₹{format_number(capital)}",
                "",
                f"    To Premium for Goodwill A/c ₹{format_number(goodwill_premium)}",
                "",
            ]

            lines.append(
                f"**Premium for Goodwill A/c Dr. ₹{format_number(goodwill_premium)}**"
            )

            if (
                sacrifice_a > 0
                and sacrifice_b > 0
            ):

                total_sacrifice = (
                    sacrifice_a
                    + sacrifice_b
                )

                a_credit = (
                    goodwill_premium
                    * sacrifice_a
                    / total_sacrifice
                )

                b_credit = (
                    goodwill_premium
                    * sacrifice_b
                    / total_sacrifice
                )

                lines += [
                    "",
                    f"    To A's Capital A/c ₹{format_number(a_credit)}",
                    "",
                    f"    To B's Capital A/c ₹{format_number(b_credit)}",
                ]

            elif sacrifice_a > 0:

                lines += [
                    "",
                    f"    To A's Capital A/c ₹{format_number(goodwill_premium)}",
                ]

            elif sacrifice_b > 0:

                lines += [
                    "",
                    f"    To B's Capital A/c ₹{format_number(goodwill_premium)}",
                ]

    return "\n".join(lines)


# ============================================================
# RETIREMENT
# ============================================================

def solve_retirement(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "retires",
            "retirement",
            "retiring partner",
            "retire",
        ]
    ):
        return None

    ratios = extract_all_ratios(t)

    if not ratios:
        return None

    old_a, old_b = ratios[0]

    lines = [
        "### Retirement of Partner",
        "",
        f"Old Ratio = {format_decimal(old_a)} : {format_decimal(old_b)}",
    ]

    if len(ratios) >= 2:

        new_a, new_b = ratios[1]

        old_total = (
            old_a
            + old_b
        )

        new_total = (
            new_a
            + new_b
        )

        old_a_share = (
            old_a
            / old_total
        )

        old_b_share = (
            old_b
            / old_total
        )

        new_a_share = (
            new_a
            / new_total
        )

        new_b_share = (
            new_b
            / new_total
        )

        gain_a = (
            new_a_share
            - old_a_share
        )

        gain_b = (
            new_b_share
            - old_b_share
        )

        lines += [
            f"New Ratio = {format_decimal(new_a)} : {format_decimal(new_b)}",
            "",
            "### Gaining Ratio",
            f"A's Gain = {format_decimal(gain_a)}",
            f"B's Gain = {format_decimal(gain_b)}",
            "",
            f"Gaining Ratio = **{simplify_ratio(gain_a, gain_b)}**",
        ]

    return "\n".join(lines)


# ============================================================
# REVALUATION
# ============================================================

def solve_revaluation(text):

    t = normalize(text)

    if (
        "revaluation" not in t
        and "revaluation account" not in t
    ):
        return None

    increase = extract_labeled_number(
        t,
        [
            "increase in asset",
            "increase in value of asset",
            "asset increased",
        ]
    )

    decrease = extract_labeled_number(
        t,
        [
            "decrease in asset",
            "decrease in value of asset",
            "asset decreased",
        ]
    )

    liability_increase = extract_labeled_number(
        t,
        [
            "increase in liability",
            "liability increased",
        ]
    )

    liability_decrease = extract_labeled_number(
        t,
        [
            "decrease in liability",
            "liability decreased",
        ]
    )

    if all(
        x is None
        for x in [
            increase,
            decrease,
            liability_increase,
            liability_decrease,
        ]
    ):
        return None

    profit = (
        (increase or 0)
        + (liability_decrease or 0)
        - (decrease or 0)
        - (liability_increase or 0)
    )

    return "\n".join([
        "### Revaluation Account",
        "",
        "Profit on Revaluation = Increase in Assets + Decrease in Liabilities",
        "− Decrease in Assets − Increase in Liabilities",
        "",
        f"= {money(increase or 0)} + {money(liability_decrease or 0)}",
        f"− {money(decrease or 0)} − {money(liability_increase or 0)}",
        "",
        f"Net Revaluation Result = **{money(profit)}**",
    ])


# ============================================================
# PAST ADJUSTMENT
# ============================================================

def solve_past_adjustment(text):

    t = normalize(text)

    if (
        "past adjustment" not in t
        and "past adjustments" not in t
    ):
        return None

    return "\n".join([
        "### Past Adjustment",
        "",
        "Past adjustment is made through the Partners' Capital/Current Accounts.",
        "",
        "Method:",
        "1. Calculate the amount each partner should receive.",
        "2. Calculate the amount actually received.",
        "3. Find the difference.",
        "4. Pass one adjustment entry for the net difference.",
    ])


# ============================================================
# GUARANTEE
# ============================================================

def solve_guarantee(text):

    t = normalize(text)

    if "guarantee" not in t:
        return None

    guaranteed = extract_labeled_number(
        t,
        [
            "guaranteed profit",
            "profit guaranteed",
            "minimum profit",
        ]
    )

    actual = extract_labeled_number(
        t,
        [
            "actual profit",
            "actual share of profit",
        ]
    )

    if guaranteed is None:
        return None

    lines = [
        "### Guarantee of Profit",
        "",
        f"Guaranteed Profit = {money(guaranteed)}",
    ]

    if actual is not None:

        deficiency = max(
            guaranteed - actual,
            0
        )

        lines += [
            f"Actual Profit = {money(actual)}",
            "",
            "Deficiency = Guaranteed Profit − Actual Profit",
            f"= {money(guaranteed)} − {money(actual)}",
            f"= **{money(deficiency)}**",
        ]

    return "\n".join(lines)


# ============================================================
# DISSOLUTION
# ============================================================

def solve_dissolution(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "dissolution",
            "realisation account",
            "realization account",
        ]
    ):
        return None

    assets = extract_labeled_number(
        t,
        [
            "assets realised",
            "assets realized",
            "assets sold for",
        ]
    )

    liabilities = extract_labeled_number(
        t,
        [
            "liabilities paid",
            "liabilities settled",
            "liabilities discharged",
        ]
    )

    expenses = extract_labeled_number(
        t,
        [
            "realisation expenses",
            "realization expenses",
        ]
    )

    if (
        assets is None
        and liabilities is None
        and expenses is None
    ):
        return None

    result = (
        (assets or 0)
        - (liabilities or 0)
        - (expenses or 0)
    )

    lines = [
        "### Dissolution / Realisation",
        "",
    ]

    if assets is not None:
        lines.append(
            f"Assets Realised = {money(assets)}"
        )

    if liabilities is not None:
        lines.append(
            f"Liabilities Paid = {money(liabilities)}"
        )

    if expenses is not None:
        lines.append(
            f"Realisation Expenses = {money(expenses)}"
        )

    lines += [
        "",
        f"Basic net realisation amount = **{money(result)}**",
    ]

    return "\n".join(lines)


# ============================================================
# CURRENT RATIO
# ============================================================

def solve_current_ratio(text):

    t = normalize(text)

    if "current ratio" not in t:
        return None

    # Don't trigger for quick ratio
    if "quick ratio" in t:
        return None

    ca = extract_labeled_number(
        t,
        [
            "current assets",
            "current asset",
        ]
    )

    cl = extract_labeled_number(
        t,
        [
            "current liabilities",
            "current liability",
        ]
    )

    if ca is None or cl is None:
        return None

    result = ca / cl

    return "\n".join([
        "### Current Ratio",
        "",
        "Current Ratio = Current Assets / Current Liabilities",
        f"= {money(ca)} / {money(cl)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# QUICK RATIO
# ============================================================

def solve_quick_ratio(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "quick ratio",
            "liquid ratio",
            "acid test ratio",
        ]
    ):
        return None

    quick_assets = extract_labeled_number(
        t,
        [
            "quick assets",
            "liquid assets",
            "quick asset",
        ]
    )

    current_liabilities = extract_labeled_number(
        t,
        [
            "current liabilities",
            "current liability",
        ]
    )

    if quick_assets is None:

        current_assets = extract_labeled_number(
            t,
            [
                "current assets",
                "current asset",
            ]
        )

        inventory = extract_labeled_number(
            t,
            [
                "inventory",
                "inventories",
                "stock",
            ]
        )

        prepaid = extract_labeled_number(
            t,
            [
                "prepaid expenses",
                "prepaid expense",
                "prepaid",
            ]
        )

        if current_assets is not None:

            quick_assets = current_assets

            if inventory is not None:
                quick_assets -= inventory

            if prepaid is not None:
                quick_assets -= prepaid

    if (
        quick_assets is None
        or current_liabilities is None
    ):
        return None

    result = (
        quick_assets
        / current_liabilities
    )

    return "\n".join([
        "### Quick Ratio",
        "",
        "Quick Assets = Current Assets − Inventory − Prepaid Expenses",
        f"Quick Assets = {money(quick_assets)}",
        "",
        "Quick Ratio = Quick Assets / Current Liabilities",
        f"= {money(quick_assets)} / {money(current_liabilities)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# DEBT EQUITY
# ============================================================

def solve_debt_equity(text):

    t = normalize(text)

    if "debt equity ratio" not in t:
        return None

    debt = extract_labeled_number(
        t,
        [
            "long term debt",
            "long-term debt",
            "long term borrowings",
            "long-term borrowings",
            "debt",
        ]
    )

    equity = extract_labeled_number(
        t,
        [
            "shareholders funds",
            "shareholders' funds",
            "shareholder funds",
            "owners funds",
            "proprietors funds",
            "equity",
        ]
    )

    if debt is None or equity is None:
        return None

    result = debt / equity

    return "\n".join([
        "### Debt-Equity Ratio",
        "",
        "Debt-Equity Ratio = Long-term Debt / Shareholders' Funds",
        f"= {money(debt)} / {money(equity)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# TOTAL ASSETS TO DEBT
# ============================================================

def solve_total_assets_debt(text):

    t = normalize(text)

    if "total assets to debt" not in t:
        return None

    assets = extract_labeled_number(
        t,
        [
            "total assets",
            "total asset",
        ]
    )

    debt = extract_labeled_number(
        t,
        [
            "long term debt",
            "long-term debt",
            "debt",
        ]
    )

    if assets is None or debt is None:
        return None

    result = assets / debt

    return "\n".join([
        "### Total Assets to Debt Ratio",
        "",
        "Ratio = Total Assets / Long-term Debt",
        f"= {money(assets)} / {money(debt)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# PROPRIETARY RATIO
# ============================================================

def solve_proprietary_ratio(text):

    t = normalize(text)

    if "proprietary ratio" not in t:
        return None

    funds = extract_labeled_number(
        t,
        [
            "shareholders funds",
            "shareholders' funds",
            "proprietors funds",
            "proprietary funds",
            "owners funds",
        ]
    )

    assets = extract_labeled_number(
        t,
        [
            "total assets",
            "total asset",
        ]
    )

    if funds is None or assets is None:
        return None

    result = funds / assets

    return "\n".join([
        "### Proprietary Ratio",
        "",
        "Proprietary Ratio = Shareholders' Funds / Total Assets",
        f"= {money(funds)} / {money(assets)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# INTEREST COVERAGE
# ============================================================

def solve_interest_coverage(text):

    t = normalize(text)

    if "interest coverage ratio" not in t:
        return None

    ebit = extract_labeled_number(
        t,
        [
            "profit before interest and tax",
            "profit before interest & tax",
            "ebit",
        ]
    )

    interest = extract_labeled_number(
        t,
        [
            "interest expense",
            "interest",
        ]
    )

    if ebit is None or interest is None:
        return None

    result = ebit / interest

    return "\n".join([
        "### Interest Coverage Ratio",
        "",
        "Interest Coverage Ratio = EBIT / Interest",
        f"= {money(ebit)} / {money(interest)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# DEBT TO CAPITAL EMPLOYED
# ============================================================

def solve_debt_capital_employed(text):

    t = normalize(text)

    if "debt to capital employed" not in t:
        return None

    debt = extract_labeled_number(
        t,
        [
            "long term debt",
            "long-term debt",
            "debt",
        ]
    )

    capital = extract_capital_employed(t)

    if debt is None or capital is None:
        return None

    result = debt / capital

    return "\n".join([
        "### Debt to Capital Employed Ratio",
        "",
        "Ratio = Long-term Debt / Capital Employed",
        f"= {money(debt)} / {money(capital)}",
        f"= **{format_decimal(result)} : 1**",
    ])


# ============================================================
# INVENTORY TURNOVER
# ============================================================

def solve_inventory_turnover(text):

    t = normalize(text)

    if "inventory turnover" not in t:
        return None

    cost = extract_labeled_number(
        t,
        [
            "cost of goods sold",
            "cost of goods sold",
            "cost of sales",
            "cost of revenue",
        ]
    )

    average_inventory = extract_labeled_number(
        t,
        [
            "average inventory",
            "average inventories",
            "average stock",
        ]
    )

    if average_inventory is None:

        opening = extract_labeled_number(
            t,
            [
                "opening inventory",
                "opening stock",
            ]
        )

        closing = extract_labeled_number(
            t,
            [
                "closing inventory",
                "closing stock",
            ]
        )

        if (
            opening is not None
            and closing is not None
        ):
            average_inventory = (
                opening
                + closing
            ) / 2

    if (
        cost is None
        or average_inventory is None
    ):
        return None

    result = (
        cost
        / average_inventory
    )

    return "\n".join([
        "### Inventory Turnover Ratio",
        "",
        "Inventory Turnover Ratio = Cost of Goods Sold / Average Inventory",
        f"= {money(cost)} / {money(average_inventory)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# RECEIVABLES TURNOVER
# ============================================================

def solve_receivables_turnover(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "trade receivables turnover",
            "receivables turnover",
            "debtors turnover",
        ]
    ):
        return None

    sales = extract_labeled_number(
        t,
        [
            "net credit sales",
            "credit sales",
            "credit revenue",
        ]
    )

    avg = extract_labeled_number(
        t,
        [
            "average trade receivables",
            "average receivables",
            "average debtors",
        ]
    )

    if avg is None:

        opening = extract_labeled_number(
            t,
            [
                "opening trade receivables",
                "opening receivables",
                "opening debtors",
            ]
        )

        closing = extract_labeled_number(
            t,
            [
                "closing trade receivables",
                "closing receivables",
                "closing debtors",
            ]
        )

        if (
            opening is not None
            and closing is not None
        ):
            avg = (
                opening
                + closing
            ) / 2

    if sales is None or avg is None:
        return None

    result = sales / avg

    return "\n".join([
        "### Trade Receivables Turnover Ratio",
        "",
        "Ratio = Net Credit Sales / Average Trade Receivables",
        f"= {money(sales)} / {money(avg)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# PAYABLES TURNOVER
# ============================================================

def solve_payables_turnover(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "trade payables turnover",
            "payables turnover",
            "creditors turnover",
        ]
    ):
        return None

    purchases = extract_labeled_number(
        t,
        [
            "net credit purchases",
            "credit purchases",
        ]
    )

    avg = extract_labeled_number(
        t,
        [
            "average trade payables",
            "average payables",
            "average creditors",
        ]
    )

    if avg is None:

        opening = extract_labeled_number(
            t,
            [
                "opening trade payables",
                "opening payables",
                "opening creditors",
            ]
        )

        closing = extract_labeled_number(
            t,
            [
                "closing trade payables",
                "closing payables",
                "closing creditors",
            ]
        )

        if (
            opening is not None
            and closing is not None
        ):
            avg = (
                opening
                + closing
            ) / 2

    if purchases is None or avg is None:
        return None

    result = purchases / avg

    return "\n".join([
        "### Trade Payables Turnover Ratio",
        "",
        "Ratio = Net Credit Purchases / Average Trade Payables",
        f"= {money(purchases)} / {money(avg)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# FIXED ASSET TURNOVER
# ============================================================

def solve_fixed_asset_turnover(text):

    t = normalize(text)

    if "fixed asset turnover" not in t:
        return None

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "net sales",
            "sales",
        ]
    )

    assets = extract_labeled_number(
        t,
        [
            "net fixed assets",
            "fixed assets",
            "fixed asset",
        ]
    )

    if revenue is None or assets is None:
        return None

    result = revenue / assets

    return "\n".join([
        "### Fixed Asset Turnover Ratio",
        "",
        "Ratio = Revenue / Net Fixed Assets",
        f"= {money(revenue)} / {money(assets)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# NET ASSET TURNOVER
# ============================================================

def solve_net_asset_turnover(text):

    t = normalize(text)

    if "net asset turnover" not in t:
        return None

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
        ]
    )

    assets = extract_labeled_number(
        t,
        [
            "net assets",
            "net asset",
        ]
    )

    if revenue is None or assets is None:
        return None

    result = revenue / assets

    return "\n".join([
        "### Net Asset Turnover Ratio",
        "",
        "Ratio = Revenue / Net Assets",
        f"= {money(revenue)} / {money(assets)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# WORKING CAPITAL TURNOVER
# ============================================================

def solve_working_capital_turnover(text):

    t = normalize(text)

    if "working capital turnover" not in t:
        return None

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
        ]
    )

    working_capital = extract_labeled_number(
        t,
        [
            "working capital",
        ]
    )

    if working_capital is None:

        ca = extract_labeled_number(
            t,
            [
                "current assets",
            ]
        )

        cl = extract_labeled_number(
            t,
            [
                "current liabilities",
            ]
        )

        if (
            ca is not None
            and cl is not None
        ):
            working_capital = (
                ca - cl
            )

    if (
        revenue is None
        or working_capital is None
    ):
        return None

    result = (
        revenue
        / working_capital
    )

    return "\n".join([
        "### Working Capital Turnover Ratio",
        "",
        f"Working Capital = {money(working_capital)}",
        "",
        "Working Capital Turnover Ratio = Revenue / Working Capital",
        f"= {money(revenue)} / {money(working_capital)}",
        f"= **{format_decimal(result)} times**",
    ])


# ============================================================
# GROSS PROFIT RATIO
# ============================================================

def solve_gp_ratio(text):

    t = normalize(text)

    if "gross profit ratio" not in t:
        return None

    gp = extract_labeled_number(
        t,
        [
            "gross profit",
            "gross profits",
        ]
    )

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "net sales",
            "sales",
        ]
    )

    if gp is None or revenue is None:
        return None

    result = (
        gp
        / revenue
        * 100
    )

    return "\n".join([
        "### Gross Profit Ratio",
        "",
        "Gross Profit Ratio = Gross Profit / Revenue × 100",
        f"= {money(gp)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


# ============================================================
# OPERATING RATIO
# ============================================================

def solve_operating_ratio(text):

    t = normalize(text)

    if "operating ratio" not in t:
        return None

    if "operating profit ratio" in t:
        return None

    cost = extract_labeled_number(
        t,
        [
            "operating cost",
            "operating costs",
        ]
    )

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
        ]
    )

    if cost is None or revenue is None:
        return None

    result = (
        cost
        / revenue
        * 100
    )

    return "\n".join([
        "### Operating Ratio",
        "",
        "Operating Ratio = Operating Cost / Revenue × 100",
        f"= {money(cost)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


# ============================================================
# OPERATING PROFIT RATIO
# ============================================================

def solve_operating_profit_ratio(text):

    t = normalize(text)

    if "operating profit ratio" not in t:
        return None

    profit = extract_labeled_number(
        t,
        [
            "operating profit",
            "operating profits",
        ]
    )

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
        ]
    )

    if profit is None or revenue is None:
        return None

    result = (
        profit
        / revenue
        * 100
    )

    return "\n".join([
        "### Operating Profit Ratio",
        "",
        "Operating Profit Ratio = Operating Profit / Revenue × 100",
        f"= {money(profit)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


# ============================================================
# NET PROFIT RATIO
# ============================================================

def solve_net_profit_ratio(text):

    t = normalize(text)

    if "net profit ratio" not in t:
        return None

    profit = extract_labeled_number(
        t,
        [
            "net profit",
            "net profits",
        ]
    )

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
        ]
    )

    if profit is None or revenue is None:
        return None

    result = (
        profit
        / revenue
        * 100
    )

    return "\n".join([
        "### Net Profit Ratio",
        "",
        "Net Profit Ratio = Net Profit / Revenue × 100",
        f"= {money(profit)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


# ============================================================
# ROI
# ============================================================

def solve_roi(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "return on investment",
            "return on capital employed",
            "roi",
        ]
    ):
        return None

    profit = extract_labeled_number(
        t,
        [
            "operating profit",
            "profit before interest and tax",
            "ebit",
        ]
    )

    capital = extract_capital_employed(t)

    if profit is None or capital is None:
        return None

    result = (
        profit
        / capital
        * 100
    )

    return "\n".join([
        "### Return on Investment",
        "",
        "ROI = Operating Profit / Capital Employed × 100",
        f"= {money(profit)} / {money(capital)} × 100",
        f"= **{percentage(result)}**",
    ])


# ============================================================
# SHARE ISSUE
# ============================================================

def solve_share_issue(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "shares",
            "share capital",
            "share issue",
            "equity shares",
        ]
    ):
        return None

    if (
        "ratio" in t
        and "share capital" not in t
    ):
        return None

    face = extract_labeled_number(
        t,
        [
            "face value per share",
            "nominal value per share",
            "face value",
            "nominal value",
        ]
    )

    if face is None:

        m = re.search(
            rf"shares?\s+(?:of|at)"
            rf"\s+(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})\s*each",
            t
        )

        if m:
            face = clean_number(
                m.group(1)
            )

    issue_price = extract_labeled_number(
        t,
        [
            "issue price per share",
            "issue price",
        ]
    )

    if issue_price is None:

        m = re.search(
            rf"issued?\s+(?:at|for)"
            rf"\s+(?:rupees\s*)?"
            rf"({NUMBER_PATTERN})"
            rf"\s*per\s*share",
            t
        )

        if m:
            issue_price = clean_number(
                m.group(1)
            )

    if face is None or issue_price is None:
        return None

    premium = (
        issue_price
        - face
    )

    lines = [
        "### Share Issue",
        "",
        f"Face Value per Share = {money(face)}",
        f"Issue Price per Share = {money(issue_price)}",
        "",
    ]

    if premium > 0:

        lines += [
            "Share Premium = Issue Price − Face Value",
            f"= {money(issue_price)} − {money(face)}",
            f"= **{money(premium)} per share**",
        ]

    elif premium < 0:

        lines += [
            "Discount = Face Value − Issue Price",
            f"= {money(face)} − {money(issue_price)}",
            f"= **{money(abs(premium))} per share**",
        ]

    else:

        lines.append(
            "**Issued at Par**"
        )

    return "\n".join(lines)


# ============================================================
# OVERSUBSCRIPTION
# ============================================================

def solve_oversubscription(text):

    t = normalize(text)

    if (
        "oversubscription" not in t
        and "oversubscribed" not in t
    ):
        return None

    offered = extract_labeled_number(
        t,
        [
            "shares offered",
            "shares issued",
            "shares offered to public",
        ]
    )

    applied = extract_labeled_number(
        t,
        [
            "shares applied for",
            "shares applied",
            "applications received for",
        ]
    )

    if offered is None or applied is None:
        return None

    excess = (
        applied
        - offered
    )

    ratio = (
        applied
        / offered
    )

    return "\n".join([
        "### Oversubscription",
        "",
        f"Shares Applied = {format_number(applied)}",
        f"Shares Offered = {format_number(offered)}",
        "",
        f"Oversubscription = **{format_number(excess)} shares**",
        f"Subscription Ratio = **{format_decimal(ratio)} times**",
    ])


# ============================================================
# FORFEITURE
# ============================================================

def solve_forfeiture(text):

    t = normalize(text)

    if (
        "forfeit" not in t
        and "forfeiture" not in t
    ):
        return None

    called = extract_labeled_number(
        t,
        [
            "called up",
            "called-up",
            "called",
        ]
    )

    received = extract_labeled_number(
        t,
        [
            "amount received",
            "amount paid",
            "amount already paid",
            "paid up",
        ]
    )

    if called is None or received is None:
        return None

    unpaid = (
        called
        - received
    )

    return "\n".join([
        "### Forfeiture of Shares",
        "",
        f"Called-up Amount = {money(called)}",
        f"Amount Received = {money(received)}",
        f"Unpaid Amount = {money(unpaid)}",
        "",
        f"Share Forfeiture A/c = **{money(received)}**",
    ])


# ============================================================
# REISSUE
# ============================================================

def solve_reissue(text):

    t = normalize(text)

    if (
        "reissue" not in t
        and "re-issued" not in t
        and "re-issue" not in t
    ):
        return None

    face = extract_labeled_number(
        t,
        [
            "face value",
            "nominal value",
        ]
    )

    reissue_price = extract_labeled_number(
        t,
        [
            "reissue price",
            "reissued at",
            "re-issue price",
        ]
    )

    forfeited = extract_labeled_number(
        t,
        [
            "amount forfeited",
            "forfeited amount",
            "share forfeiture",
        ]
    )

    if face is None or reissue_price is None:
        return None

    discount = max(
        face - reissue_price,
        0
    )

    lines = [
        "### Reissue of Forfeited Shares",
        "",
        f"Face Value = {money(face)}",
        f"Reissue Price = {money(reissue_price)}",
        f"Discount on Reissue = **{money(discount)}**",
    ]

    if forfeited is not None:

        reserve = max(
            forfeited
            - discount,
            0
        )

        lines += [
            "",
            f"Amount in Share Forfeiture A/c = {money(forfeited)}",
            "",
            "Capital Reserve = Share Forfeiture − Reissue Discount",
            f"= {money(forfeited)} − {money(discount)}",
            f"= **{money(reserve)}**",
        ]

    return "\n".join(lines)


# ============================================================
# DEBENTURES
# ============================================================

def solve_debenture(text):

    t = normalize(text)

    if (
        "debenture" not in t
        and "debentures" not in t
    ):
        return None

    face = extract_labeled_number(
        t,
        [
            "face value",
            "nominal value",
        ]
    )

    issue_price = extract_labeled_number(
        t,
        [
            "issue price",
            "issued at",
        ]
    )

    rate = extract_percentage(t)

    lines = [
        "### Debentures",
        "",
    ]

    if face is not None:

        lines.append(
            f"Face Value = {money(face)}"
        )

    if (
        face is not None
        and issue_price is not None
    ):

        difference = (
            issue_price
            - face
        )

        if difference > 0:

            lines += [
                f"Issue Price = {money(issue_price)}",
                f"Premium = **{money(difference)}**",
            ]

        elif difference < 0:

            lines += [
                f"Issue Price = {money(issue_price)}",
                f"Discount = **{money(abs(difference))}**",
            ]

        else:

            lines.append(
                "Issued at Par."
            )

    if (
        face is not None
        and rate is not None
    ):

        interest = (
            face
            * rate
            / 100
        )

        lines += [
            "",
            f"Interest Rate = {percentage(rate)}",
            f"Annual Interest = {money(face)} × {format_decimal(rate)} / 100",
            f"= **{money(interest)}**",
        ]

    if len(lines) <= 2:
        return None

    return "\n".join(lines)


# ============================================================
# CASH FLOW
# ============================================================

def solve_cash_flow(text):

    t = normalize(text)

    if not any(
        x in t
        for x in [
            "cash flow",
            "cash flows",
            "cash flow statement",
        ]
    ):
        return None

    profit = extract_labeled_number(
        t,
        [
            "profit after tax",
            "profit after tax",
            "net profit",
            "profit",
        ]
    )

    if profit is None:
        return None

    depreciation = extract_labeled_number(
        t,
        [
            "depreciation",
            "depreciation charged",
        ]
    )

    amortisation = extract_labeled_number(
        t,
        [
            "amortisation",
            "amortization",
        ]
    )

    gain = extract_labeled_number(
        t,
        [
            "gain on sale",
            "profit on sale",
            "profit on sale of asset",
        ]
    )

    loss = extract_labeled_number(
        t,
        [
            "loss on sale",
            "loss on sale of asset",
        ]
    )

    cfo = profit

    lines = [
        "### Cash Flow from Operating Activities",
        "",
        f"Profit = {money(profit)}",
    ]

    if depreciation is not None:

        cfo += depreciation

        lines.append(
            f"Add: Depreciation = {money(depreciation)}"
        )

    if amortisation is not None:

        cfo += amortisation

        lines.append(
            f"Add: Amortisation = {money(amortisation)}"
        )

    if gain is not None:

        cfo -= gain

        lines.append(
            f"Less: Gain on Sale = {money(gain)}"
        )

    if loss is not None:

        cfo += loss

        lines.append(
            f"Add: Loss on Sale = {money(loss)}"
        )

    lines += [
        "",
        f"Cash from Operating Activities before Working Capital Changes = **{money(cfo)}**",
    ]

    return "\n".join(lines)


# ============================================================
# MASTER LOCAL SOLVER
# ============================================================

def local_solve(question):

    q = question or ""

    # --------------------------------------------------------
    # BASIC MATH
    # --------------------------------------------------------

    result = basic_math_solver(q)

    if result:
        return result

    # --------------------------------------------------------
    # PARTNERSHIP
    # --------------------------------------------------------

    result = solve_admission(q)

    if result:
        return result

    result = solve_retirement(q)

    if result:
        return result

    result = solve_past_adjustment(q)

    if result:
        return result

    result = solve_guarantee(q)

    if result:
        return result

    result = solve_revaluation(q)

    if result:
        return result

    result = solve_dissolution(q)

    if result:
        return result

    result = solve_weighted_average_profit(q)

    if result:
        return result

    result = solve_capitalisation_goodwill(q)

    if result:
        return result

    result = solve_super_profit(q)

    if result:
        return result

    result = solve_average_profit_goodwill(q)

    if result:
        return result

    result = solve_normal_profit_question(q)

    if result:
        return result

    result = solve_interest_on_capital(q)

    if result:
        return result

    result = solve_interest_on_drawings(q)

    if result:
        return result

    result = solve_partner_salary_commission(q)

    if result:
        return result

    # --------------------------------------------------------
    # RATIOS
    # --------------------------------------------------------

    result = solve_quick_ratio(q)

    if result:
        return result

    result = solve_current_ratio(q)

    if result:
        return result

    result = solve_debt_equity(q)

    if result:
        return result

    result = solve_total_assets_debt(q)

    if result:
        return result

    result = solve_proprietary_ratio(q)

    if result:
        return result

    result = solve_interest_coverage(q)

    if result:
        return result

    result = solve_debt_capital_employed(q)

    if result:
        return result

    result = solve_inventory_turnover(q)

    if result:
        return result

    result = solve_receivables_turnover(q)

    if result:
        return result

    result = solve_payables_turnover(q)

    if result:
        return result

    result = solve_fixed_asset_turnover(q)

    if result:
        return result

    result = solve_net_asset_turnover(q)

    if result:
        return result

    result = solve_working_capital_turnover(q)

    if result:
        return result

    result = solve_gp_ratio(q)

    if result:
        return result

    result = solve_operating_profit_ratio(q)

    if result:
        return result

    result = solve_operating_ratio(q)

    if result:
        return result

    result = solve_net_profit_ratio(q)

    if result:
        return result

    result = solve_roi(q)

    if result:
        return result

    # --------------------------------------------------------
    # COMPANY ACCOUNTS
    # --------------------------------------------------------

    result = solve_forfeiture(q)

    if result:
        return result

    result = solve_reissue(q)

    if result:
        return result

    result = solve_oversubscription(q)

    if result:
        return result

    result = solve_share_issue(q)

    if result:
        return result

    result = solve_debenture(q)

    if result:
        return result

    # --------------------------------------------------------
    # CASH FLOW
    # --------------------------------------------------------

    result = solve_cash_flow(q)

    if result:
        return result

    return None


# ============================================================
# AI FALLBACK
# ============================================================

def ai_solve(question, image_data=None):

    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:

        return {
            "success": False,
            "error": "OPENAI_API_KEY is not configured."
        }

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=api_key
        )

        system_prompt = """
You are Commerce AI, an expert Class 12 CBSE Accountancy solver.

Solve the complete question accurately.

IMPORTANT RULES:

1. Read the entire question before solving.
2. Identify the correct chapter and accounting method.
3. Never ignore any condition given in the question.
4. Show formula.
5. Show substitution.
6. Show calculations step by step.
7. Give final answer clearly.
8. Use Indian accounting terminology.
9. Use ₹ for Indian currency.
10. For partnership questions carefully calculate:
   - old ratio
   - new ratio
   - sacrificing ratio
   - gaining ratio
   - goodwill
   - revaluation
   - reserves
   - capital/current accounts
   - journal entries
11. For admission, if old partners change their ratio independently,
    use the explicitly stated new ratio instead of assuming old ratio.
12. For company accounts, give proper journal entries.
13. For ratios, use the correct CBSE formula.
14. For cash flow, classify items correctly.
15. Do not invent missing information.
16. If information is missing, clearly state what is missing.
17. Give the final numerical answer in bold.
"""

        content = []

        if question:

            content.append({
                "type": "input_text",
                "text": question
            })

        if image_data:

            content.append({
                "type": "input_image",
                "image_url": image_data
            })

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        answer = getattr(
            response,
            "output_text",
            None
        )

        if not answer:
            answer = str(response)

        return {
            "success": True,
            "answer": answer,
            "source": "ai",
            "api_used": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
            "source": "ai",
            "api_used": True
        }


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):

    def send_json(
        self,
        data,
        status=200
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
            "Access-Control-Allow-Methods",
            "POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):

        self.send_json({
            "success": True
        })

    def do_GET(self):

        self.send_json({
            "success": True,
            "message": "Commerce AI Accountancy API is running."
        })

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(
                content_length
            )

            data = json.loads(
                body.decode("utf-8")
            )

            question = data.get(
                "question",
                ""
            )

            image = data.get(
                "image",
                None
            )

            if (
                not question
                and not image
            ):

                self.send_json(
                    {
                        "success": False,
                        "error": "Please provide a question or image."
                    },
                    400
                )

                return

            # ------------------------------------------------
            # LOCAL ENGINE FIRST
            # ------------------------------------------------

            if question:

                answer = local_solve(
                    question
                )

                if answer:

                    self.send_json({
                        "success": True,
                        "answer": answer,
                        "source": "local",
                        "api_used": False
                    })

                    return

            # ------------------------------------------------
            # AI FALLBACK
            # ------------------------------------------------

            result = ai_solve(
                question,
                image
            )

            if result.get("success"):

                self.send_json(
                    result,
                    200
                )

            else:

                self.send_json(
                    result,
                    500
                )

        except json.JSONDecodeError:

            self.send_json(
                {
                    "success": False,
                    "error": "Invalid JSON request."
                },
                400
            )

        except Exception as e:

            self.send_json(
                {
                    "success": False,
                    "error": str(e)
                },
                500
            )


# ============================================================
# VERCEL ENTRY POINT
# ============================================================

handler = Handler
