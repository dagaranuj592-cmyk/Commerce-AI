import os
import json
import re
import base64
from http.server import BaseHTTPRequestHandler

from openai import OpenAI

from api.calculator import calculate


# ==========================================
# DATABASE PATH
# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PATTERN_DATABASE_PATH = os.path.join(
    BASE_DIR,
    "database",
    "accountancy",
    "patterns.json"
)


# ==========================================
# LOAD PATTERN DATABASE
# ==========================================

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


# ==========================================
# NUMBER EXTRACTION
# ==========================================

def extract_money_numbers(text):

    """
    Finds numbers such as:

    ₹3,20,000
    3,20,000
    ₹200000
    200000
    """

    matches = re.findall(
        r"(?:₹\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)",
        text
    )

    numbers = []

    for item in matches:

        try:

            value = float(
                item.replace(",", "")
            )

            numbers.append(value)

        except Exception:

            pass

    return numbers


# ==========================================
# EXTRACT PERCENTAGE
# ==========================================

def extract_percentage(text):

    patterns = [
        r"(\d+(?:\.\d+)?)\s*%",
        r"rate\s*(?:of\s*)?(?:return\s*)?(?:is|=)?\s*(\d+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1)
                )

            except Exception:

                pass

    return None


# ==========================================
# EXTRACT YEARS PURCHASE
# ==========================================

def extract_years_purchase(text):

    patterns = [
        r"(\d+(?:\.\d+)?)\s*years?\s*purchase",
        r"(\d+(?:\.\d+)?)\s*year\s*purchase",
        r"years?\s*purchase\s*(?:of|=)?\s*(\d+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1)
                )

            except Exception:

                pass

    return None


# ==========================================
# EXTRACT CAPITAL EMPLOYED
# ==========================================

def extract_capital_employed(text):

    patterns = [
        r"capital employed\s*(?:is|=|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"capital employed.{0,20}?₹?\s*([\d,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1).replace(
                        ",",
                        ""
                    )
                )

            except Exception:

                pass

    return None


# ==========================================
# EXTRACT AVERAGE PROFIT
# ==========================================

def extract_average_profit(text):

    patterns = [
        r"average profit\s*(?:is|=|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"average profits?\s*(?:is|=|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1).replace(
                        ",",
                        ""
                    )
                )

            except Exception:

                pass

    return None


# ==========================================
# HISTORICAL PROFIT DETECTION
# ==========================================

def extract_historical_profits(text):

    """
    Detect historical profits from questions like:

    The profits of the firm for the last four years were
    ₹3,20,000, ₹2,80,000, ₹3,60,000 and ₹4,00,000.
    """

    lower_text = text.lower()

    # Historical-profit question check
    if not (
        "profit" in lower_text
        and (
            "last" in lower_text
            or "previous" in lower_text
            or "past" in lower_text
        )
    ):
        return []

    # Find the part after "profits ... were/are"
    match = re.search(
        r"profits?.*?\b(?:were|are)\b(.*?)(?:\.|calculate|$)",
        text,
        re.IGNORECASE
    )

    if not match:
        return []

    profit_section = match.group(1)

    # Extract only money-like numbers from profit section
    matches = re.findall(
        r"(?:₹\s*)?(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)",
        profit_section
    )

    profits = []

    for item in matches:

        try:

            value = float(
                item.replace(",", "")
            )

            if value >= 1000:
                profits.append(value)

        except Exception:

            pass

    return profits


# ==========================================
# FIND DATABASE PATTERN
# ==========================================

def find_pattern(question):

    database = load_database()

    patterns = database.get(
        "patterns",
        []
    )

    question_lower = question.lower()

    best_pattern = None
    best_score = 0

    for pattern in patterns:

        keywords = pattern.get(
            "keywords",
            []
        )

        score = 0

        for keyword in keywords:

            if keyword.lower() in question_lower:

                score += 1

        if score > best_score:

            best_score = score
            best_pattern = pattern

    return best_pattern


# ==========================================
# LOCAL ACCOUNTANCY ENGINE
# ==========================================

def local_solve(question):

    q = question.lower()


    # ======================================
    # HISTORICAL PROFITS + GOODWILL
    # ======================================

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

        years_purchase = extract_years_purchase(
            question
        )

        capital = extract_capital_employed(
            question
        )

        rate = extract_percentage(
            question
        )

        # ----------------------------------
        # Super Profit Method
        # ----------------------------------

        if (
            len(profits) >= 2
            and years_purchase is not None
            and capital is not None
            and rate is not None
        ):

            total = sum(profits)

            average_profit = (
                total / len(profits)
            )

            result = calculate({
                "type": "goodwill_super_profit",
                "average_profit": average_profit,
                "capital_employed": capital,
                "normal_rate": rate,
                "years_purchase": years_purchase
            })

            if result:

                result["historical_profits"] = profits

                # Add detailed first steps
                result["steps"] = [
                    "Profits of previous years:",
                    " + ".join(
                        "₹" + format_number(x)
                        for x in profits
                    ),
                    "",
                    "Total Profit = "
                    + " + ".join(
                        "₹" + format_number(x)
                        for x in profits
                    ),
                    "Total Profit = ₹"
                    + format_number(total),
                    "",
                    "Average Profit = Total Profit ÷ Number of Years",
                    "Average Profit = ₹"
                    + format_number(total)
                    + " ÷ "
                    + str(len(profits)),
                    "Average Profit = ₹"
                    + format_number(average_profit),
                    "",
                    "Normal Profit = Capital Employed × Normal Rate / 100",
                    "Normal Profit = ₹"
                    + format_number(capital)
                    + " × "
                    + format_number(rate)
                    + " / 100",
                    "Normal Profit = ₹"
                    + format_number(
                        capital * rate / 100
                    ),
                    "",
                    "Super Profit = Average Profit − Normal Profit",
                    "Super Profit = ₹"
                    + format_number(average_profit)
                    + " − ₹"
                    + format_number(
                        capital * rate / 100
                    ),
                    "Super Profit = ₹"
                    + format_number(
                        average_profit
                        - (capital * rate / 100)
                    ),
                    "",
                    "Goodwill = Super Profit × Years' Purchase",
                    "Goodwill = ₹"
                    + format_number(
                        average_profit
                        - (capital * rate / 100)
                    )
                    + " × "
                    + format_number(
                        years_purchase
                    ),
                    "Goodwill = ₹"
                    + format_number(
                        (
                            average_profit
                            - (
                                capital
                                * rate
                                / 100
                            )
                        )
                        * years_purchase
                    )
                ]

                return result


        # ----------------------------------
        # Average Profit Method
        # ----------------------------------

        if (
            len(profits) >= 2
            and years_purchase is not None
        ):

            result = calculate({
                "type": "average_profit",
                "profits": profits
            })

            if result:

                average_profit = result["value"]

                goodwill_result = calculate({
                    "type": "goodwill_average_profit",
                    "average_profit": average_profit,
                    "years_purchase": years_purchase
                })

                if goodwill_result:

                    goodwill_result["steps"] = [
                        "Profits of previous years:",
                        " + ".join(
                            "₹" + format_number(x)
                            for x in profits
                        ),
                        "",
                        "Total Profit = ₹"
                        + format_number(
                            sum(profits)
                        ),
                        "Average Profit = Total Profit ÷ Number of Years",
                        "Average Profit = ₹"
                        + format_number(
                            average_profit
                        )
                        + " ÷ "
                        + str(len(profits)),
                        "Average Profit = ₹"
                        + format_number(
                            average_profit
                        ),
                        "",
                        "Goodwill = Average Profit × Years' Purchase",
                        "Goodwill = ₹"
                        + format_number(
                            average_profit
                        )
                        + " × "
                        + format_number(
                            years_purchase
                        ),
                        "Goodwill = ₹"
                        + format_number(
                            average_profit
                            * years_purchase
                        )
                    ]

                    return goodwill_result


    # ======================================
    # AVERAGE PROFIT
    # ======================================

    average_profit = extract_average_profit(
        question
    )

    if average_profit is not None:

        # Super Profit
        if (
            "super profit" in q
            and capital_is_present(question)
            and extract_percentage(question) is not None
        ):

            capital = extract_capital_employed(
                question
            )

            rate = extract_percentage(
                question
            )

            return calculate({
                "type": "super_profit",
                "average_profit": average_profit,
                "capital_employed": capital,
                "normal_rate": rate
            })


    # ======================================
    # CURRENT RATIO
    # ======================================

    if (
        "current ratio" in q
        and "current asset" in q
        and "current liabil" in q
    ):

        assets = find_labeled_number(
            question,
            [
                "current assets",
                "current asset"
            ]
        )

        liabilities = find_labeled_number(
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
                "type": "current_ratio",
                "current_assets": assets,
                "current_liabilities": liabilities
            })


    # ======================================
    # QUICK RATIO
    # ======================================

    if (
        (
            "quick ratio" in q
            or "liquid ratio" in q
        )
        and "current liabil" in q
    ):

        quick_assets = find_labeled_number(
            question,
            [
                "quick assets",
                "quick asset"
            ]
        )

        liabilities = find_labeled_number(
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
                "type": "quick_ratio",
                "quick_assets": quick_assets,
                "current_liabilities": liabilities
            })


    # ======================================
    # GROSS PROFIT RATIO
    # ======================================

    if "gross profit ratio" in q:

        gross_profit = find_labeled_number(
            question,
            [
                "gross profit"
            ]
        )

        revenue = find_labeled_number(
            question,
            [
                "revenue",
                "sales"
            ]
        )

        if (
            gross_profit is not None
            and revenue is not None
        ):

            return calculate({
                "type": "gross_profit_ratio",
                "gross_profit": gross_profit,
                "revenue": revenue
            })


    # ======================================
    # NET PROFIT RATIO
    # ======================================

    if "net profit ratio" in q:

        net_profit = find_labeled_number(
            question,
            [
                "net profit"
            ]
        )

        revenue = find_labeled_number(
            question,
            [
                "revenue",
                "sales"
            ]
        )

        if (
            net_profit is not None
            and revenue is not None
        ):

            return calculate({
                "type": "net_profit_ratio",
                "net_profit": net_profit,
                "revenue": revenue
            })


    # ======================================
    # ROI
    # ======================================

    if (
        "roi" in q
        or "return on investment" in q
    ):

        operating_profit = find_labeled_number(
            question,
            [
                "operating profit"
            ]
        )

        capital = find_labeled_number(
            question,
            [
                "capital employed"
            ]
        )

        if (
            operating_profit is not None
            and capital is not None
        ):

            return calculate({
                "type": "roi",
                "operating_profit": operating_profit,
                "capital_employed": capital
            })


    # ======================================
    # SUPER PROFIT
    # ======================================

    if "super profit" in q:

        capital = extract_capital_employed(
            question
        )

        rate = extract_percentage(
            question
        )

        if (
            average_profit is not None
            and capital is not None
            and rate is not None
        ):

            return calculate({
                "type": "super_profit",
                "average_profit": average_profit,
                "capital_employed": capital,
                "normal_rate": rate
            })


    return None


# ==========================================
# HELPERS
# ==========================================

def capital_is_present(text):

    return (
        "capital employed" in text.lower()
    )


def find_labeled_number(
    text,
    labels
):

    for label in labels:

        pattern = (
            re.escape(label)
            + r"\s*(?:is|=|are|of)?\s*"
            + r"₹?\s*"
            + r"([\d,]+(?:\.\d+)?)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                return float(
                    match.group(1).replace(
                        ",",
                        ""
                    )
                )

            except Exception:

                pass

    return None


def format_number(number):

    if isinstance(number, float):

        if number.is_integer():

            number = int(number)

    return f"{number:,}"


# ==========================================
# FORMAT RESULT
# ==========================================

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

    title = result.get(
        "title",
        "Solution"
    )

    lines.append(
        "📚 " + title
    )

    lines.append("")

    for step in result.get(
        "steps",
        []
    ):

        lines.append(step)

    lines.append("")

    value = result.get(
        "value"
    )

    title_lower = title.lower()

    if "ratio" in title_lower:

        lines.append(
            "✅ Final Answer: "
            + f"{value:.2f}".rstrip(
                "0"
            ).rstrip(".")
            + " : 1"
        )

    elif isinstance(value, (int, float)):

        lines.append(
            "✅ Final Answer: ₹"
            + format_number(value)
        )

    return "\n".join(lines)


# ==========================================
# AI FALLBACK
# ==========================================

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

Relevant pattern from our Commerce database:

Pattern:
""" + pattern.get(
            "id",
            ""
        ) + """

Chapter:
""" + pattern.get(
            "chapter",
            ""
        ) + """

Formula:
""" + pattern.get(
            "formula",
            ""
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

Solve the student's Commerce question.

Subjects:
- Accountancy
- Economics

Give an exam-ready, student-friendly solution.

For numerical questions:
1. Identify the given information.
2. Identify what is required.
3. Write the formula.
4. Substitute values.
5. Show every important calculation.
6. Give the final answer clearly.

Do not invent missing values.

""" + database_context + """

QUESTION:

""" + question

    content = [
        {
            "type": "input_text",
            "text": prompt
        }
    ]

    if image:

        content.append({
            "type": "input_image",
            "image_url": image
        })

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "user",
                "content": content
            }
        ]
    )

    return response.output_text


# ==========================================
# HTTP HANDLER
# ==========================================

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
                            "error": "Question ya photo required hai."
                        },
                        ensure_ascii=False
                    ).encode("utf-8")
                )

                return


            # ==================================
            # LOCAL ENGINE FIRST
            # ==================================

            local_result = None

            if question and not image:

                local_result = local_solve(
                    question
                )

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
                            "source": "local_database",
                            "api_used": False
                        },
                        ensure_ascii=False
                    ).encode("utf-8")
                )

                return


            # ==================================
            # DATABASE PATTERN
            # ==================================

            pattern = find_pattern(
                question
            )


            # ==================================
            # AI FALLBACK
            # ==================================

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
                        "pattern": (
                            pattern.get(
                                "id"
                            )
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
