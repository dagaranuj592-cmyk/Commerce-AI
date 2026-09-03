import os
import json
import re
import math

from http.server import BaseHTTPRequestHandler
from openai import OpenAI

from api.calculator import calculate


# =========================================================
# PATHS
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

        return {"patterns": []}


def find_pattern(question):

    database = load_database()

    patterns = database.get(
        "patterns",
        []
    )

    q = question.lower()

    best = None
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
            best = pattern

    return best


# =========================================================
# NUMBER HELPERS
# =========================================================

def clean_number(value):

    try:
        return float(
            str(value).replace(",", "").replace("₹", "").strip()
        )
    except Exception:
        return None


def format_number(number):

    if number is None:
        return "0"

    if isinstance(number, float) and number.is_integer():
        number = int(number)

    return f"{number:,}"


def format_ratio(number):

    return (
        f"{number:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def simplify_ratio(a, b):

    if a is None or b is None:
        return None

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
# EXTRACTION
# =========================================================

def extract_percentage(text):

    patterns = [

        r"(\d+(?:\.\d+)?)\s*%",

        r"normal\s+rate.*?(\d+(?:\.\d+)?)",

        r"rate\s+of\s+return.*?(\d+(?:\.\d+)?)"

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

        r"(\d+(?:\.\d+)?)\s*years?['’]?\s*purchase",

        r"(\d+(?:\.\d+)?)\s*year['’]?\s*purchase",

        r"purchase\s*(?:of|=)?\s*(\d+(?:\.\d+)?)\s*years?",

        r"years?['’]?\s*purchase\s*(?:of|=)?\s*(\d+(?:\.\d+)?)"

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

    pattern = (
        r"capital\s+employed"
        r".{0,30}?"
        r"(?:₹\s*)?"
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


def extract_average_profit(text):

    pattern = (
        r"average\s+profits?"
        r".{0,20}?"
        r"(?:₹\s*)?"
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


def extract_historical_profits(text):

    q = text.lower()

    if not (
        "profit" in q
        and (
            "last" in q
            or "previous" in q
            or "past" in q
        )
    ):
        return []

    match = re.search(
        r"profits?.*?\b(?:were|are)\b"
        r"(.*?)(?:\.|calculate|$)",
        text,
        re.IGNORECASE
    )

    if not match:
        return []

    section = match.group(1)

    matches = re.findall(
        r"(?:₹\s*)?"
        r"(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)",
        section
    )

    profits = []

    for item in matches:

        value = clean_number(item)

        if value is not None and value >= 1000:
            profits.append(value)

    return profits


def extract_labeled_number(text, labels):

    for label in labels:

        pattern = (
            re.escape(label)
            + r"\s*"
            r"(?:is|are|=|of)?\s*"
            r"(?:₹\s*)?"
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
# RATIO PARSER
# =========================================================

def extract_ratio(text, person):

    q = text.lower()

    # Examples:
    # A:B = 3:2
    # A and B are in ratio 3:2

    patterns = [

        rf"{person}\s*[:\-]?\s*"
        rf"{'B' if person == 'A' else 'A'}"
        rf"\s*(?:=|is|are|was|were|in)?\s*"
        rf"(\d+)\s*:\s*(\d+)",

        r"ratio\s*(?:of\s*)?"
        r"(\d+)\s*:\s*(\d+)"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return (
                float(match.group(1)),
                float(match.group(2))
            )

    # Specific old ratio:
    match = re.search(
        r"(?:old|existing|present).*?"
        r"ratio.*?"
        r"(\d+)\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return (
            float(match.group(1)),
            float(match.group(2))
        )

    return None


# =========================================================
# LOCAL SOLVER
# =========================================================

def local_solve(question):

    q = question.lower()


    # =====================================================
    # 1. HISTORICAL PROFITS + SUPER PROFIT GOODWILL
    # =====================================================

    if (
        "goodwill" in q
        and "profit" in q
        and (
            "last" in q
            or "previous" in q
            or "past" in q
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
                total / len(profits)
            )

            normal = (
                capital * rate / 100
            )

            super_profit = (
                average - normal
            )

            goodwill = (
                super_profit * years
            )

            return {
                "success": True,
                "title":
                    "Goodwill - Super Profit Method",
                "value":
                    goodwill,
                "steps": [

                    "Given:",

                    "Capital Employed = ₹"
                    + format_number(capital),

                    "Normal Rate of Return = "
                    + format_number(rate)
                    + "%",

                    "Profits = "
                    + ", ".join(
                        "₹" + format_number(x)
                        for x in profits
                    ),

                    "Years' Purchase = "
                    + format_number(years),

                    "",

                    "Step 1: Total Profit",

                    "Total Profit = "
                    + " + ".join(
                        "₹" + format_number(x)
                        for x in profits
                    ),

                    "Total Profit = ₹"
                    + format_number(total),

                    "",

                    "Step 2: Average Profit",

                    "Average Profit = "
                    "Total Profit ÷ Number of Years",

                    "Average Profit = ₹"
                    + format_number(total)
                    + " ÷ "
                    + str(len(profits)),

                    "Average Profit = ₹"
                    + format_number(average),

                    "",

                    "Step 3: Normal Profit",

                    "Normal Profit = "
                    "Capital Employed × Rate ÷ 100",

                    "Normal Profit = ₹"
                    + format_number(capital)
                    + " × "
                    + format_number(rate)
                    + " ÷ 100",

                    "Normal Profit = ₹"
                    + format_number(normal),

                    "",

                    "Step 4: Super Profit",

                    "Super Profit = "
                    "Average Profit − Normal Profit",

                    "Super Profit = ₹"
                    + format_number(average)
                    + " − ₹"
                    + format_number(normal),

                    "Super Profit = ₹"
                    + format_number(super_profit),

                    "",

                    "Step 5: Goodwill",

                    "Goodwill = "
                    "Super Profit × Years' Purchase",

                    "Goodwill = ₹"
                    + format_number(super_profit)
                    + " × "
                    + format_number(years),

                    "Goodwill = ₹"
                    + format_number(goodwill)

                ]
            }


    # =====================================================
    # 2. GOODWILL - AVERAGE PROFIT
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
    # 3. SUPER PROFIT
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
    # 4. CURRENT RATIO
    # =====================================================

    if "current ratio" in q:

        assets = extract_labeled_number(
            question,
            [
                "current assets",
                "current asset"
            ]
        )

        liabilities = extract_labeled_number(
            question,
            [
                "current liabilities",
                "current liability"
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
    # 5. QUICK RATIO
    # =====================================================

    if (
        "quick ratio" in q
        or "liquid ratio" in q
    ):

        quick_assets = extract_labeled_number(
            question,
            [
                "quick assets",
                "quick asset"
            ]
        )

        liabilities = extract_labeled_number(
            question,
            [
                "current liabilities",
                "current liability"
            ]
        )

        if (
            quick_assets is not None
            and liabilities is not None
        ):

            return calculate({

                "type":
                    "quick_ratio",

                "quick_assets":
                    quick_assets,

                "current_liabilities":
                    liabilities

            })


    # =====================================================
    # 6. DEBT EQUITY RATIO
    # =====================================================

    if "debt-equity ratio" in q or "debt equity ratio" in q:

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
                "shareholders funds",
                "shareholder funds"
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
    # 7. GROSS PROFIT RATIO
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
    # 8. NET PROFIT RATIO
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
    # 9. ROI
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
    # 10. INTEREST ON CAPITAL
    # =====================================================

    if (
        "interest on capital" in q
    ):

        capital = extract_labeled_number(
            question,
            [
                "capital",
                "capital account"
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
    # 11. INTEREST ON DRAWINGS
    # =====================================================

    if (
        "interest on drawings" in q
    ):

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
    # 12. CONTRIBUTION
    # =====================================================

    if "contribution" in q:

        sales = extract_labeled_number(
            question,
            [
                "sales"
            ]
        )

        variable_cost = extract_labeled_number(
            question,
            [
                "variable cost",
                "variable costs"
            ]
        )

        if (
            sales is not None
            and variable_cost is not None
        ):

            return calculate({

                "type":
                    "contribution",

                "sales":
                    sales,

                "variable_cost":
                    variable_cost

            })


    # =====================================================
    # 13. P/V RATIO
    # =====================================================

    if (
        "p/v ratio" in q
        or "profit volume ratio" in q
    ):

        contribution = extract_labeled_number(
            question,
            [
                "contribution"
            ]
        )

        sales = extract_labeled_number(
            question,
            [
                "sales"
            ]
        )

        if (
            contribution is not None
            and sales is not None
        ):

            return calculate({

                "type":
                    "profit_volume_ratio",

                "contribution":
                    contribution,

                "sales":
                    sales

            })


    # =====================================================
    # 14. BREAK EVEN POINT
    # =====================================================

    if (
        "break even" in q
        or "break-even" in q
    ):

        fixed_cost = extract_labeled_number(
            question,
            [
                "fixed cost",
                "fixed costs"
            ]
        )

        pv_match = re.search(
            r"(?:p/v|p-v|profit volume)"
            r".{0,15}?"
            r"(\d+(?:\.\d+)?)\s*%",
            question,
            re.IGNORECASE
        )

        pv_ratio = None

        if pv_match:
            pv_ratio = clean_number(
                pv_match.group(1)
            )

        if (
            fixed_cost is not None
            and pv_ratio is not None
        ):

            return calculate({

                "type":
                    "break_even_point",

                "fixed_cost":
                    fixed_cost,

                "pv_ratio":
                    pv_ratio

            })


    # =====================================================
    # 15. DEPRECIATION SLM
    # =====================================================

    if (
        "straight line" in q
        or "straight-line" in q
    ):

        cost = extract_labeled_number(
            question,
            [
                "cost",
                "original cost"
            ]
        )

        residual = extract_labeled_number(
            question,
            [
                "residual value",
                "scrap value"
            ]
        )

        life = extract_labeled_number(
            question,
            [
                "useful life",
                "life"
            ]
        )

        if cost is not None and life is not None:

            return calculate({

                "type":
                    "depreciation_straight_line",

                "cost":
                    cost,

                "residual_value":
                    residual or 0,

                "useful_life":
                    life

            })


    # =====================================================
    # 16. MPC
    # =====================================================

    if "mpc" in q:

        dc = extract_labeled_number(
            question,
            [
                "change in consumption",
                "change in consumption (dc)"
            ]
        )

        dy = extract_labeled_number(
            question,
            [
                "change in income",
                "change in income (dy)"
            ]
        )

        if dc is not None and dy is not None:

            return calculate({

                "type":
                    "mpc",

                "change_consumption":
                    dc,

                "change_income":
                    dy

            })


    # =====================================================
    # 17. MPS
    # =====================================================

    if re.search(
        r"\bmps\b",
        q
    ):

        ds = extract_labeled_number(
            question,
            [
                "change in saving",
                "change in savings"
            ]
        )

        dy = extract_labeled_number(
            question,
            [
                "change in income"
            ]
        )

        if ds is not None and dy is not None:

            return calculate({

                "type":
                    "mps",

                "change_saving":
                    ds,

                "change_income":
                    dy

            })


    # =====================================================
    # 18. MULTIPLIER
    # =====================================================

    if (
        "multiplier" in q
        and "money multiplier" not in q
    ):

        mpc_match = re.search(
            r"mpc.{0,15}?"
            r"(\d+(?:\.\d+)?)",
            question,
            re.IGNORECASE
        )

        if mpc_match:

            mpc = clean_number(
                mpc_match.group(1)
            )

            if mpc is not None:

                # If written as 0.8, use directly.
                # If written as 80%, convert.
                if mpc > 1:
                    mpc = mpc / 100

                return calculate({

                    "type":
                        "multiplier",

                    "mpc":
                        mpc

                })


    # =====================================================
    # NO LOCAL SOLUTION
    # =====================================================

    return None


# =========================================================
# FORMAT LOCAL RESULT
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

        lines.append("")

        if "ratio" in title:

            lines.append(
                "✅ Final Answer: "
                + format_ratio(value)
                + " : 1"
            )

        elif (
            "mpc" in title
            or "mps" in title
            or "multiplier" in title
        ):

            lines.append(
                "✅ Final Answer: "
                + format_ratio(value)
            )

        elif "%" in "\n".join(
            result.get("steps", [])
        ):

            lines.append(
                "✅ Final Answer: "
                + format_number(value)
                + "%"
            )

        else:

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

    context = ""

    if pattern:

        context = """

Relevant database pattern:

ID:
""" + str(
            pattern.get("id", "")
        ) + """

Chapter:
""" + str(
            pattern.get("chapter", "")
        ) + """

Formula:
""" + str(
            pattern.get("formula", "")
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

Solve only academic Commerce questions,
especially Accountancy and Economics.

Give:
1. Given information
2. Required
3. Formula/rule
4. Step-by-step calculation
5. Final answer

Do not invent missing information.

""" + context + """

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

            length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(
                length
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


            # =============================================
            # EMPTY INPUT
            # =============================================

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


            # =============================================
            # LOCAL ENGINE FIRST
            # =============================================

            local_result = None

            if question and not image:

                local_result = local_solve(
                    question
                )


            # =============================================
            # LOCAL ANSWER
            # =============================================

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
                                "local_database",
                            "api_used":
                                False
                        },
                        ensure_ascii=False
                    ).encode("utf-8")
                )

                return


            # =============================================
            # DATABASE PATTERN
            # =============================================

            pattern = find_pattern(
                question
            )


            # =============================================
            # AI FALLBACK
            # =============================================

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
                        "source": "ai",
                        "api_used": True,
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
                        "error": str(e)
                    },
                    ensure_ascii=False
                ).encode("utf-8")
        )
