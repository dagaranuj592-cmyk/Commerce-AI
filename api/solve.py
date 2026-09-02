import os
import json
import base64
from http.server import BaseHTTPRequestHandler
from openai import OpenAI


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            question = data.get("question", "").strip()
            image = data.get("image", "")

            client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )

            prompt = """
You are a Commerce education tutor.

Solve ONLY Commerce academic questions, especially:
1. Accountancy
2. Economics

Give a complete student-friendly solution.

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
- Solve every numerical step if applicable
- Explain graphs/diagrams when required
- Give an exam-ready final answer

If the question is unclear, say exactly what information is missing.
Do not invent figures or assumptions.

Question:
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

            answer = response.output_text

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "success": True,
                    "answer": answer
                }).encode("utf-8")
            )

        except Exception as e:

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "success": False,
                    "error": str(e)
                }).encode("utf-8")
            )
