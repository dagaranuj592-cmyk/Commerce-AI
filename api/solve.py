import os
import json
import re
import ast
import operator as op
import math

from http.server import BaseHTTPRequestHandler
from openai import OpenAI

from api.calculator import calculate


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

PATTERN_DATABASE_PATH = os.path.join(
    BASE_DIR,
    "database",
    "accountancy",
    "patterns.json"
)


# =========================================================
# DATABASE
# =========================================================

def load_database():

    try:

        with open(
            PATTERN_DATABASE_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {"patterns": []}


def find_pattern(question):

    database = load_database()

    patterns = database.get(
        "patterns",
        []
    )

    q = question.lower()

    best_pattern = None
    best_score = 0

    for pattern in patterns:

        keywords = pattern.get(
            "keywords",
            []
        )

        score = 0

        for keyword in keywords:

            if keyword.lower() in q:
                score += 1

        if score > best_score:

            best_score = score
            best_pattern = pattern

    return best_pattern


# =========================================================
# BASIC HELPERS
# =========================================================

def clean_number(value):

    try:

        return float(
            str(value)
            .replace(",", "")
            .replace("₹", "")
            .strip()
        )

    except Exception:

        return None


def format_number(value):

    if value is None:
        return "0"

    if isinstance(value, float):

        if value.is_integer():
            value = int(value)

    return f"{value:,}"


def format_decimal(value):

    if value is None:
        return "0"

    return (
        f"{value:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def simplify_ratio(a, b):

    if a == 0 and b == 0:
        return "0 : 0"

    scale = 1000000

    ai = round(a * scale)
    bi = round(b * scale)

    divisor = math.gcd(
        abs(ai),
        abs(bi)
    )

    if divisor == 0:
        return "0 : 0"

    return (
        f"{ai // divisor} : "
        f"{bi // divisor}"
    )


# =========================================================
# NUMBER EXTRACTION
# =========================================================

def extract_percentage(text):

    patterns = [

        r"(\d+(?:\.\d+)?)\s*%",

        r"rate\s+of\s+return"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)",

        r"normal\s+rate"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return clean_number(
                match.group(1)
            )

    return None


def extract_years_purchase(text):

    patterns = [

        r"(\d+(?:\.\d+)?)\s*"
        r"years?['’]?\s*purchase",

        r"(\d+(?:\.\d+)?)\s*"
        r"year['’]?\s*purchase",

        r"purchase\s*(?:of|=)?\s*"
        r"(\d+(?:\.\d+)?)\s*years?",

        r"years?['’]?\s*purchase"
        r"\s*(?:of|=)?\s*"
        r"(\d+(?:\.\d+)?)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return clean_number(
                match.group(1)
            )

    return None


def extract_labeled_number(
    text,
    labels
):

    for label in labels:

        pattern = (
            re.escape(label)
            + r"\s*"
            r"(?:is|are|=|of)?"
            r"\s*(?:₹\s*)?"
            r"([\d,]+(?:\.\d+)?)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return clean_number(
                match.group(1)
            )

    return None


# =========================================================
# AMOUNT BEFORE PHRASE
# =========================================================

def extract_amount_before_phrase(
    text,
    phrases
):

    for phrase in phrases:

        pattern = (
            r"(?:₹\s*)?"
            r"([\d,]+(?:\.\d+)?)"
            r"\s*(?:as|for|towards|of)?\s*"
            + re.escape(phrase)
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return clean_number(
                match.group(1)
            )

    return None


def extract_capital_employed(text):

    return extract_labeled_number(
        text,
        [
            "capital employed",
            "capital employed is",
            "capital employed of"
        ]
    )


def extract_average_profit(text):

    return extract_labeled_number(
        text,
        [
            "average profit",
            "average profits"
        ]
    )


# =========================================================
# HISTORICAL PROFITS
# =========================================================

def extract_historical_profits(text):

    q = text.lower()

    if "profit" not in q:
        return []

    if not any(
        word in q
        for word in [
            "last",
            "previous",
            "past",
            "years"
        ]
    ):
        return []

    match = re.search(
        r"profits?.*?"
        r"(?:were|are|was|is)"
        r"(.*?)(?:\.|calculate|$)",
        text,
        re.IGNORECASE
    )

    if not match:
        return []

    section = match.group(1)

    numbers = re.findall(
        r"(?:₹\s*)?"
        r"(\d{1,3}(?:,\d{2,3})*"
        r"(?:\.\d+)?|\d+(?:\.\d+)?)",
        section
    )

    result = []

    for number in numbers:

        value = clean_number(number)

        if (
            value is not None
            and value >= 1000
        ):

            result.append(value)

    return result


# =========================================================
# RATIO / FRACTION HELPERS
# =========================================================

def extract_first_ratio(text):

    match = re.search(
        r"(\d+(?:\.\d+)?)"
        r"\s*:\s*"
        r"(\d+(?:\.\d+)?)",
        text
    )

    if match:

        return (
            float(match.group(1)),
            float(match.group(2))
        )

    return None


def extract_partner_old_ratio(text):

    match = re.search(
        r"(?:ratio|sharing profits?)"
        r".{0,50}?"
        r"(\d+(?:\.\d+)?)"
        r"\s*:\s*"
        r"(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:

        return (
            float(match.group(1)),
            float(match.group(2))
        )

    return extract_first_ratio(text)


def extract_fraction_share(text):

    patterns = [

        r"(\d+(?:\.\d+)?)\s*/\s*"
        r"(\d+(?:\.\d+)?)\s*share",

        r"for\s+"
        r"(\d+(?:\.\d+)?)\s*/\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*share",

        r"(\d+(?:\.\d+)?)\s*/\s*"
        r"(\d+(?:\.\d+)?)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            numerator = float(
                match.group(1)
            )

            denominator = float(
                match.group(2)
            )

            if denominator != 0:

                return (
                    numerator,
                    denominator
                )

    return None


# =========================================================
# SAFE BASIC MATH
# =========================================================

_ALLOWED_OPERATORS = {

    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos

}


def safe_math(node):

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
        ast.UnaryOp
    ):

        operator = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operator is None:
            raise ValueError()

        return operator(
            safe_math(node.operand)
        )

    if isinstance(
        node,
        ast.BinOp
    ):

        operator = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operator is None:
            raise ValueError()

        left = safe_math(
            node.left
        )

        right = safe_math(
            node.right
        )

        return operator(
            left,
            right
        )

    raise ValueError()


def solve_basic_math(question):

    q = question.strip()

    q = q.replace("×", "*")
    q = q.replace("x", "*")
    q = q.replace("X", "*")
    q = q.replace("÷", "/")
    q = q.replace("−", "-")
    q = q.replace("–", "-")

    q = re.sub(
        r"^(calculate|solve|find)\s+",
        "",
        q,
        flags=re.IGNORECASE
    )

    q = q.strip()

    if not re.fullmatch(
        r"[\d\s\+\-\*\/\.\^]+",
        q
    ):

        return None

    if not re.search(
        r"[\+\-\*\/]",
        q
    ):

        return None

    try:

        q = q.replace(
            "^",
            "**"
        )

        tree = ast.parse(
            q,
            mode="eval"
        )

        result = safe_math(
            tree.body
        )

        return result

    except Exception:

        return None


# =========================================================
# LOCAL SOLVER
# =========================================================

def local_solve(question):

    q = question.lower().strip()


    # =====================================================
    # BASIC MATH
    # =====================================================

    basic_result = solve_basic_math(
        question
    )

    if basic_result is not None:

        return {

            "success": True,

            "title":
                "Basic Calculation",

            "value":
                basic_result,

            "steps": [

                f"{question.strip()} = "
                f"{format_decimal(basic_result)}"

            ]

        }


    # =====================================================
    # ADMISSION OF PARTNER
    # =====================================================

    if (
        "admitted" in q
        or "admission of" in q
        or "new partner" in q
    ):

        old_ratio = extract_partner_old_ratio(
            question
        )

        new_share = extract_fraction_share(
            question
        )

        if (
            old_ratio is not None
            and new_share is not None
        ):

            old_a, old_b = old_ratio

            numerator, denominator = new_share

            c_share = (
                numerator
                / denominator
            )

            remaining_share = (
                1 - c_share
            )

            total_old = (
                old_a
                + old_b
            )

            new_a = (
                remaining_share
                * old_a
                / total_old
            )

            new_b = (
                remaining_share
                * old_b
                / total_old
            )

            sacrifice_a = (
                old_a / total_old
                - new_a
            )

            sacrifice_b = (
                old_b / total_old
                - new_b
            )

            steps = [

                "Given:",

                "Old Ratio = "
                + format_decimal(old_a)
                + " : "
                + format_decimal(old_b),

                "New Partner's Share = "
                + format_decimal(numerator)
                + "/"
                + format_decimal(denominator),

                "",

                "Remaining Share for Old Partners = "
                "1 − New Partner's Share",

                "Remaining Share = "
                + format_decimal(
                    remaining_share
                ),

                "",

                "New Share of A = "
                + format_decimal(
                    remaining_share
                )
                + " × "
                + format_decimal(old_a)
                + "/"
                + format_decimal(total_old),

                "New Share of A = "
                + format_decimal(new_a),

                "",

                "New Share of B = "
                + format_decimal(
                    remaining_share
                )
                + " × "
                + format_decimal(old_b)
                + "/"
                + format_decimal(total_old),

                "New Share of B = "
                + format_decimal(new_b),

                "",

                "Sacrifice of A = Old Share − New Share",

                "Sacrifice of A = "
                + format_decimal(
                    old_a / total_old
                )
                + " − "
                + format_decimal(new_a),

                "Sacrifice of A = "
                + format_decimal(
                    sacrifice_a
                ),

                "",

                "Sacrifice of B = Old Share − New Share",

                "Sacrifice of B = "
                + format_decimal(
                    old_b / total_old
                )
                + " − "
                + format_decimal(new_b),

                "Sacrifice of B = "
                + format_decimal(
                    sacrifice_b
                ),

                "",

                "New Ratio = "
                + format_decimal(new_a)
                + " : "
                + format_decimal(new_b)
                + " : "
                + format_decimal(c_share),

                "Sacrificing Ratio = "
                + simplify_ratio(
                    sacrifice_a,
                    sacrifice_b
                )

            ]


            # =================================================
            # GOODWILL PREMIUM
            # =================================================

            goodwill = extract_amount_before_phrase(
                question,
                [
                    "as goodwill premium",
                    "as premium for goodwill",
                    "goodwill premium",
                    "premium for goodwill"
                ]
            )

            if goodwill is None:

                goodwill = extract_labeled_number(
                    question,
                    [
                        "goodwill premium",
                        "premium for goodwill",
                        "goodwill"
                    ]
                )


            if goodwill is not None:

                total_sacrifice = (
                    sacrifice_a
                    + sacrifice_b
                )

                if total_sacrifice != 0:

                    amount_a = (
                        goodwill
                        * sacrifice_a
                        / total_sacrifice
                    )

                    amount_b = (
                        goodwill
                        * sacrifice_b
                        / total_sacrifice
                    )

                    steps.extend([

                        "",

                        "Goodwill Premium = ₹"
                        + format_number(
                            goodwill
                        ),

                        "A's Share of Goodwill = ₹"
                        + format_number(
                            amount_a
                        ),

                        "B's Share of Goodwill = ₹"
                        + format_number(
                            amount_b
                        ),

                        "",

                        "Journal Entry 1:",

                        "Bank A/c Dr. ₹"
                        + format_number(
                            goodwill
                        ),

                        "    To Premium for Goodwill A/c ₹"
                        + format_number(
                            goodwill
                        ),

                        "",

                        "Journal Entry 2:",

                        "Premium for Goodwill A/c Dr. ₹"
                        + format_number(
                            goodwill
                        ),

                        "    To A's Capital A/c ₹"
                        + format_number(
                            amount_a
                        ),

                        "    To B's Capital A/c ₹"
                        + format_number(
                            amount_b
                        )

                    ])


            return {

                "success": True,

                "title":
                    "Admission of Partner",

                "value":
                    None,

                "steps":
                    steps

            }


    # =====================================================
    # HISTORICAL PROFITS + GOODWILL
    # =====================================================

    if (
        "goodwill" in q
        and "profit" in q
        and any(
            word in q
            for word in [
                "last",
                "previous",
                "past"
            ]
        )
    ):

        profits = extract_historical_profits(
            question
        )

        capital = extract_capital_employed(
            question
        )

        rate = extract_percentage(
            question
        )

        years = extract_years_purchase(
            question
        )

        if (
            len(profits) >= 2
            and capital is not None
            and rate is not None
            and years is not None
        ):

            total = sum(profits)

            average = (
                total
                / len(profits)
            )

            normal = (
                capital
                * rate
                / 100
            )

            super_profit = (
                average
                - normal
            )

            goodwill = (
                super_profit
                * years
            )

            return {

                "success": True,

                "title":
                    "Goodwill - Super Profit Method",

                "value":
                    goodwill,

                "steps": [

                    "Total Profit = "
                    + " + ".join(
                        "₹" + format_number(x)
                        for x in profits
                    ),

                    "Total Profit = ₹"
                    + format_number(total),

                    "",

                    "Average Profit = "
                    "Total Profit ÷ Number of Years",

                    "Average Profit = ₹"
                    + format_number(average),

                    "",

                    "Normal Profit = "
                    "Capital Employed × Rate ÷ 100",

                    "Normal Profit = ₹"
                    + format_number(normal),

                    "",

                    "Super Profit = "
                    "Average Profit − Normal Profit",

                    "Super Profit = ₹"
                    + format_number(
                        super_profit
                    ),

                    "",

                    "Goodwill = "
                    "Super Profit × Years' Purchase",

                    "Goodwill = ₹"
                    + format_number(
                        super_profit
                    )
                    + " × "
                    + format_decimal(
                        years
                    ),

                    "Goodwill = ₹"
                    + format_number(
                        goodwill
                    )

                ]

            }


    # =====================================================
    # GOODWILL - AVERAGE PROFIT
    # =====================================================

    if (
        "goodwill" in q
        and "average profit" in q
    ):

        average = extract_average_profit(
            question
        )

        years = extract_years_purchase(
            question
        )

        if (
            average is not None
            and years is not None
        ):

            return calculate({

                "type":
                    "goodwill_average_profit",

                "average_profit":
                    average,

                "years_purchase":
                    years

            })


    # =====================================================
    # SUPER PROFIT
    # =====================================================

    if "super profit" in q:

        average = extract_average_profit(
            question
        )

        capital = extract_capital_employed(
            question
        )

        rate = extract_percentage(
            question
        )

        if (
            average is not None
            and capital is not None
            and rate is not None
        ):

            years = extract_years_purchase(
                question
            )

            if (
                "goodwill" in q
                and years is not None
            ):

                return calculate({

                    "type":
                        "goodwill_super_profit",

                    "average_profit":
                        average,

                    "capital_employed":
                        capital,

                    "normal_rate":
                        rate,

                    "years_purchase":
                        years

                })

            return calculate({

                "type":
                    "super_profit",

                "average_profit":
                    average,

                "capital_employed":
                    capital,

                "normal_rate":
                    rate

            })


    # =====================================================
    # CURRENT RATIO
    # =====================================================

    if "current ratio" in q:

        assets = extract_labeled_number(
            question,
            [
                "current assets"
            ]
        )

        liabilities = extract_labeled_number(
            question,
            [
                "current liabilities"
            ]
        )

        if (
            assets is not None
            and liabilities is not None
        ):

            return calculate({

                "type":
                    "current_ratio",

                "current_assets":
                    assets,

                "current_liabilities":
                    liabilities

            })


    # =====================================================
    # QUICK RATIO
    # =====================================================

    if (
        "quick ratio" in q
        or "liquid ratio" in q
    ):

        assets = extract_labeled_number(
            question,
            [
                "quick assets",
                "liquid assets"
            ]
        )

        liabilities = extract_labeled_number(
            question,
            [
                "current liabilities"
            ]
        )

        if (
            assets is not None
            and liabilities is not None
        ):

            return calculate({

                "type":
                    "quick_ratio",

                "quick_assets":
                    assets,

                "current_liabilities":
                    liabilities

            })


    # =====================================================
    # DEBT-EQUITY RATIO
    # =====================================================

    if (
        "debt-equity ratio" in q
        or "debt equity ratio" in q
    ):

        debt = extract_labeled_number(
            question,
            [
                "long-term debt",
                "long term debt"
            ]
        )

        equity = extract_labeled_number(
            question,
            [
                "shareholders' funds",
                "shareholders funds"
            ]
        )

        if (
            debt is not None
            and equity is not None
        ):

            return calculate({

                "type":
                    "debt_equity_ratio",

                "long_term_debt":
                    debt,

                "shareholders_funds":
                    equity

            })


    # =====================================================
    # DEBT RATIO
    # =====================================================

    if (
        "debt ratio" in q
        or "debt to total assets" in q
    ):

        debt = extract_labeled_number(
            question,
            [
                "total debt",
                "debt"
            ]
        )

        assets = extract_labeled_number(
            question,
            [
                "total assets",
                "assets"
            ]
        )

        if (
            debt is not None
            and assets is not None
            and assets != 0
        ):

            ratio = (
                debt
                / assets
                * 100
            )

            return {

                "success": True,

                "title":
                    "Debt Ratio",

                "value":
                    ratio,

                "steps": [

                    "Debt Ratio = "
                    "Total Debt ÷ Total Assets × 100",

                    "Debt Ratio = ₹"
                    + format_number(debt)
                    + " ÷ ₹"
                    + format_number(assets)
                    + " × 100",

                    "Debt Ratio = "
                    + format_decimal(ratio)
                    + "%"

                ]

            }


    # =====================================================
    # PROPRIETARY RATIO
    # =====================================================

    if "proprietary ratio" in q:

        assets = extract_labeled_number(
            question,
            [
                "total assets",
                "assets"
            ]
        )

        debt = extract_labeled_number(
            question,
            [
                "total debt",
                "debt"
            ]
        )

        if (
            assets is not None
            and debt is not None
            and assets != 0
        ):

            shareholders_funds = (
                assets - debt
            )

            ratio = (
                shareholders_funds
                / assets
            )

            return {

                "success": True,

                "title":
                    "Proprietary Ratio",

                "value":
                    ratio,

                "steps": [

                    "Shareholders' Funds = "
                    "Total Assets − Total Debt",

                    "Shareholders' Funds = ₹"
                    + format_number(
                        shareholders_funds
                    ),

                    "",

                    "Proprietary Ratio = "
                    "Shareholders' Funds ÷ Total Assets",

                    "Proprietary Ratio = "
                    + format_decimal(ratio)
                    + " : 1"

                ]

            }


    # =====================================================
    # GROSS PROFIT RATIO
    # =====================================================

    if "gross profit ratio" in q:

        profit = extract_labeled_number(
            question,
            [
                "gross profit"
            ]
        )

        revenue = extract_labeled_number(
            question,
            [
                "revenue",
                "sales"
            ]
        )

        if (
            profit is not None
            and revenue is not None
        ):

            return calculate({

                "type":
                    "gross_profit_ratio",

                "gross_profit":
                    profit,

                "revenue":
                    revenue

            })


    # =====================================================
    # NET PROFIT RATIO
    # =====================================================

    if "net profit ratio" in q:

        profit = extract_labeled_number(
            question,
            [
                "net profit"
            ]
        )

        revenue = extract_labeled_number(
            question,
            [
                "revenue",
                "sales"
            ]
        )

        if (
            profit is not None
            and revenue is not None
        ):

            return calculate({

                "type":
                    "net_profit_ratio",

                "net_profit":
                    profit,

                "revenue":
                    revenue

            })


    # =====================================================
    # ROI
    # =====================================================

    if (
        "roi" in q
        or "return on investment" in q
    ):

        profit = extract_labeled_number
