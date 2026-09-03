import os
import re
import ast
import operator
import math
import base64
import json
from http.server import BaseHTTPRequestHandler

# ============================================================
# COMMERCE AI - MASTER ACCOUNTANCY SOLVER
# ============================================================
# Covers major Class 12 Accountancy numerical patterns:
#
# PARTNERSHIP
# - Profit sharing ratio
# - Average profit
# - Weighted average profit
# - Goodwill - average profit method
# - Goodwill - super profit method
# - Goodwill - capitalization of average profit
# - Goodwill - capitalization of super profit
# - Normal profit
# - Super profit
# - Interest on capital
# - Interest on drawings
# - Partner salary
# - Partner commission
# - Guarantee of profit
# - Admission
# - New profit sharing ratio
# - Sacrificing ratio
# - Goodwill premium
# - Retirement
# - Gaining ratio
# - Revaluation basics
# - Past adjustment basics
# - Dissolution basics
#
# COMPANY ACCOUNTS
# - Share issue
# - Shares at par
# - Shares at premium
# - Oversubscription
# - Calls
# - Calls in arrears
# - Calls in advance
# - Forfeiture
# - Reissue
# - Debentures basics
#
# FINANCIAL STATEMENT ANALYSIS
# - Current ratio
# - Quick ratio
# - Debt equity ratio
# - Total assets to debt ratio
# - Proprietary ratio
# - Interest coverage ratio
# - Debt to capital employed ratio
# - Inventory turnover ratio
# - Trade receivables turnover ratio
# - Trade payables turnover ratio
# - Fixed asset turnover ratio
# - Net asset turnover ratio
# - Working capital turnover ratio
# - Gross profit ratio
# - Operating ratio
# - Operating profit ratio
# - Net profit ratio
# - ROI
#
# CASH FLOW
# - Basic indirect method calculations
#
# ============================================================


# ------------------------------------------------------------
# BASIC HELPERS
# ------------------------------------------------------------

def clean_number(value):
    if value is None:
        return None

    try:
        value = str(value)
        value = value.replace(",", "")
        value = value.replace("₹", "")
        value = value.replace("Rs.", "")
        value = value.replace("Rs", "")
        value = value.replace("rs.", "")
        value = value.replace("rs", "")
        value = value.replace("%", "")
        value = value.strip()

        return float(value)
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


def money(value):
    return "₹" + format_number(value)


def percentage(value):
    return f"{format_decimal(value)}%"


def safe_div(a, b):
    if b == 0:
        return None
    return a / b


def simplify_ratio(a, b):
    if a is None or b is None:
        return None

    try:
        a = float(a)
        b = float(b)

        if a == 0 and b == 0:
            return "0 : 0"

        scale = 1000000
        ai = round(a * scale)
        bi = round(b * scale)

        g = math.gcd(abs(ai), abs(bi))

        if g == 0:
            return f"{format_decimal(a)} : {format_decimal(b)}"

        x = ai // g
        y = bi // g

        return f"{x} : {y}"

    except Exception:
        return f"{format_decimal(a)} : {format_decimal(b)}"


def normalize(text):
    if not text:
        return ""

    text = str(text)

    replacements = {
        "₹": " rupees ",
        "rs.": " rupees ",
        "rs": " rupees ",
        "Rs.": " rupees ",
        "Rs": " rupees ",
        "—": "-",
        "–": "-",
        "×": "*",
        "÷": "/",
        "−": "-",
        "“": '"',
        "”": '"',
        "’": "'",
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    return text.lower()


# ------------------------------------------------------------
# NUMBER EXTRACTION
# ------------------------------------------------------------

NUMBER = r"(?:(?:\d+(?:,\d{3})*)|(?:\d+)(?:\.\d+)?)"


def all_numbers(text):
    text = normalize(text)

    found = re.findall(
        r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?",
        text
    )

    result = []

    for x in found:
        n = clean_number(x)
        if n is not None:
            result.append(n)

    return result


def first_number(text):
    nums = all_numbers(text)
    return nums[0] if nums else None


def extract_percentage(text, default=None):
    text = normalize(text)

    m = re.search(
        rf"({NUMBER})\s*(?:%|percent|per cent)",
        text
    )

    if m:
        return clean_number(m.group(1))

    return default


def extract_years_purchase(text):
    text = normalize(text)

    m = re.search(
        rf"({NUMBER})\s*(?:years?|yrs?)\s*(?:purchase|p\.?a\.?)",
        text
    )

    if m:
        return clean_number(m.group(1))

    m = re.search(
        rf"({NUMBER})\s*(?:years?|yrs?)",
        text
    )

    if "purchase" in text and m:
        return clean_number(m.group(1))

    return None


def extract_labeled_number(text, labels):
    text = normalize(text)

    label_pattern = "|".join(re.escape(x) for x in labels)

    m = re.search(
        rf"(?:{label_pattern})\s*(?:is|was|of|=|:)?\s*{NUMBER}",
        text
    )

    if m:
        return clean_number(m.group(0).split()[-1])

    # More reliable second pass
    for label in labels:
        m = re.search(
            rf"{re.escape(label)}\D{{0,30}}({NUMBER})",
            text
        )

        if m:
            return clean_number(m.group(1))

    return None


def extract_amount_after(text, phrases):
    text = normalize(text)

    for phrase in phrases:
        m = re.search(
            rf"{re.escape(phrase)}\D{{0,40}}({NUMBER})",
            text
        )

        if m:
            return clean_number(m.group(1))

    return None


def extract_capital_employed(text):
    return extract_labeled_number(
        text,
        [
            "capital employed",
            "capital employed of",
            "capital invested",
            "total capital",
        ]
    )


def extract_average_profit(text):
    return extract_labeled_number(
        text,
        [
            "average profit",
            "avg profit",
            "average profits",
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


# ------------------------------------------------------------
# RATIO EXTRACTION
# ------------------------------------------------------------

def extract_ratio(text):
    text = normalize(text)

    patterns = [
        r"(\d+)\s*:\s*(\d+)",
        r"ratio\s*(?:of|is|=)?\s*(\d+)\s*:\s*(\d+)",
        r"sharing\s*(?:profits\s*)?(?:in\s*)?(?:the\s*)?ratio\s*(\d+)\s*:\s*(\d+)",
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return float(m.group(1)), float(m.group(2))

    return None


def extract_all_ratios(text):
    text = normalize(text)

    matches = re.findall(
        r"(\d+)\s*:\s*(\d+)",
        text
    )

    return [(float(a), float(b)) for a, b in matches]


def extract_fraction(text):
    text = normalize(text)

    m = re.search(r"(\d+)\s*/\s*(\d+)", text)

    if m:
        a = float(m.group(1))
        b = float(m.group(2))

        if b != 0:
            return a / b

    # one fifth, one fourth etc.
    words = {
        "one half": 1 / 2,
        "one third": 1 / 3,
        "one fourth": 1 / 4,
        "one quarter": 1 / 4,
        "one fifth": 1 / 5,
        "one sixth": 1 / 6,
        "one seventh": 1 / 7,
        "one eighth": 1 / 8,
        "one tenth": 1 / 10,
        "two fifth": 2 / 5,
        "two fifths": 2 / 5,
        "three fifth": 3 / 5,
        "three fifths": 3 / 5,
    }

    for word, value in words.items():
        if word in text:
            return value

    return None


# ------------------------------------------------------------
# HISTORICAL PROFITS
# ------------------------------------------------------------

def extract_profit_series(text):
    text = normalize(text)

    profits = []

    patterns = [
        rf"(?:first|1st)\s*year\D{{0,30}}({NUMBER})",
        rf"(?:second|2nd)\s*year\D{{0,30}}({NUMBER})",
        rf"(?:third|3rd)\s*year\D{{0,30}}({NUMBER})",
        rf"(?:fourth|4th)\s*year\D{{0,30}}({NUMBER})",
        rf"(?:fifth|5th)\s*year\D{{0,30}}({NUMBER})",
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            profits.append(clean_number(m.group(1)))

    if len(profits) >= 2:
        return profits

    # "profits were 10000, 12000, 15000, 18000"
    m = re.search(
        r"(?:profits?|profit for the years?)\D{0,50}"
        r"((?:\d[\d,]*(?:\.\d+)?\D*){2,})",
        text
    )

    if m:
        nums = all_numbers(m.group(1))

        if len(nums) >= 2:
            return nums

    return []


# ------------------------------------------------------------
# SAFE BASIC MATH
# ------------------------------------------------------------

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
        tree = ast.parse(expression, mode="eval")
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
            op = _ALLOWED_BIN.get(type(node.op))
            if not op:
                raise ValueError()

            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 20:
                raise ValueError()

            return op(left, right)

        if isinstance(node, ast.UnaryOp):
            op = _ALLOWED_UNARY.get(type(node.op))
            if not op:
                raise ValueError()

            return op(evaluate(node.operand))

        raise ValueError()

    try:
        return evaluate(tree)
    except Exception:
        return None


def basic_math_solver(text):
    raw = text.strip()

    # Remove currency symbols
    expr = raw.replace(",", "")
    expr = expr.replace("₹", "")
    expr = expr.replace("×", "*")
    expr = expr.replace("÷", "/")
    expr = expr.replace("^", "**")

    # Only treat as basic math if the whole question is basically math
    if not re.fullmatch(r"[\d\s+\-*/().^%]+", expr):
        return None

    # Percent notation
    if "%" in expr:
        return None

    result = safe_math(expr)

    if result is None:
        return None

    return (
        "### Answer\n"
        f"{format_number(result)}"
    )


# ------------------------------------------------------------
# PARTNERSHIP - GOODWILL
# ------------------------------------------------------------

def solve_average_profit_goodwill(text):
    t = normalize(text)

    if not (
        "goodwill" in t
        and ("average profit" in t or "average profits" in t)
    ):
        return None

    # If "super profit" is mentioned, don't use this method
    if "super profit" in t:
        return None

    profits = extract_profit_series(t)
    avg = extract_average_profit(t)

    if avg is None and len(profits) >= 2:
        avg = sum(profits) / len(profits)

    years = extract_years_purchase(t)

    if avg is None or years is None:
        return None

    goodwill = avg * years

    lines = [
        "### Goodwill — Average Profit Method",
        "",
        f"Average Profit = {money(avg)}",
        f"Years' Purchase = {format_decimal(years)}",
        "",
        f"Goodwill = Average Profit × Years' Purchase",
        f"= {money(avg)} × {format_decimal(years)}",
        f"= **{money(goodwill)}**",
    ]

    return "\n".join(lines)


def solve_super_profit(text):
    t = normalize(text)

    if "super profit" not in t:
        return None

    avg = extract_average_profit(t)
    normal = extract_normal_profit(t)

    if avg is None:
        profits = extract_profit_series(t)
        if profits:
            avg = sum(profits) / len(profits)

    if normal is None:
        # Normal profit can be calculated:
        # Capital employed × Normal Rate / 100
        capital = extract_capital_employed(t)
        rate = extract_percentage(t)

        if capital is not None and rate is not None:
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

    if years is not None and "goodwill" in t:
        goodwill = super_profit * years

        lines += [
            "",
            "### Goodwill by Super Profit Method",
            "",
            f"Goodwill = Super Profit × Years' Purchase",
            f"= {money(super_profit)} × {format_decimal(years)}",
            f"= **{money(goodwill)}**",
        ]

    return "\n".join(lines)


def solve_capitalisation_goodwill(text):
    t = normalize(text)

    if "capitalisation" not in t and "capitalization" not in t:
        return None

    if "goodwill" not in t:
        return None

    capital = extract_capital_employed(t)
    avg = extract_average_profit(t)
    rate = extract_percentage(t)

    if avg is None:
        profits = extract_profit_series(t)
        if profits:
            avg = sum(profits) / len(profits)

    if avg is None or rate is None:
        return None

    capitalised_value = avg * 100 / rate

    if capital is not None:
        goodwill = capitalised_value - capital

        return "\n".join([
            "### Goodwill — Capitalisation of Average Profit Method",
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
        "### Capitalised Value of Business",
        "",
        f"Average Profit = {money(avg)}",
        f"Normal Rate = {percentage(rate)}",
        "",
        "Capitalised Value = Average Profit × 100 / Normal Rate",
        f"= **{money(capitalised_value)}**",
    ])


# ------------------------------------------------------------
# NORMAL PROFIT
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# WEIGHTED AVERAGE PROFIT
# ------------------------------------------------------------

def solve_weighted_average_profit(text):
    t = normalize(text)

    if "weighted average" not in t:
        return None

    profits = extract_profit_series(t)

    if len(profits) < 2:
        return None

    # Try to detect explicit weights
    weights = []

    for m in re.finditer(
        rf"(?:weight|weights?)\D{{0,20}}({NUMBER})",
        t
    ):
        n = clean_number(m.group(1))
        if n is not None:
            weights.append(n)

    if len(weights) != len(profits):
        # Standard 1,2,3... weighting
        weights = list(range(1, len(profits) + 1))

    weighted_total = sum(
        p * w for p, w in zip(profits, weights)
    )

    weight_total = sum(weights)

    avg = weighted_total / weight_total

    return "\n".join([
        "### Weighted Average Profit",
        "",
        "Weighted Average Profit",
        f"= Σ(Profit × Weight) / ΣWeight",
        f"= {money(weighted_total)} / {format_decimal(weight_total)}",
        f"= **{money(avg)}**",
    ])


# ------------------------------------------------------------
# INTEREST ON CAPITAL
# ------------------------------------------------------------

def solve_interest_on_capital(text):
    t = normalize(text)

    if "interest on capital" not in t:
        return None

    capital = extract_labeled_number(
        t,
        [
            "capital",
            "capital account",
            "opening capital",
            "capital invested",
        ]
    )

    rate = extract_percentage(t)

    if capital is None or rate is None:
        return None

    interest = capital * rate / 100

    return "\n".join([
        "### Interest on Capital",
        "",
        "Interest = Capital × Rate / 100",
        f"= {money(capital)} × {format_decimal(rate)} / 100",
        f"= **{money(interest)}**",
    ])


# ------------------------------------------------------------
# INTEREST ON DRAWINGS
# ------------------------------------------------------------

def solve_interest_on_drawings(text):
    t = normalize(text)

    if "interest on drawings" not in t:
        return None

    amount = extract_labeled_number(
        t,
        [
            "drawings",
            "drawing",
            "drawings made",
            "amount of drawings",
        ]
    )

    rate = extract_percentage(t)

    if amount is None or rate is None:
        return None

    # Months/days if explicitly available
    months = extract_labeled_number(
        t,
        [
            "months",
            "month",
        ]
    )

    if months is not None and months <= 12:
        interest = amount * rate / 100 * months / 12

        return "\n".join([
            "### Interest on Drawings",
            "",
            "Interest = Drawings × Rate × Time / 100",
            f"= {money(amount)} × {format_decimal(rate)}% × {format_decimal(months)}/12",
            f"= **{money(interest)}**",
        ])

    interest = amount * rate / 100

    return "\n".join([
        "### Interest on Drawings",
        "",
        "Interest = Drawings × Rate / 100",
        f"= {money(amount)} × {format_decimal(rate)} / 100",
        f"= **{money(interest)}**",
    ])


# ------------------------------------------------------------
# SALARY / COMMISSION
# ------------------------------------------------------------

def solve_partner_salary_commission(text):
    t = normalize(text)

    if not (
        "partner" in t
        and ("salary" in t or "commission" in t)
    ):
        return None

    results = []

    salary = extract_labeled_number(
        t,
        [
            "salary",
            "partner salary",
            "salary to partner",
        ]
    )

    if salary is not None:
        results.append(
            f"Partner Salary = **{money(salary)}**"
        )

    commission = extract_labeled_number(
        t,
        [
            "commission",
            "partner commission",
        ]
    )

    rate = extract_percentage(t)

    profit = extract_labeled_number(
        t,
        [
            "profit",
            "net profit",
            "profit before commission",
            "profit before charging commission",
        ]
    )

    if commission is None and rate is not None and profit is not None:
        commission = profit * rate / 100

    if commission is not None:
        results.append(
            f"Partner Commission = **{money(commission)}**"
        )

    if not results:
        return None

    return "### Partner Salary / Commission\n\n" + "\n".join(results)


# ------------------------------------------------------------
# ADMISSION
# ------------------------------------------------------------

def solve_admission(text):
    t = normalize(text)

    admission_words = [
        "admitted",
        "admission of",
        "new partner",
        "admit c",
        "admit a",
        "admit b",
    ]

    if not any(x in t for x in admission_words):
        return None

    ratio = extract_ratio(t)

    if ratio is None:
        return None

    old_a, old_b = ratio
    old_total = old_a + old_b

    # New partner share
    new_share = extract_fraction(t)

    if new_share is None:
        # e.g. "C is admitted for 1/5 share"
        m = re.search(
            r"for\s+(\d+)\s*/\s*(\d+)\s+share",
            t
        )

        if m:
            new_share = float(m.group(1)) / float(m.group(2))

    if new_share is None:
        return None

    remaining = 1 - new_share

    # Explicit equal sharing among old partners
    equal_old = any(
        phrase in t
        for phrase in [
            "share the future profits equally",
            "share future profits equally",
            "future profits equally",
            "share equally after",
            "equally after c",
            "equally after admission",
        ]
    )

    if equal_old:
        new_a = remaining / 2
        new_b = remaining / 2
    else:
        new_a = (old_a / old_total) * remaining
        new_b = (old_b / old_total) * remaining

    new_c = new_share

    # Convert to whole-number ratio
    common = 100000

    A = round(new_a * common)
    B = round(new_b * common)
    C = round(new_c * common)

    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))

    if g:
        A //= g
        B //= g
        C //= g

    # Sacrifice
    old_a_share = old_a / old_total
    old_b_share = old_b / old_total

    sacrifice_a = old_a_share - new_a
    sacrifice_b = old_b_share - new_b

    # Goodwill premium
    goodwill_premium = extract_amount_after(
        t,
        [
            "goodwill premium",
            "premium for goodwill",
            "brings goodwill",
            "brings as goodwill",
        ]
    )

    goodwill_valuation = extract_amount_after(
        t,
        [
            "goodwill of the firm is valued at",
            "goodwill is valued at",
            "goodwill valued at",
            "goodwill of the firm",
        ]
    )

    # If valuation is given and new partner share is known
    if goodwill_premium is None and goodwill_valuation is not None:
        goodwill_premium = goodwill_valuation * new_share

    capital = extract_amount_after(
        t,
        [
            "brings",
            "brings capital",
            "brings as capital",
            "capital",
        ]
    )

    # Avoid accidentally treating goodwill as capital
    if capital is not None and goodwill_premium is not None:
        if abs(capital - goodwill_premium) < 0.0001:
            capital = None

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

    # Convert sacrifice to ratio
    sa = round(sacrifice_a * common)
    sb = round(sacrifice_b * common)

    if sa == 0 and sb == 0:
        sacrifice_ratio = "0 : 0"
    elif sb == 0:
        sacrifice_ratio = "1 : 0"
    elif sa == 0:
        sacrifice_ratio = "0 : 1"
    else:
        sacrifice_ratio = simplify_ratio(sa, sb)

    lines += [
        f"Sacrificing Ratio = **{sacrifice_ratio}**",
    ]

    if goodwill_premium is not None:
        lines += [
            "",
            "### Goodwill",
            f"Goodwill Premium brought by C = **{money(goodwill_premium)}**",
        ]

        if sacrifice_a > 0 and sacrifice_b > 0:
            total_sacrifice = sacrifice_a + sacrifice_b

            a_credit = goodwill_premium * sacrifice_a / total_sacrifice
            b_credit = goodwill_premium * sacrifice_b / total_sacrifice

            lines += [
                "",
                f"A's share of goodwill = {money(a_credit)}",
                f"B's share of goodwill = {money(b_credit)}",
            ]

        elif sacrifice_a > 0:
            lines += [
                "",
                f"Entire goodwill premium goes to A = **{money(goodwill_premium)}**",
            ]

        elif sacrifice_b > 0:
            lines += [
                "",
                f"Entire goodwill premium goes to B = **{money(goodwill_premium)}**",
            ]

        if capital is not None:
            lines += [
                "",
                "### Journal Entries",
                "",
                "**Bank A/c Dr.** " + money(capital + goodwill_premium),
                "",
                "    To C's Capital A/c " + money(capital),
                "",
                "    To Premium for Goodwill A/c " + money(goodwill_premium),
                "",
                "Premium for Goodwill A/c Dr. " + money(goodwill_premium),
            ]

            if sacrifice_a > 0 and sacrifice_b > 0:
                total_sacrifice = sacrifice_a + sacrifice_b
                a_credit = goodwill_premium * sacrifice_a / total_sacrifice
                b_credit = goodwill_premium * sacrifice_b / total_sacrifice

                lines += [
                    "",
                    "    To A's Capital A/c " + money(a_credit),
                    "",
                    "    To B's Capital A/c " + money(b_credit),
                ]

            elif sacrifice_a > 0:
                lines += [
                    "",
                    "    To A's Capital A/c " + money(goodwill_premium),
                ]

            elif sacrifice_b > 0:
                lines += [
                    "",
                    "    To B's Capital A/c " + money(goodwill_premium),
                ]

    return "\n".join(lines)


# ------------------------------------------------------------
# RETIREMENT
# ------------------------------------------------------------

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

    ratio = extract_ratio(t)

    if ratio is None:
        return None

    old_a, old_b = ratio

    new_ratio = None

    ratios = extract_all_ratios(t)

    if len(ratios) >= 2:
        new_ratio = ratios[1]

    lines = [
        "### Retirement of Partner",
        "",
        f"Old Profit Sharing Ratio = {format_decimal(old_a)} : {format_decimal(old_b)}",
    ]

    if new_ratio:
        na, nb = new_ratio

        old_total = old_a + old_b
        new_total = na + nb

        old_a_share = old_a / old_total
        old_b_share = old_b / old_total

        new_a_share = na / new_total
        new_b_share = nb / new_total

        gain_a = new_a_share - old_a_share
        gain_b = new_b_share - old_b_share

        lines += [
            f"New Ratio = {format_decimal(na)} : {format_decimal(nb)}",
            "",
            "### Gaining Ratio",
            f"A's Gain = {format_decimal(gain_a)}",
            f"B's Gain = {format_decimal(gain_b)}",
            "",
            f"Gaining Ratio = **{simplify_ratio(gain_a, gain_b)}**",
        ]

    return "\n".join(lines)


# ------------------------------------------------------------
# FINANCIAL RATIOS
# ------------------------------------------------------------

def solve_current_ratio(text):
    t = normalize(text)

    if "current ratio" not in t:
        return None

    current_assets = extract_labeled_number(
        t,
        ["current assets", "current asset"]
    )

    current_liabilities = extract_labeled_number(
        t,
        ["current liabilities", "current liability"]
    )

    if current_assets is None or current_liabilities is None:
        return None

    result = current_assets / current_liabilities

    return "\n".join([
        "### Current Ratio",
        "",
        "Current Ratio = Current Assets / Current Liabilities",
        f"= {money(current_assets)} / {money(current_liabilities)}",
        f"= **{format_decimal(result)} : 1**",
    ])


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
        ["current liabilities", "current liability"]
    )

    if quick_assets is None:
        current_assets = extract_labeled_number(
            t,
            ["current assets", "current asset"]
        )

        inventory = extract_labeled_number(
            t,
            ["inventory", "inventories", "stock"]
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

    if quick_assets is None or current_liabilities is None:
        return None

    result = quick_assets / current_liabilities

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
            "equity",
            "owners funds",
            "proprietors funds",
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
            "interest",
            "interest expense",
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


# ------------------------------------------------------------
# TURNOVER RATIOS
# ------------------------------------------------------------

def solve_inventory_turnover(text):
    t = normalize(text)

    if "inventory turnover" not in t:
        return None

    cost = extract_labeled_number(
        t,
        [
            "cost of revenue",
            "cost of goods sold",
            "cost of goods sold",
            "cost of sales",
        ]
    )

    avg_inventory = extract_labeled_number(
        t,
        [
            "average inventory",
            "average inventories",
            "average stock",
        ]
    )

    if avg_inventory is None:
        opening = extract_labeled_number(
            t,
            ["opening inventory", "opening stock"]
        )

        closing = extract_labeled_number(
            t,
            ["closing inventory", "closing stock"]
        )

        if opening is not None and closing is not None:
            avg_inventory = (opening + closing) / 2

    if cost is None or avg_inventory is None:
        return None

    result = cost / avg_inventory

    return "\n".join([
        "### Inventory Turnover Ratio",
        "",
        "Inventory Turnover Ratio = Cost of Goods Sold / Average Inventory",
        f"= {money(cost)} / {money(avg_inventory)}",
        f"= **{format_decimal(result)} times**",
    ])


def solve_receivables_turnover(text):
    t = normalize(text)

    if not any(
        x in t
        for x in [
            "trade receivables turnover",
            "debtors turnover",
            "receivables turnover",
        ]
    ):
        return None

    credit_sales = extract_labeled_number(
        t,
        [
            "credit sales",
            "credit revenue",
            "net credit sales",
        ]
    )

    avg_receivables = extract_labeled_number(
        t,
        [
            "average trade receivables",
            "average receivables",
            "average debtors",
        ]
    )

    if avg_receivables is None:
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

        if opening is not None and closing is not None:
            avg_receivables = (opening + closing) / 2

    if credit_sales is None or avg_receivables is None:
        return None

    result = credit_sales / avg_receivables

    return "\n".join([
        "### Trade Receivables Turnover Ratio",
        "",
        "Ratio = Net Credit Sales / Average Trade Receivables",
        f"= {money(credit_sales)} / {money(avg_receivables)}",
        f"= **{format_decimal(result)} times**",
    ])


def solve_payables_turnover(text):
    t = normalize(text)

    if not any(
        x in t
        for x in [
            "trade payables turnover",
            "creditors turnover",
            "payables turnover",
        ]
    ):
        return None

    credit_purchases = extract_labeled_number(
        t,
        [
            "credit purchases",
            "net credit purchases",
        ]
    )

    avg_payables = extract_labeled_number(
        t,
        [
            "average trade payables",
            "average payables",
            "average creditors",
        ]
    )

    if avg_payables is None:
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

        if opening is not None and closing is not None:
            avg_payables = (opening + closing) / 2

    if credit_purchases is None or avg_payables is None:
        return None

    result = credit_purchases / avg_payables

    return "\n".join([
        "### Trade Payables Turnover Ratio",
        "",
        "Ratio = Net Credit Purchases / Average Trade Payables",
        f"= {money(credit_purchases)} / {money(avg_payables)}",
        f"= **{format_decimal(result)} times**",
    ])


def solve_fixed_asset_turnover(text):
    t = normalize(text)

    if "fixed asset turnover" not in t:
        return None

    revenue = extract_labeled_number(
        t,
        [
            "revenue from operations",
            "revenue",
            "sales",
            "net sales",
        ]
    )

    fixed_assets = extract_labeled_number(
        t,
        [
            "net fixed assets",
            "fixed assets",
            "fixed asset",
        ]
    )

    if revenue is None or fixed_assets is None:
        return None

    result = revenue / fixed_assets

    return "\n".join([
        "### Fixed Asset Turnover Ratio",
        "",
        "Ratio = Revenue / Net Fixed Assets",
        f"= {money(revenue)} / {money(fixed_assets)}",
        f"= **{format_decimal(result)} times**",
    ])


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
            ["current assets"]
        )

        cl = extract_labeled_number(
            t,
            ["current liabilities"]
        )

        if ca is not None and cl is not None:
            working_capital = ca - cl

    if revenue is None or working_capital is None:
        return None

    result = revenue / working_capital

    return "\n".join([
        "### Working Capital Turnover Ratio",
        "",
        "Working Capital = Current Assets − Current Liabilities",
        f"Working Capital = {money(working_capital)}",
        "",
        "Working Capital Turnover Ratio = Revenue / Working Capital",
        f"= {money(revenue)} / {money(working_capital)}",
        f"= **{format_decimal(result)} times**",
    ])


# ------------------------------------------------------------
# PROFITABILITY RATIOS
# ------------------------------------------------------------

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
            "sales",
            "net sales",
        ]
    )

    if gp is None or revenue is None:
        return None

    result = gp / revenue * 100

    return "\n".join([
        "### Gross Profit Ratio",
        "",
        "Gross Profit Ratio = Gross Profit / Revenue × 100",
        f"= {money(gp)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


def solve_operating_ratio(text):
    t = normalize(text)

    if "operating ratio" not in t:
        return None

    if "operating profit ratio" in t:
        return None

    operating_cost = extract_labeled_number(
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

    if operating_cost is None or revenue is None:
        return None

    result = operating_cost / revenue * 100

    return "\n".join([
        "### Operating Ratio",
        "",
        "Operating Ratio = Operating Cost / Revenue × 100",
        f"= {money(operating_cost)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


def solve_operating_profit_ratio(text):
    t = normalize(text)

    if "operating profit ratio" not in t:
        return None

    op = extract_labeled_number(
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

    if op is None or revenue is None:
        return None

    result = op / revenue * 100

    return "\n".join([
        "### Operating Profit Ratio",
        "",
        "Operating Profit Ratio = Operating Profit / Revenue × 100",
        f"= {money(op)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


def solve_net_profit_ratio(text):
    t = normalize(text)

    if "net profit ratio" not in t:
        return None

    np = extract_labeled_number(
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

    if np is None or revenue is None:
        return None

    result = np / revenue * 100

    return "\n".join([
        "### Net Profit Ratio",
        "",
        "Net Profit Ratio = Net Profit / Revenue × 100",
        f"= {money(np)} / {money(revenue)} × 100",
        f"= **{percentage(result)}**",
    ])


def solve_roi(text):
    t = normalize(text)

    if not any(
        x in t
        for x in [
            "return on investment",
            "roi",
            "return on capital employed",
        ]
    ):
        return None

    operating_profit = extract_labeled_number(
        t,
        [
            "operating profit",
            "profit before interest and tax",
            "ebit",
        ]
    )

    capital = extract_capital_employed(t)

    if operating_profit is None or capital is None:
        return None

    result = operating_profit / capital * 100

    return "\n".join([
        "### Return on Investment",
        "",
        "ROI = Operating Profit / Capital Employed × 100",
        f"= {money(operating_profit)} / {money(capital)} × 100",
        f"= **{percentage(result)}**",
    ])


# ------------------------------------------------------------
# SHARE CAPITAL
# ------------------------------------------------------------

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

    # Don't interfere with ratio questions
    if "ratio" in t and "share capital" not in t:
        return None

    face_value = extract_labeled_number(
        t,
        [
            "face value",
            "nominal value",
            "face value per share",
            "nominal value per share",
        ]
    )

    issue_price = extract_labeled_number(
        t,
        [
            "issue price",
            "issued at",
            "issue price per share",
        ]
    )

    number_shares = extract_labeled_number(
        t,
        [
            "number of shares",
            "shares issued",
            "shares are issued",
            "shares offered",
        ]
    )

    if face_value is None:
        # common "shares of ₹10 each"
        m = re.search(
            rf"shares?\s+(?:of|at)\s+(?:rupees\s*)?({NUMBER})\s*each",
            t
        )

        if m:
            face_value = clean_number(m.group(1))

    if issue_price is None:
        m = re.search(
            rf"issued?\s+(?:at|for)\s+(?:rupees\s*)?({NUMBER})\s*per\s*share",
            t
        )

        if m:
            issue_price = clean_number(m.group(1))

    if face_value is None or issue_price is None:
        return None

    premium = issue_price - face_value

    lines = [
        "### Share Issue",
        "",
        f"Face Value per Share = {money(face_value)}",
        f"Issue Price per Share = {money(issue_price)}",
        "",
        f"Share Premium = Issue Price − Face Value",
        f"= {money(issue_price)} − {money(face_value)}",
        f"= **{money(premium)} per share**",
    ]

    if number_shares is not None:
        capital = number_shares * face_value
        total_issue = number_shares * issue_price
        total_premium = number_shares * premium

        lines += [
            "",
            f"Number of Shares = {format_number(number_shares)}",
            f"Share Capital = {format_number(number_shares)} × {money(face_value)}",
            f"= **{money(capital)}**",
            "",
            f"Total Securities Premium = **{money(total_premium)}**",
            f"Total Amount Received = **{money(total_issue)}**",
        ]

    return "\n".join(lines)


def solve_oversubscription(text):
    t = normalize(text)

    if "oversubscription" not in t:
        if "oversubscribed" not in t:
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
            "shares applied",
            "shares applied for",
            "applications received for",
        ]
    )

    if offered is None or applied is None:
        return None

    ratio = applied / offered

    excess = applied - offered

    return "\n".join([
        "### Oversubscription",
        "",
        f"Shares Applied = {format_number(applied)}",
        f"Shares Offered = {format_number(offered)}",
        "",
        f"Oversubscription = {format_number(excess)} shares",
        f"Subscription Ratio = **{format_decimal(ratio)} times**",
    ])


# ------------------------------------------------------------
# FORFEITURE / REISSUE
# ------------------------------------------------------------

def solve_forfeiture(text):
    t = normalize(text)

    if "forfeit" not in t and "forfeiture" not in t:
        return None

    face = extract_labeled_number(
        t,
        [
            "face value",
            "nominal value",
        ]
    )

    called = extract_labeled_number(
        t,
        [
            "called up",
            "called",
        ]
    )

    received = extract_labeled_number(
        t,
        [
            "amount received",
            "amount paid",
            "paid up",
        ]
    )

    if face is None and called is None:
        return None

    if called is None:
        called = face

    if received is None:
        return None

    unpaid = called - received

    return "\n".join([
        "### Forfeiture of Shares",
        "",
        f"Called-up Amount = {money(called)}",
        f"Amount Received = {money(received)}",
        f"Unpaid Amount = {money(unpaid)}",
        "",
        "Share Forfeiture A/c = Amount already received on forfeited shares",
        f"= **{money(received)}**",
    ])


def solve_reissue(text):
    t = normalize(text)

    if "reissue" not in t and "re-issued" not in t:
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
            "forfeited amount",
            "share forfeiture",
            "amount forfeited",
        ]
    )

    if face is None or reissue_price is None:
        return None

    discount = max(face - reissue_price, 0)

    lines = [
        "### Reissue of Forfeited Shares",
        "",
        f"Face Value = {money(face)}",
        f"Reissue Price = {money(reissue_price)}",
        f"Discount on Reissue = **{money(discount)}**",
    ]

    if forfeited is not None:
        capital_reserve = forfeited - discount

        if capital_reserve < 0:
            capital_reserve = 0

        lines += [
            "",
            f"Amount in Share Forfeiture A/c = {money(forfeited)}",
            "",
            "Capital Reserve = Share Forfeiture − Reissue Discount",
            f"= {money(forfeited)} − {money(discount)}",
            f"= **{money(capital_reserve)}**",
        ]

    return "\n".join(lines)


# ------------------------------------------------------------
# DEBENTURES
# ------------------------------------------------------------

def solve_debenture(text):
    t = normalize(text)

    if "debenture" not in t and "debentures" not in t:
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

    lines = ["### Debentures"]

    if face is not None:
        lines.append(
            f"Face Value = {money(face)}"
        )

    if issue_price is not None and face is not None:
        premium_discount = issue_price - face

        if premium_discount > 0:
            lines += [
                f"Issue Price = {money(issue_price)}",
                f"Premium = **{money(premium_discount)}**",
            ]
        elif premium_discount < 0:
            lines += [
                f"Issue Price = {money(issue_price)}",
                f"Discount = **{money(abs(premium_discount))}**",
            ]
        else:
            lines.append("Issued at Par.")

    if rate is not None and face is not None:
        interest = face * rate / 100

        lines += [
            "",
            f"Interest Rate = {percentage(rate)}",
            f"Annual Interest = {money(face)} × {format_decimal(rate)} / 100",
            f"= **{money(interest)}**",
        ]

    if len(lines) == 1:
        return None

    return "\n".join(lines)


# ------------------------------------------------------------
# CASH FLOW - BASIC INDIRECT METHOD
# ------------------------------------------------------------

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

    pat = extract_labeled_number(
        t,
        [
            "profit after tax",
            "profit after tax",
            "net profit",
            "profit",
        ]
    )

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

    if pat is None:
        return None

    cfo = pat

    lines = [
        "### Cash Flow from Operating Activities",
        "",
        f"Profit = {money(pat)}",
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


# ------------------------------------------------------------
# PAST ADJUSTMENT
# ------------------------------------------------------------

def solve_past_adjustment(text):
    t = normalize(text)

    if "past adjustment" not in t and "past adjustments" not in t:
        return None

    lines = [
        "### Past Adjustment",
        "",
        "Past adjustment is normally made through the Partners' Capital/Current Accounts.",
        "",
        "General rule:",
        "1. Calculate the amount that should have been credited/debited.",
        "2. Compare it with the amount actually credited/debited.",
        "3. Pass one adjustment entry for the net difference.",
    ]

    return "\n".join(lines)


# ------------------------------------------------------------
# GUARANTEE
# ------------------------------------------------------------

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
        deficiency = max(guaranteed - actual, 0)

        lines += [
            f"Actual Profit = {money(actual)}",
            "",
            "Deficiency = Guaranteed Profit − Actual Profit",
            f"= {money(guaranteed)} − {money(actual)}",
            f"= **{money(deficiency)}**",
        ]

    return "\n".join(lines)


# ------------------------------------------------------------
# REVALUATION
# ------------------------------------------------------------

def solve_revaluation(text):
    t = normalize(text)

    if "revaluation" not in t and "revaluation account" not in t:
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


# ------------------------------------------------------------
# DISSOLUTION
# ------------------------------------------------------------

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
            "assets realised for",
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

    realisation_expenses = extract_labeled_number(
        t,
        [
            "realisation expenses",
            "realization expenses",
            "expenses of realisation",
            "expenses of realization",
        ]
    )

    if assets is None and liabilities is None and realisation_expenses is None:
        return None

    profit = None

    if assets is not None:
        profit = assets

        if liabilities is not None:
            profit -= liabilities

        if realisation_expenses is not None:
            profit -= realisation_expenses

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

    if realisation_expenses is not None:
        lines.append(
            f"Realisation Expenses = {money(realisation_expenses)}"
        )

    if profit is not None:
        lines += [
            "",
            f"Basic net realisation amount = **{money(profit)}**",
        ]

    return "\n".join(lines)


# ------------------------------------------------------------
# MASTER LOCAL SOLVER
# ------------------------------------------------------------

def local_solve(question):
    q = question or ""
    t = normalize(q)

    # 1. Basic arithmetic
    result = basic_math_solver(q)

    if result:
        return result

    # --------------------------------------------------------
    # PARTNERSHIP
    # --------------------------------------------------------

    # Admission must come before generic goodwill
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

    # Goodwill methods
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
    # FINANCIAL RATIOS
    # --------------------------------------------------------

    # Specific ratios first
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


# ------------------------------------------------------------
# AI FALLBACK
# ------------------------------------------------------------

def ai_solve(question, image_data=None):
    key = os.environ.get("OPENAI_API_KEY")

    if not key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY is not configured."
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)

        system_prompt = """
You are Commerce AI, an expert Class 12 CBSE Accountancy solver.

Solve the student's question accurately.

Rules:
1. Read the complete question before solving.
2. Identify the exact chapter and method.
3. Show formula.
4. Show substitution.
5. Show calculations step by step.
6. Give final answer clearly.
7. For partnership questions, carefully calculate:
   - old ratio
   - new ratio
   - sacrificing ratio
   - gaining ratio
   - goodwill
   - revaluation
   - capital/current accounts
   - journal entries
8. For company accounts, show journal entries where required.
9. For ratio analysis, use the correct formula.
10. For cash flow, classify items correctly.
11. Never invent missing values.
12. If the question is ambiguous, state exactly what information is missing.
13. Use Indian accounting terminology and ₹.
"""

        user_content = []

        if question:
            user_content.append({
                "type": "input_text",
                "text": question
            })

        if image_data:
            user_content.append({
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
                    "content": user_content
                }
            ]
        )

        answer = getattr(response, "output_text", None)

        if not answer:
            answer = str(response)

        return {
            "success": True,
            "answer": answer,
            "source": "ai",
            "api_used": True
        }

    except Exception as e:
        error_text = str(e)

        return {
            "success": False,
            "error": error_text,
            "source": "ai",
            "api_used": True
        }


# ------------------------------------------------------------
# HTTP HANDLER
# ------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
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
        self._send_json({
            "success": True
        })

    def do_GET(self):
        self._send_json({
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

            raw_body = self.rfile.read(
                content_length
            )

            data = json.loads(
                raw_body.decode("utf-8")
            )

            question = data.get(
                "question",
                ""
            )

            image = data.get(
                "image",
                None
            )

            if not question and not image:
                self._send_json(
                    {
                        "success": False,
                        "error": "Please provide a question or image."
                    },
                    400
                )
                return

            # ------------------------------------------------
            # LOCAL MASTER ENGINE
            # ------------------------------------------------

            local_answer = None

            if question:
                local_answer = local_solve(
                    question
                )

            if local_answer:
                self._send_json({
                    "success": True,
                    "answer": local_answer,
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
                self._send_json(
                    result,
                    200
                )
            else:
                self._send_json(
                    result,
                    500
                )

        except json.JSONDecodeError:
            self._send_json(
                {
                    "success": False,
                    "error": "Invalid JSON request."
                },
                400
            )

        except Exception as e:
            self._send_json(
                {
                    "success": False,
                    "error": str(e)
                },
                500
            )


# Vercel entry point
handler = Handler
