import os
import json
import re
from http.server import BaseHTTPRequestHandler

from openai import OpenAI

from api.calculator import calculate


# -----------------------------------
# DATABASE
# -----------------------------------

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "database",
    "accountancy.json"
)


def load_database():

    try:

        with open(
            DATABASE_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


# -----------------------------------
# FORMULA SEARCH
# -----------------------------------

def find_formulas(question, database):

    question_lower = question.lower()

    matches = []

    chapters = database.get(
        "chapters",
        {}
    )

    for chapter_key, chapter in chapters.items():

        chapter_name = chapter.get(
            "name",
            ""
        ).lower()

        formulas = chapter.get(
            "formulas",
            {}
        )

        for formula_key, formula_data in formulas.items():

            formula_text = formula_data.get(
                "formula",
                ""
            )

            use_when = formula_data.get(
                "use_when",
                ""
            )

            search_text = (
                chapter_name
                + " "
                + formula_key.replace("_", " ")
                + " "
                + formula_text
                + " "
                + use_when
            ).lower()

            score = 0

            for word in question_lower.split():

                word = word.strip(
                    ".,!?():;"
                )

                if (
                    len(word) >= 4
                    and word in search_text
                ):

                    score += 1

            if score > 0:

                matches.append({
                    "chapter": chapter_name,
                    "formula": formula_text,
                    "use_when": use_when,
                    "score": score
                })

    matches.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return matches[:5]


# -----------------------------------
# NUMBER HELPERS
# -----------------------------------

def clean_number(value):

    value = value.replace(
        ",",
        ""
    )

    value = value.replace(
        "₹",
        ""
    )

    value = value.strip()

    return float(value)


def find_number_after_patterns(
    question,
    patterns
):

    for pattern in patterns:

        match = re.search(
            pattern,
            question,
            re.IGNORECASE
        )

        if match:

            try:

                return clean_number(
                    match.group(1)
                )

            except Exception:

                pass

    return None


# -----------------------------------
# AUTOMATIC QUESTION DETECTION
# -----------------------------------

def detect_and_calculate(question):

    q = question.lower()


    # =================================
    # CURRENT RATIO
    # =================================

    if (
        "current ratio" in q
        and (
            "current assets" in q
            or "current asset" in q
        )
        and (
            "current liabilities" in q
            or "current liability" in q
        )
    ):

        assets = find_number_after_patterns(
            question,
            [
                r"current assets?\s*(?:=|are|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"current assets?.{0,20}?₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        liabilities = find_number_after_patterns(
            question,
            [
                r"current liabilities?\s*(?:=|are|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"current liabilities?.{0,20}?₹?\s*([\d,]+(?:\.\d+)?)"
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


    # =================================
    # QUICK RATIO
    # =================================

    if (
        "quick ratio" in q
        or "liquid ratio" in q
    ):

        quick_assets = find_number_after_patterns(
            question,
            [
                r"quick assets?\s*(?:=|are|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"quick assets?.{0,20}?₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        liabilities = find_number_after_patterns(
            question,
            [
                r"current liabilities?\s*(?:=|are|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
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


    # =================================
    # SUPER PROFIT / GOODWILL
    # =================================

    if (
        "super profit" in q
        or (
            "goodwill" in q
            and "normal rate" in q
        )
    ):

        average_profit = find_number_after_patterns(
            question,
            [
                r"average profit\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"average profits?\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        capital = find_number_after_patterns(
            question,
            [
                r"capital employed\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"capital employed.{0,20}?₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        rate = find_number_after_patterns(
            question,
            [
                r"normal rate(?: of return)?\s*(?:=|is|of)?\s*([\d.]+)\s*%?",
                r"normal rate.{0,15}?([\d.]+)\s*%"
            ]
        )

        years = find_number_after_patterns(
            question,
            [
                r"(\d+(?:\.\d+)?)\s*(?:years?|year)\s*(?:purchase|purchases)",
                r"years?'?\s*purchase\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)"
            ]
        )

        if (
            average_profit is not None
            and capital is not None
            and rate is not None
        ):

            if (
                "goodwill" in q
                and years is not None
            ):

                return calculate({
                    "type": "goodwill_super_profit",
                    "average_profit": average_profit,
                    "capital_employed": capital,
                    "normal_rate": rate,
                    "years_purchase": years
                })

            return calculate({
                "type": "super_profit",
                "average_profit": average_profit,
                "capital_employed": capital,
                "normal_rate": rate
            })


    # =================================
    # AVERAGE PROFIT GOODWILL
    # =================================

    if (
        "goodwill" in q
        and (
            "average profit" in q
            or "average profit method" in q
        )
    ):

        average_profit = find_number_after_patterns(
            question,
            [
                r"average profit\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        years = find_number_after_patterns(
            question,
            [
                r"(\d+(?:\.\d+)?)\s*(?:years?|year)\s*(?:purchase|purchases)",
                r"years?'?\s*purchase\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)"
            ]
        )

        if (
            average_profit is not None
            and years is not None
        ):

            return calculate({
                "type": "goodwill_average_profit",
                "average_profit": average_profit,
                "years_purchase": years
            })


    # =================================
    # GROSS PROFIT RATIO
    # =================================

    if "gross profit ratio" in q:

        gross_profit = find_number_after_patterns(
            question,
            [
                r"gross profit\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        revenue = find_number_after_patterns(
            question,
            [
                r"revenue(?: from operations)?\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"sales\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
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


    # =================================
    # NET PROFIT RATIO
    # =================================

    if "net profit ratio" in q:

        net_profit = find_number_after_patterns(
            question,
            [
                r"net profit\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        revenue = find_number_after_patterns(
            question,
            [
                r"revenue(?: from operations)?\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)",
                r"sales\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
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


    # =================================
    # ROI
    # =================================

    if (
        "roi" in q
        or "return on investment" in q
    ):

        operating_profit = find_number_after_patterns(
            question,
            [
                r"operating profit\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        capital = find_number_after_patterns(
            question,
            [
                r"capital employed\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
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


    # =================================
    # INTEREST ON CAPITAL
    # =================================

    if "interest on capital" in q:

        capital = find_number_after_patterns(
            question,
            [
                r"capital\s*(?:=|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        rate = find_number_after_patterns(
            question,
            [
                r"rate\s*(?:=|is|of)?\s*([\d.]+)\s*%"
            ]
        )

        time = find_number_after_patterns(
            question,
            [
                r"time\s*(?:=|is|of)?\s*([\d.]+)",
                r"for\s*([\d.]+)\s*(?:year|years)"
            ]
        )

        if (
            capital is not None
            and rate is not None
        ):

            return calculate({
                "type": "interest_on_capital",
                "capital": capital,
                "rate": rate,
                "time": time if time else 1
            })


    # =================================
    # INTEREST ON DRAWINGS
    # =================================

    if "interest on drawings" in q:

        drawings = find_number_after_patterns(
            question,
            [
                r"drawings\s*(?:=|are|is|of)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
            ]
        )

        rate = find_number_after_patterns(
            question,
            [
                r"rate\s*(?:=|is|of)?\s*([\d.]+)\s*%"
            ]
        )

        time = find_number_after_patterns(
            question,
            [
                r"time\s*(?:=|is|of)?\s*([\d.]+)",
                r"for\s*([\d.]+)\s*(?:year|years)"
            ]
        )

        if (
            drawings is not None
            and rate is not None
        ):

            return calculate({
                "type": "interest_on_drawings",
                "drawings": drawings,
                "rate": rate,
                "time": time if time else 1
            })


    return None


# -----------------------------------
# FORMAT CALCULATOR ANSWER
# -----------------------------------

def format_calculator_answer(result):

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

    lines.append("")

    value = result.get(
        "value"
    )

    # Ratio values should NOT have ₹
    title = result.get(
        "title",
        ""
    ).lower()

    if "ratio" in title:

        if isinstance(value, float):

            if value.is_integer():

                value_text = str(
                    int(value)
                )

            else:

                value_text = f"{value:.2f}".rstrip(
                    "0"
                ).rstrip(".")

        else:

            value_text = str(value)

    else:

        if isinstance(value, float):

            if value.is_integer():

                value_text = (
                    "₹"
                    + f"{int(value):,}"
                )

            else:

                value_text = (
                    "₹"
                    + f"{value:,.2f}"
                )

        else:

            value_text = str(value)

    lines.append(
        "✅ Final Answer: "
        + value_text
    )

    return "\n".join(lines)


# -----------------------------------
# AI FALLBACK
# -----------------------------------

def solve_with_ai(
    question,
    image,
    formula_matches
):

    client = OpenAI(
        api_key=os.environ.get(
            "OPENAI_API_KEY"
        )
    )

    database_context = ""

    if formula_matches:

        database_context = (
            "\n\nOUR OWN FORMULA DATABASE:\n"
        )

        for item in formula_matches:

            database_context += (
                "\nChapter: "
                + item["chapter"]
                + "\nFormula: "
                + item["formula"]
                + "\nUse when: "
                + item["use_when"]
                + "\n"
            )

    prompt = """
You are Commerce AI.

Solve ONLY Commerce academic questions.

Subjects:
1. Accountancy
2. Economics

Give a complete student-friendly solution.

Use our own formula database whenever a relevant formula exists.

For Accountancy:
- Identify what is given
- Identify what is required
- Write the relevant formula/rule
- Show every calculation step
- Show working notes where needed
- Give the final answer clearly
- Do not skip important steps

For Economics:
- Identify the concept
- Explain it simply
- Solve numerical questions step by step
- Explain graphs when required
- Give an exam-ready final answer

Do not invent figures or assumptions.

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


# -----------------------------------
# HTTP HANDLER
# -----------------------------------

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

            data = json.loads(body)

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


            # --------------------------------
            # STEP 1:
            # TRY OUR OWN CALCULATOR
            # --------------------------------

            calculator_result = None

            if question and not image:

                calculator_result = (
                    detect_and_calculate(
                        question
                    )
                )


            # --------------------------------
            # CALCULATOR SUCCESS
            # NO API CALL
            # --------------------------------

            if (
                calculator_result
                and calculator_result.get(
                    "success"
                )
            ):

                answer = format_calculator_answer(
                    calculator_result
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
                            "source": "calculator",
                            "api_used": False
                        },
                        ensure_ascii=False
                    ).encode("utf-8")
                )

                return


            # --------------------------------
            # STEP 2:
            # SEARCH DATABASE
            # --------------------------------

            database = load_database()

            formula_matches = find_formulas(
                question,
                database
            )


            # --------------------------------
            # STEP 3:
            # AI FALLBACK
            # --------------------------------

            answer = solve_with_ai(
                question,
                image,
                formula_matches
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
                        "database_matches": len(
                            formula_matches
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
