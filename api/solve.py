import os
import json
from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# -----------------------------
# LOAD OUR OWN DATABASE
# -----------------------------

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "database",
    "accountancy.json"
)


def load_database():

    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return {}


# -----------------------------
# SEARCH FORMULAS
# -----------------------------

def find_formulas(question, database):

    question_lower = question.lower()

    matches = []

    chapters = database.get("chapters", {})

    for chapter_key, chapter in chapters.items():

        chapter_name = chapter.get("name", "").lower()

        formulas = chapter.get("formulas", {})

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

            words = question_lower.split()

            score = 0

            for word in words:

                if len(word) >= 4 and word in search_text:
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


# -----------------------------
# AI FALLBACK
# -----------------------------

def solve_with_ai(question, image, formula_matches):

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    database_context = ""

    if formula_matches:

        database_context = "\n\nOUR FORMULA DATABASE:\n"

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

IMPORTANT:
Our own formula database is provided below.
Use the database formulas when they are relevant.
Do NOT invent a different formula when the database formula applies.

For Accountancy:
- Identify what is given
- Identify what is required
- Write the relevant formula
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

If the question is unclear, clearly state what information is missing.
Do not invent figures.

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


# -----------------------------
# HTTP HANDLER
# -----------------------------

class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = self.rfile.read(length)

            data = json.loads(body)

            question = data.get(
                "question",
                ""
            ).strip()

            image = data.get(
                "image",
                ""
            )

            if not question and not image:

                self.send_response(400)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                self.wfile.write(
                    json.dumps({
                        "success": False,
                        "error": "Question ya photo required hai."
                    }).encode("utf-8")
                )

                return

            # Load our database
            database = load_database()

            # Search relevant formulas
            formula_matches = find_formulas(
                question,
                database
            )

            # AI currently handles the final solution
            answer = solve_with_ai(
                question,
                image,
                formula_matches
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "success": True,
                    "answer": answer,
                    "database_matches": len(
                        formula_matches
                    )
                }).encode("utf-8")
            )

        except Exception as e:

            self.send_response(500)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "success": False,
                    "error": str(e)
                }).encode("utf-8")
    )
