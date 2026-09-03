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
        ) as file:

            return json.load(file)

    except Exception:

        return {
            "patterns": []
        }


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

    try:
        value = float(value)

        # Remove floating-point calculation errors
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

    return (
        f"{value:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def simplify_ratio(a, b):

    if a == 0 and b == 0:
        return "0 : 0"

    scale = 1000000

    a_int = round(a * scale)
    b_int = round(b * scale)

    divisor = math.gcd(
        abs(a_int),
        abs(b_int)
    )

    if divisor == 0:
        return "0 : 0"

    return (
        f"{a_int // divisor} : "
        f"{b_int // divisor}"
    )


# =========================================================
# NUMBER EXTRACTION
# =========================================================

def extract_labeled_number(text, labels):

    for label in labels:

        pattern = (
            re.escape(label)
            + r"\s*"
            + r"(?:is|are|=|of)?"
            + r"\s*"
            + r"(?:₹\s*)?"
            + r"([\d,]+(?:\.\d+)?)"
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


def extract_percentage(text):

    patterns = [

        r"(\d+(?:\.\d+)?)\s*%",

        r"normal\s+rate"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)",

        r"rate\s+of\s+return"
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


def extract_capital_employed(text):

    return extract_labeled_number(
        text,
        [
            "capital employed"
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
# AMOUNT EXTRACTION
# =========================================================

def extract_amount_before_phrase(
    text,
    phrases
):

    for phrase in phrases:

        pattern = (
            r"(?:₹\s*)?"
            r"([\d,]+(?:\.\d+)?)"
            r"\s*"
            r"(?:as|for|towards|of)?"
            r"\s*"
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


def extract_goodwill_amount(text):

    # Example:
    # ₹30,000 as goodwill premium

    amount = extract_amount_before_phrase(
        text,
        [
            "as goodwill premium",
            "as premium for goodwill",
            "goodwill premium",
            "premium for goodwill"
        ]
    )

    if amount is not None:
        return amount

    # Example:
    # goodwill premium ₹30,000

    return extract_labeled_number(
        text,
        [
            "goodwill premium",
            "premium for goodwill"
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

    profits = []

    for number in numbers:

        value = clean_number(number)

        if (
            value is not None
            and value >= 1000
        ):

            profits.append(value)

    return profits


# =========================================================
# RATIO / FRACTION
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
        r"(?:ratio|sharing profits?|share)"
        r".{0,60}?"
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

        r"(\d+(?:\.\d+)?)"
        r"\s*/\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*share",

        r"for\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*/\s*"
        r"(\d+(?:\.\d+)?)",

        r"(\d+(?:\.\d+)?)"
        r"\s*/\s*"
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

    q = q.replace(
        "×",
        "*"
    )

    q = q.replace(
        "÷",
        "/"
    )

    q = q.replace(
        "−",
        "-"
    )

    q = q.replace(
        "–",
        "-"
    )

    q = re.sub(
        r"^(calculate|solve|find)\s+",
        "",
        q,
        flags=re.IGNORECASE
    )

    q = q.strip()

    # Only simple mathematical expressions
    if not re.fullmatch(
        r"[\d\s\+\-\*\/\(\)\.\^]+",
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

        return safe_math(
            tree.body
        )

    except Exception:

        return None


# =========================================================
# LOCAL SOLVER
# =========================================================

def local_solve(question):

    q = question.lower().strip()


    # =====================================================
    # 1. BASIC MATH
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
    # 2. ADMISSION OF PARTNER
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
                1
                - c_share
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

            old_a_share = (
                old_a
                / total_old
            )

            old_b_share = (
                old_b
                / total_old
            )

            sacrifice_a = (
                old_a_share
                - new_a
            )

            sacrifice_b = (
                old_b_share
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

                "Remaining Share for A and B = "
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

                "New Ratio = "
                + format_decimal(new_a)
                + " : "
                + format_decimal(new_b)
                + " : "
                + format_decimal(c_share),

                "",

                "Sacrifice of A = Old Share − New Share",

                "Sacrifice of A = "
                + format_decimal(old_a_share)
                + " − "
                + format_decimal(new_a),

                "Sacrifice of A = "
                + format_decimal(
                    sacrifice_a
                ),

                "",

                "Sacrifice of B = Old Share − New Share",

                "Sacrifice of B = "
                + format_decimal(old_b_share)
                + " − "
                + format_decimal(new_b),

                "Sacrifice of B = "
                + format_decimal(
                    sacrifice_b
                ),

                "",

                "Sacrificing Ratio = "
                + simplify_ratio(
                    sacrifice_a,
                    sacrifice_b
                )

            ]


            # =================================================
            # GOODWILL PREMIUM
            # =================================================

            goodwill = extract_goodwill_amount(
                question
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
    # 3. HISTORICAL PROFIT + GOODWILL
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

            total = sum(
                profits
            )

            average = (
                total
                / len(profits)
            )

            normal_profit = (
                capital
                * rate
                / 100
            )

            super_profit = (
                average
                - normal_profit
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
                    + format_number(
                        normal_profit
                    ),

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
                    + format_decimal(years),

                    "Goodwill = ₹"
                    + format_number(
                        goodwill
                    )

                ]

            }


    # =====================================================
    # 4. GOODWILL - AVERAGE PROFIT
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
    # 5. SUPER PROFIT
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
    # 6. CURRENT RATIO
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
    # 7. QUICK RATIO
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
    # 8. DEBT-EQUITY RATIO
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
    # 9. DEBT RATIO
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
    # 10. PROPRIETARY RATIO
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
                assets
                - debt
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
    # 11. GROSS PROFIT RATIO
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
    # 12. NET PROFIT RATIO
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
    # 13. ROI
    # =====================================================

    if (
        "roi" in q
        or "return on investment" in q
    ):

        profit = extract_labeled_number(
            question,
            [
                "operating profit"
            ]
        )

        capital = extract_capital_employed(
            question
        )

        if (
            profit is not None
            and capital is not None
        ):

            return calculate({

                "type":
                    "roi",

                "operating_profit":
                    profit,

                "capital_employed":
                    capital

            })


    # =====================================================
    # 14. INTEREST ON CAPITAL
    # =====================================================

    if "interest on capital" in q:

        capital = extract_labeled_number(
            question,
            [
                "capital"
            ]
        )

        rate = extract_percentage(
            question
        )

        if (
            capital is not None
            and rate is not None
        ):

            return calculate({

                "type":
                    "interest_on_capital",

                "capital":
                    capital,

                "rate":
                    rate

            })


    # =====================================================
    # 15. INTEREST ON DRAWINGS
    # =====================================================

    if "interest on drawings" in q:

        drawings = extract_labeled_number(
            question,
            [
                "drawings",
                "drawing"
            ]
        )

        rate = extract_percentage(
            question
        )

        if (
            drawings is not None
            and rate is not None
        ):

            return calculate({

                "type":
                    "interest_on_drawings",

                "drawings":
                    drawings,

                "rate":
                    rate

            })


    # =====================================================
    # NO LOCAL SOLUTION
    # =====================================================

    return None


# =========================================================
# FORMAT RESULT
# =========================================================

def format_result(result):

    if not result:
        return ""

    if not result.get("success"):

        return (
            "❌ "
            + result.get(
                "error",
                "Calculation error."
            )
        )

    lines = []

    lines.append(
        "📚 "
        + result.get(
            "title",
            "Solution"
        )
    )

    lines.append("")

    for step in result.get(
        "steps",
        []
    ):

        lines.append(step)

    value = result.get(
        "value"
    )

    title = result.get(
        "title",
        ""
    ).lower()

    if (
        value is not None
        and isinstance(
            value,
            (int, float)
        )
    ):

        if (
            "basic calculation"
            in title
        ):

            lines.append("")

            lines.append(
                "✅ Final Answer: "
                + format_decimal(value)
            )

        elif (
            "ratio" in title
            and (
                "debt ratio" not in title
                and "gross profit ratio" not in title
                and "net profit ratio" not in title
            )
        ):

            lines.append("")

            lines.append(
                "✅ Final Answer: "
                + format_decimal(value)
                + " : 1"
            )

        elif (
            "ratio" in title
            or "profit ratio" in title
        ):

            lines.append("")

            lines.append(
                "✅ Final Answer: "
                + format_decimal(value)
                + "%"
            )

        else:

            lines.append("")

            lines.append(
                "✅ Final Answer: ₹"
                + format_number(value)
            )

    return "\n".join(lines)


# =========================================================
# AI FALLBACK
# =========================================================

def solve_with_ai(
    question,
    image,
    pattern
):

    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise Exception(
            "OPENAI_API_KEY is not configured."
        )

    client = OpenAI(
        api_key=api_key
    )

    database_context = ""

    if pattern:

        database_context = """

Relevant database pattern:

Chapter:
""" + str(
            pattern.get(
                "chapter",
                ""
            )
        ) + """

Formula:
""" + str(
            pattern.get(
                "formula",
                ""
            )
        ) + """

Method:
""" + "\n".join(
            pattern.get(
                "method",
                []
            )
        )


    prompt = """
You are Commerce AI.

Solve the student's Accountancy or Economics
question accurately.

Give:

1. Given
2. Required
3. Formula / Rule
4. Step-by-step calculation
5. Final Answer

For Accountancy:
- show working notes
- show journal entries when asked
- show ratios clearly
- use correct formulas
- use ₹ correctly

For Economics:
- show the formula
- calculate step by step
- clearly state the final answer

Never invent missing information.

""" + database_context + """

Question:

""" + question


    content = [

        {
            "type":
                "input_text",

            "text":
                prompt
        }

    ]

    if image:

        content.append({

            "type":
                "input_image",

            "image_url":
                image

        })


    response = client.responses.create(

        model="gpt-5.6-luna",

        input=[

            {
                "role":
                    "user",

                "content":
                    content
            }

        ]
    )

    return response.output_text


# =========================================================
# HTTP HANDLER
# =========================================================

class handler(
    BaseHTTPRequestHandler
):

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                content_length
            )

            data = json.loads(
                body
            )

            question = data.get(
                "question",
                ""
            ).strip()

            image = data.get(
                "image",
                ""
            )


            # =================================================
            # EMPTY INPUT
            # =================================================

            if (
                not question
                and not image
            ):

                self.send_response(400)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.end_headers()

                self.wfile.write(

                    json.dumps(
                        {
                            "success": False,
                            "error":
                                "Question ya photo required hai."
                        },
                        ensure_ascii=False
                    ).encode("utf-8")

                )

                return


            # =================================================
            # LOCAL ENGINE FIRST
            # =================================================

            local_result = None

            if question:

                local_result = local_solve(
                    question
                )


            # =================================================
            # LOCAL SUCCESS
            # =================================================

            if (
                local_result
                and local_result.get(
                    "success"
                )
            ):

                answer = format_result(
                    local_result
                )

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.end_headers()

                self.wfile.write(

                    json.dumps(
                        {
                            "success": True,
                            "answer": answer,
                            "source":
                                "local_engine",
                            "api_used":
                                False
                        },
                        ensure_ascii=False
                    ).encode("utf-8")

                )

                return


            # =================================================
            # DATABASE PATTERN
            # =================================================

            pattern = find_pattern(
                question
            )


            # =================================================
            # AI FALLBACK
            # =================================================

            answer = solve_with_ai(
                question,
                image,
                pattern
            )


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.end_headers()

            self.wfile.write(

                json.dumps(
                    {
                        "success": True,
                        "answer": answer,
                        "source":
                            "ai",
                        "api_used":
                            True,
                        "pattern":
                            (
                                pattern.get("id")
                                if pattern
                                else None
                            )
                    },
                    ensure_ascii=False
                ).encode("utf-8")

            )


        except Exception as e:

            self.send_response(500)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.end_headers()

            self.wfile.write(

                json.dumps(
                    {
                        "success": False,
                        "error":
                            str(e)
                    },
                    ensure_ascii=False
                ).encode("utf-8")

    )
