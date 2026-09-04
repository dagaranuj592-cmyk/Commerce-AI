import os
import re
import json
import ast
import operator as op
from http.server import BaseHTTPRequestHandler

# =========================================================
# COMMERCE AI - DETAILED ACCOUNTANCY SOLVER
# =========================================================

# -------------------------
# BASIC HELPERS
# -------------------------

def normalize(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace("₹", " ")
    text = text.replace("rs.", " ")
    text = text.replace("Rs.", " ")
    text = text.replace("Rs", " ")
    text = text.replace(",", "")
    text = text.replace("×", "*")
    text = text.replace("÷", "/")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    return text.lower().strip()


def clean_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except:
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
    except:
        return str(value)


def money(value):
    return "₹" + format_number(value)


def format_decimal(value, places=2):
    try:
        return f"{float(value):.{places}f}"
    except:
        return str(value)


def percentage(value):
    try:
        return f"{float(value):.2f}%"
    except:
        return str(value)


def all_numbers(text):
    text = str(text).replace(",", "")
    nums = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text)
    return [float(x) for x in nums]


def first_number(text):
    nums = all_numbers(text)
    return nums[0] if nums else None


def safe_div(a, b):
    try:
        if b == 0:
            return None
        return a / b
    except:
        return None


def fraction_text(num, den):
    if den == 0:
        return "undefined"
    return f"{num}/{den}"


# -------------------------
# FRACTION / RATIO HELPERS
# -------------------------

def gcd(a, b):
    a = abs(int(a))
    b = abs(int(b))
    while b:
        a, b = b, a % b
    return a


def simplify_ratio(values):
    values = [int(round(float(x))) for x in values]
    if not values:
        return ""
    g = values[0]
    for x in values[1:]:
        g = gcd(g, x)
    if g == 0:
        return ":".join(map(str, values))
    return ":".join(str(int(x / g)) for x in values)


def parse_fraction(s):
    if not s:
        return None

    s = str(s).strip()

    m = re.search(r"(\d+)\s*/\s*(\d+)", s)
    if m:
        return float(m.group(1)) / float(m.group(2))

    m = re.search(r"(\d+)\s*:\s*(\d+)", s)
    if m:
        return float(m.group(1)) / float(m.group(2))

    return None


def extract_ratio(text):
    text = normalize(text)

    patterns = [
        r"ratio\s*(?:of|is|=|:)?\s*(\d+)\s*:\s*(\d+)",
        r"sharing.*?(\d+)\s*:\s*(\d+)",
        r"profits.*?(\d+)\s*:\s*(\d+)"
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1)), int(m.group(2))

    return None


def extract_percentage(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text))
    return float(m.group(1)) if m else None


def extract_share(text):
    text = normalize(text)

    m = re.search(
        r"(?:for|admits?.*?for|admit.*?for)\s*(?:a\s*)?(\d+)\s*/\s*(\d+)\s*(?:share)?",
        text
    )

    if m:
        return float(m.group(1)) / float(m.group(2))

    m = re.search(r"(\d+)\s*/\s*(\d+)\s*share", text)
    if m:
        return float(m.group(1)) / float(m.group(2))

    return None


# -------------------------
# MONEY EXTRACTION
# -------------------------

def extract_labeled_number(text, labels):
    text = str(text)

    for label in labels:
        pattern = rf"{label}\s*(?:=|is|of|amount)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"
        m = re.search(pattern, text, re.I)
        if m:
            return clean_number(m.group(1))

    return None


def extract_amount_after(text, phrases):
    text = str(text)

    for phrase in phrases:
        pattern = rf"{phrase}\s*(?:=|is|of|amounting\s+to|worth)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"
        m = re.search(pattern, text, re.I)
        if m:
            return clean_number(m.group(1))

    return None


# =========================================================
# SAFE MATH
# =========================================================

_ALLOWED_BIN = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}

_ALLOWED_UNARY = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def safe_math(expression):
    try:
        expression = expression.replace(",", "")
        tree = ast.parse(expression, mode="eval")

        def calc(node):
            if isinstance(node, ast.Expression):
                return calc(node.body)

            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError()

            if isinstance(node, ast.BinOp):
                fn = _ALLOWED_BIN.get(type(node.op))
                if not fn:
                    raise ValueError()
                return fn(calc(node.left), calc(node.right))

            if isinstance(node, ast.UnaryOp):
                fn = _ALLOWED_UNARY.get(type(node.op))
                if not fn:
                    raise ValueError()
                return fn(calc(node.operand))

            raise ValueError()

        return calc(tree)

    except:
        return None


# =========================================================
# GOODWILL
# =========================================================

def solve_goodwill_average(text):
    n = normalize(text)

    if "average profit" not in n:
        return None

    profits = []

    m = re.search(
        r"profits?\s*(?:are|were|of)?\s*([\d,\s]+(?:and|,)\s*[\d,\s]+(?:and|,)?[\d,\s]*)",
        text,
        re.I
    )

    if m:
        profits = all_numbers(m.group(1))

    if not profits:
        nums = all_numbers(text)
        if len(nums) >= 3:
            profits = nums[:3]

    years = extract_labeled_number(text, ["years?['’]? purchase", "years?"])

    if years is None:
        m = re.search(r"(\d+)\s*(?:years?|year).*?(?:purchase|goodwill)", n)
        if m:
            years = float(m.group(1))

    if not profits or years is None:
        return None

    avg = sum(profits) / len(profits)
    goodwill = avg * years

    return f"""DETAILED SOLUTION — GOODWILL BY AVERAGE PROFIT METHOD

Given:
Profits = {", ".join(money(x) for x in profits)}
Number of years' purchase = {format_number(years)}

Step 1: Calculate Average Profit

Average Profit
= Total Profits / Number of Years

= ({' + '.join(money(x) for x in profits)}) / {format_number(len(profits))}

= {money(avg)}

Step 2: Calculate Goodwill

Formula:
Goodwill = Average Profit × Years' Purchase

= {money(avg)} × {format_number(years)}

= {money(goodwill)}

FINAL ANSWER:
Goodwill = {money(goodwill)}
"""



def solve_goodwill_super(text):
    n = normalize(text)

    if "super profit" not in n:
        return None

    avg = extract_labeled_number(text, ["average profit"])
    normal = extract_labeled_number(text, ["normal profit"])

    years = extract_labeled_number(
        text,
        ["years?['’]? purchase", "years? purchase"]
    )

    if avg is None or normal is None or years is None:
        return None

    super_profit = avg - normal
    goodwill = super_profit * years

    return f"""DETAILED SOLUTION — GOODWILL BY SUPER PROFIT METHOD

Given:
Average Profit = {money(avg)}
Normal Profit = {money(normal)}
Years' Purchase = {format_number(years)}

Step 1: Calculate Super Profit

Formula:
Super Profit = Average Profit - Normal Profit

= {money(avg)} - {money(normal)}

= {money(super_profit)}

Step 2: Calculate Goodwill

Formula:
Goodwill = Super Profit × Years' Purchase

= {money(super_profit)} × {format_number(years)}

= {money(goodwill)}

FINAL ANSWER:
Super Profit = {money(super_profit)}
Goodwill = {money(goodwill)}
"""



def solve_goodwill_capitalisation(text):
    n = normalize(text)

    if "capitalisation" not in n and "capitalization" not in n:
        return None

    avg = extract_labeled_number(text, ["average profit"])
    normal_rate = extract_labeled_number(
        text,
        ["normal rate", "normal rate of return"]
    )
    net_assets = extract_labeled_number(
        text,
        ["capital employed", "net assets"]
    )

    if avg is None or normal_rate is None:
        return None

    capitalised = safe_div(avg * 100, normal_rate)

    goodwill = None

    if net_assets is not None:
        goodwill = capitalised - net_assets

    result = f"""DETAILED SOLUTION — CAPITALISATION METHOD

Given:
Average Profit = {money(avg)}
Normal Rate of Return = {format_number(normal_rate)}%
"""

    result += f"""
Step 1: Calculate Capitalised Value of Average Profit

Formula:
Capitalised Value
= Average Profit × 100 / Normal Rate

= {money(avg)} × 100 / {format_number(normal_rate)}

= {money(capitalised)}
"""

    if net_assets is not None:
        result += f"""
Step 2: Calculate Goodwill

Formula:
Goodwill = Capitalised Value - Net Assets

= {money(capitalised)} - {money(net_assets)}

= {money(goodwill)}

FINAL ANSWER:
Goodwill = {money(goodwill)}
"""
    else:
        result += "\nNet Assets were not provided, so goodwill cannot be completed."

    return result


# =========================================================
# SUPER PROFIT
# =========================================================

def solve_super_profit(text):
    n = normalize(text)

    if "super profit" not in n:
        return None

    avg = extract_labeled_number(text, ["average profit"])
    normal = extract_labeled_number(text, ["normal profit"])

    if avg is None or normal is None:
        return None

    sp = avg - normal

    return f"""DETAILED SOLUTION — SUPER PROFIT

Given:
Average Profit = {money(avg)}
Normal Profit = {money(normal)}

Formula:
Super Profit = Average Profit - Normal Profit

= {money(avg)} - {money(normal)}

= {money(sp)}

FINAL ANSWER:
Super Profit = {money(sp)}
"""


# =========================================================
# PARTNERSHIP — ADMISSION
# =========================================================

def solve_admission(text):
    n = normalize(text)

    if "admit" not in n and "admission" not in n:
        return None

    ratio = extract_ratio(text)
    c_share = extract_share(text)

    if ratio is None or c_share is None:
        return None

    a_old, b_old = ratio
    total_old = a_old + b_old

    a_old_share = a_old / total_old
    b_old_share = b_old / total_old

    remaining = 1 - c_share

    # Future profits equally
    equal_future = bool(
        re.search(
            r"(a\s*and\s*b|a\s*&\s*b).*?(share|divide).*?(equally|equal)",
            n
        )
        or re.search(
            r"(future\s+profits?|profits?).*?(equally|equal).*?(a\s*and\s*b|a\s*&\s*b)",
            n
        )
    )

    if equal_future:
        a_new = remaining / 2
        b_new = remaining / 2
    else:
        a_new = remaining * a_old_share
        b_new = remaining * b_old_share

    c_new = c_share

    sacrifice_a = a_old_share - a_new
    sacrifice_b = b_old_share - b_new

    new_ratio_values = [
        round(a_new * 1000000),
        round(b_new * 1000000),
        round(c_new * 1000000)
    ]

    sac_values = [
        round(sacrifice_a * 1000000),
        round(sacrifice_b * 1000000)
    ]

    new_ratio = simplify_ratio(new_ratio_values)
    sacrifice_ratio = simplify_ratio(sac_values)

    # Goodwill premium
    premium = None

    direct_patterns = [
        r"goodwill\s+premium\s*(?:=|is|of)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
        r"premium\s+for\s+goodwill\s*(?:=|is|of)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
        r"goodwill\s+premium.*?(?:brings?|brought).*?(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)"
    ]

    for p in direct_patterns:
        m = re.search(p, text, re.I)
        if m:
            premium = clean_number(m.group(1))
            break

    if premium is None:
        premium = extract_amount_after(
            text,
            [
                r"brings?\s*(?:₹|rs\.?|inr)?",
                r"brought\s*(?:₹|rs\.?|inr)?",
                r"goodwill\s+premium",
                r"premium\s+for\s+goodwill"
            ]
        )

    goodwill_value = extract_labeled_number(
        text,
        ["goodwill of the firm", "firm goodwill", "goodwill"]
    )

    capital = extract_labeled_number(
        text,
        ["capital", "capital brought", "brings.*?capital"]
    )

    result = f"""DETAILED SOLUTION — ADMISSION OF A PARTNER

STEP 1: Old Profit-Sharing Ratio

A : B = {a_old} : {b_old}

Total = {a_old + b_old}

A's old share
= {a_old}/{a_old + b_old}
= {fraction_text(a_old, total_old)}

B's old share
= {b_old}/{a_old + b_old}
= {fraction_text(b_old, total_old)}

STEP 2: C's Share

C is admitted for = {c_share:.4f}
= {c_share * 100:.2f}%

STEP 3: Remaining Share of A and B

Remaining share
= 1 - C's share

= 1 - {c_share:.4f}

= {remaining:.4f}
"""

    if equal_future:
        result += f"""
STEP 4: New Shares of A and B

Since A and B decide to share future profits equally:

A's new share
= {remaining:.4f} / 2
= {a_new:.4f}

B's new share
= {remaining:.4f} / 2
= {b_new:.4f}

C's new share
= {c_new:.4f}
"""
    else:
        result += f"""
STEP 4: New Shares of A and B

The remaining profit is divided according to their old ratio.

A's new share
= {remaining:.4f} × {a_old}/{total_old}
= {a_new:.4f}

B's new share
= {remaining:.4f} × {b_old}/{total_old}
= {b_new:.4f}

C's new share
= {c_new:.4f}
"""

    result += f"""
STEP 5: New Profit-Sharing Ratio

A : B : C
= {a_new:.4f} : {b_new:.4f} : {c_new:.4f}

Therefore:

NEW RATIO = {new_ratio}

STEP 6: Sacrificing Ratio

Sacrifice = Old Share - New Share

A's sacrifice
= {a_old_share:.4f} - {a_new:.4f}
= {sacrifice_a:.4f}

B's sacrifice
= {b_old_share:.4f} - {b_new:.4f}
= {sacrifice_b:.4f}

Therefore:

SACRIFICING RATIO = {sacrifice_ratio}
"""

    if goodwill_value is not None:
        implied = goodwill_value * c_share

        result += f"""
STEP 7: Goodwill

Goodwill of firm = {money(goodwill_value)}

C's share = {c_share:.4f}

C's share of goodwill
= {money(goodwill_value)} × {c_share:.4f}
= {money(implied)}
"""

    if premium is not None:
        result += f"""
C brings Goodwill Premium = {money(premium)}

Distribution of premium is made among sacrificing partners in their sacrificing ratio.

A's sacrifice = {sacrifice_a:.4f}
B's sacrifice = {sacrifice_b:.4f}
"""

        total_sac = sacrifice_a + sacrifice_b

        if total_sac > 0:
            a_premium = premium * sacrifice_a / total_sac
            b_premium = premium * sacrifice_b / total_sac

            result += f"""
A's share of premium
= {money(premium)} × {sacrifice_a:.4f}/{total_sac:.4f}
= {money(a_premium)}

B's share of premium
= {money(premium)} × {sacrifice_b:.4f}/{total_sac:.4f}
= {money(b_premium)}
"""
        else:
            a_premium = b_premium = 0

    else:
        a_premium = b_premium = None

    if capital is not None:
        result += f"""
C's Capital = {money(capital)}
"""

    if capital is not None or premium is not None:
        result += """

JOURNAL ENTRIES
----------------
"""

        if capital is not None and premium is not None:
            total_bank = capital + premium

            result += f"""
Bank A/c Dr.                         {money(total_bank)}
      To C's Capital A/c                         {money(capital)}
      To Premium for Goodwill A/c               {money(premium)}

(Being C's capital and goodwill premium brought in cash)
"""

            if a_premium is not None and b_premium is not None:
                if a_premium > 0:
                    result += f"""
Premium for Goodwill A/c Dr.       {money(premium)}
      To A's Capital A/c                         {money(a_premium)}
      To B's Capital A/c                         {money(b_premium)}

(Being goodwill premium distributed among sacrificing partners)
"""

        elif capital is not None:
            result += f"""
Bank A/c Dr.                         {money(capital)}
      To C's Capital A/c                         {money(capital)}

(Being C's capital brought in cash)
"""

        elif premium is not None:
            result += f"""
Bank A/c Dr.                         {money(premium)}
      To Premium for Goodwill A/c               {money(premium)}

(Being goodwill premium brought in cash by C)
"""

    result += f"""

FINAL ANSWER
------------
New Profit-Sharing Ratio = {new_ratio}
Sacrificing Ratio of A and B = {sacrifice_ratio}
"""

    return result


# =========================================================
# PARTNERSHIP — REVALUATION
# =========================================================

def solve_revaluation(text):
    n = normalize(text)

    if "revaluation" not in n and "revalued" not in n:
        return None

    gains = []
    losses = []

    patterns_gain = [
        r"(\w+)\s+(?:was\s+)?increased\s+by\s+(?:₹|rs\.?|inr)?\s*([\d,]+)",
        r"(\w+)\s+(?:is\s+)?appreciated\s+by\s+(?:₹|rs\.?|inr)?\s*([\d,]+)"
    ]

    patterns_loss = [
        r"(\w+)\s+(?:was\s+)?decreased\s+by\s+(?:₹|rs\.?|inr)?\s*([\d,]+)",
        r"(\w+)\s+(?:is\s+)?reduced\s+by\s+(?:₹|rs\.?|inr)?\s*([\d,]+)"
    ]

    for p in patterns_gain:
        for m in re.finditer(p, text, re.I):
            gains.append((m.group(1), clean_number(m.group(2))))

    for p in patterns_loss:
        for m in re.finditer(p, text, re.I):
            losses.append((m.group(1), clean_number(m.group(2))))

    if not gains and not losses:
        return None

    total_gain = sum(x[1] for x in gains)
    total_loss = sum(x[1] for x in losses)
    profit = total_gain - total_loss

    result = """DETAILED SOLUTION — REVALUATION ACCOUNT

STEP 1: Revaluation Gains
"""

    if gains:
        for name, amount in gains:
            result += f"{name.title()} increased = {money(amount)}\n"
    else:
        result += "No revaluation gain identified.\n"

    result += f"""
Total Gain = {money(total_gain)}

STEP 2: Revaluation Losses
"""

    if losses:
        for name, amount in losses:
            result += f"{name.title()} decreased = {money(amount)}\n"
    else:
        result += "No revaluation loss identified.\n"

    result += f"""
Total Loss = {money(total_loss)}

STEP 3: Revaluation Profit / Loss

Revaluation Result
= Total Gain - Total Loss

= {money(total_gain)} - {money(total_loss)}

= {money(abs(profit))}

FINAL ANSWER:
"""

    if profit >= 0:
        result += f"Revaluation Profit = {money(profit)}"
    else:
        result += f"Revaluation Loss = {money(abs(profit))}"

    return result


# =========================================================
# ACCOUNTING RATIOS
# =========================================================

def solve_ratio(text):
    n = normalize(text)

    # Current Ratio
    if "current ratio" in n:
        ca = extract_labeled_number(
            text,
            ["current assets", "current asset"]
        )
        cl = extract_labeled_number(
            text,
            ["current liabilities", "current liability"]
        )

        if ca is not None and cl is not None:
            r = safe_div(ca, cl)

            return f"""DETAILED SOLUTION — CURRENT RATIO

Formula:
Current Ratio = Current Assets / Current Liabilities

= {money(ca)} / {money(cl)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Current Ratio = {format_decimal(r)} : 1
"""

    # Quick Ratio
    if "quick ratio" in n:
        ca = extract_labeled_number(text, ["current assets"])
        inv = extract_labeled_number(text, ["inventory", "inventories"])
        prepaid = extract_labeled_number(
            text,
            ["prepaid expenses", "prepaid expense"]
        )
        cl = extract_labeled_number(text, ["current liabilities"])

        if ca is not None and cl is not None:
            quick_assets = ca

            if inv is not None:
                quick_assets -= inv

            if prepaid is not None:
                quick_assets -= prepaid

            r = safe_div(quick_assets, cl)

            return f"""DETAILED SOLUTION — QUICK RATIO

Formula:
Quick Assets = Current Assets - Inventory - Prepaid Expenses

= {money(ca)} - {money(inv or 0)} - {money(prepaid or 0)}

= {money(quick_assets)}

Quick Ratio
= Quick Assets / Current Liabilities

= {money(quick_assets)} / {money(cl)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Quick Ratio = {format_decimal(r)} : 1
"""

    # Debt Equity
    if "debt equity" in n or "debt-equity" in n:
        debt = extract_labeled_number(
            text,
            ["long term debt", "long-term debt", "debt"]
        )
        equity = extract_labeled_number(
            text,
            ["shareholders funds", "shareholders' funds", "equity"]
        )

        if debt is not None and equity is not None:
            r = safe_div(debt, equity)

            return f"""DETAILED SOLUTION — DEBT EQUITY RATIO

Formula:
Debt Equity Ratio = Long-term Debt / Shareholders' Funds

= {money(debt)} / {money(equity)}

= {format_decimal(r)} : 1

FINAL ANSWER:
Debt Equity Ratio = {format_decimal(r)} : 1
"""

    # Gross Profit Ratio
    if "gross profit ratio" in n:
        gp = extract_labeled_number(text, ["gross profit"])
        sales = extract_labeled_number(text, ["revenue from operations", "sales"])

        if gp is not None and sales is not None:
            r = safe_div(gp * 100, sales)

            return f"""DETAILED SOLUTION — GROSS PROFIT RATIO

Formula:
Gross Profit Ratio = Gross Profit / Revenue from Operations × 100

= {money(gp)} / {money(sales)} × 100

= {percentage(r)}

FINAL ANSWER:
Gross Profit Ratio = {percentage(r)}
"""

    # Net Profit Ratio
    if "net profit ratio" in n:
        np = extract_labeled_number(text, ["net profit"])
        sales = extract_labeled_number(text, ["revenue from operations", "sales"])

        if np is not None and sales is not None:
            r = safe_div(np * 100, sales)

            return f"""DETAILED SOLUTION — NET PROFIT RATIO

Formula:
Net Profit Ratio = Net Profit / Revenue from Operations × 100

= {money(np)} / {money(sales)} × 100

= {percentage(r)}

FINAL ANSWER:
Net Profit Ratio = {percentage(r)}
"""

    return None


# =========================================================
# SHARE CAPITAL
# =========================================================

def solve_share(text):
    n = normalize(text)

    if not any(x in n for x in [
        "share capital",
        "shares issued",
        "shares allotted",
        "oversubscription",
        "forfeiture",
        "reissue"
    ]):
        return None

    # Oversubscription
    if "oversubscription" in n or "oversubscribed" in n:
        applied = extract_labeled_number(
            text,
            ["applied for", "applications for", "shares applied"]
        )

        issued = extract_labeled_number(
            text,
            ["issued", "shares issued", "offered"]
        )

        if applied is not None and issued is not None:
            excess = applied - issued

            return f"""DETAILED SOLUTION — OVERSUBSCRIPTION

Shares applied for = {format_number(applied)}
Shares issued/allotted = {format_number(issued)}

Excess applications
= Shares Applied - Shares Issued

= {format_number(applied)} - {format_number(issued)}

= {format_number(excess)} shares

FINAL ANSWER:
Excess applications = {format_number(excess)} shares
"""

    # Simple issue at premium
    if "premium" in n and "share" in n:
        face = extract_labeled_number(
            text,
            ["face value", "nominal value"]
        )
        premium = extract_labeled_number(
            text,
            ["premium"]
        )
        shares = extract_labeled_number(
            text,
            ["shares", "number of shares"]
        )

        if face is not None and premium is not None and shares is not None:
            total_face = face * shares
            total_premium = premium * shares
            total = total_face + total_premium

            return f"""DETAILED SOLUTION — ISSUE OF SHARES AT PREMIUM

Given:
Number of Shares = {format_number(shares)}
Face Value per Share = {money(face)}
Premium per Share = {money(premium)}

Step 1: Share Capital

= {format_number(shares)} × {money(face)}

= {money(total_face)}

Step 2: Securities Premium

= {format_number(shares)} × {money(premium)}

= {money(total_premium)}

Step 3: Total Amount

= {money(total_face)} + {money(total_premium)}

= {money(total)}

FINAL ANSWER:
Share Capital = {money(total_face)}
Securities Premium = {money(total_premium)}
Total = {money(total)}
"""

    return None


# =========================================================
# DEBENTURES
# =========================================================

def solve_debenture(text):
    n = normalize(text)

    if "debenture" not in n:
        return None

    number = extract_labeled_number(
        text,
        ["debentures", "number of debentures"]
    )

    face = extract_labeled_number(
        text,
        ["face value", "nominal value"]
    )

    rate = extract_labeled_number(
        text,
        ["rate of interest", "interest rate"]
    )

    if number is not None and face is not None and rate is not None:
        total = number * face
        interest = total * rate / 100

        return f"""DETAILED SOLUTION — DEBENTURES

Given:
Number of Debentures = {format_number(number)}
Face Value = {money(face)}
Rate of Interest = {format_number(rate)}%

Step 1: Total Debenture Value

= Number of Debentures × Face Value

= {format_number(number)} × {money(face)}

= {money(total)}

Step 2: Annual Interest

Formula:
Interest = Debenture Value × Rate / 100

= {money(total)} × {format_number(rate)} / 100

= {money(interest)}

FINAL ANSWER:
Total Debenture Value = {money(total)}
Annual Interest = {money(interest)}
"""

    return None


# =========================================================
# CASH FLOW
# =========================================================

def solve_cash_flow(text):
    n = normalize(text)

    if "cash flow" not in n:
        return None

    profit = extract_labeled_number(
        text,
        ["net profit", "profit before tax", "profit"]
    )

    depreciation = extract_labeled_number(
        text,
        ["depreciation"]
    )

    gain = extract_labeled_number(
        text,
        ["profit on sale", "gain on sale"]
    )

    loss = extract_labeled_number(
        text,
        ["loss on sale"]
    )

    if profit is None:
        return None

    operating = profit

    if depreciation is not None:
        operating += depreciation

    if gain is not None:
        operating -= gain

    if loss is not None:
        operating += loss

    return f"""DETAILED SOLUTION — CASH FLOW FROM OPERATING ACTIVITIES

Starting point:
Net Profit / Profit before Tax = {money(profit)}

Add: Depreciation = {money(depreciation or 0)}
Less: Profit on Sale of Asset = {money(gain or 0)}
Add: Loss on Sale of Asset = {money(loss or 0)}

Calculation:

Cash from Operating Activities before working-capital adjustments

= {money(profit)}
+ {money(depreciation or 0)}
- {money(gain or 0)}
+ {money(loss or 0)}

= {money(operating)}

FINAL ANSWER:
Cash Flow from Operating Activities before working-capital adjustments
= {money(operating)}

Note:
This is the indirect-method adjustment section. Working-capital changes,
tax and other required adjustments must be added separately when given.
"""


# =========================================================
# BASIC MATH
# =========================================================

def solve_basic_math(text):
    original = str(text)

    # Only attempt if it looks like a calculation
    if not re.search(r"\d\s*[\+\-\*\/×÷]\s*\d", original):
        return None

    cleaned = original.replace("×", "*").replace("÷", "/")
    cleaned = cleaned.replace(",", "")

    m = re.search(
        r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)\s*([\+\-\*/])\s*(-?\d+(?:\.\d+)?)",
        cleaned
    )

    if not m:
        return None

    a = float(m.group(1))
    operator = m.group(2)
    b = float(m.group(3))

    expression = f"{a}{operator}{b}"
    answer = safe_math(expression)

    if answer is None:
        return None

    return f"""DETAILED CALCULATION

Given:
{m.group(0)}

Working:
{m.group(0)} = {format_number(answer)}

FINAL ANSWER:
{format_number(answer)}
"""


# =========================================================
# LOCAL SOLVER DISPATCHER
# =========================================================

def local_solve(question):
    text = str(question)

    # Most specific first
    solvers = [
        solve_admission,
        solve_revaluation,
        solve_goodwill_average,
        solve_goodwill_super,
        solve_goodwill_capitalisation,
        solve_super_profit,
        solve_ratio,
        solve_share,
        solve_debenture,
        solve_cash_flow,
        solve_basic_math,
    ]

    for solver in solvers:
        try:
            answer = solver(text)
            if answer:
                return answer
        except Exception:
            continue

    return None


# =========================================================
# OPENAI FALLBACK
# =========================================================

def ai_solve(question, image=None):
    try:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            return {
                "answer": (
                    "AI backend is not configured. "
                    "Please set OPENAI_API_KEY in Vercel Environment Variables."
                )
            }

        client = OpenAI(api_key=api_key)

        prompt = """You are Commerce AI, an expert CBSE Class 12 Accountancy and Economics teacher.

Solve the student's question accurately.

IMPORTANT:
1. Give a detailed teacher-style solution.
2. Start with GIVEN.
3. Write the correct FORMULA.
4. Substitute the numbers.
5. Show calculations step-by-step.
6. Explain important reasoning.
7. Give FINAL ANSWER clearly.
8. For partnership questions, show ratios/fractions clearly.
9. For admission/retirement/death questions, calculate old ratio, new ratio, sacrificing/gaining ratio and goodwill treatment.
10. For journal-entry questions, provide proper journal entries with Dr., Cr. and narration.
11. For revaluation questions, prepare the required calculation clearly.
12. For ratios, show numerator, denominator and formula.
13. For cash flow, use the indirect method where applicable.
14. Do not invent missing figures. If information is missing, clearly say what is missing.
15. Use Indian accounting terminology and ₹.

Return a clean, readable answer suitable for a Class 12 student."""

        content = [
            {
                "type": "input_text",
                "text": prompt + "\n\nSTUDENT QUESTION:\n" + str(question)
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

        return {
            "answer": response.output_text
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# =========================================================
# HTTP HANDLER FOR VERCEL
# =========================================================

class Handler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({"ok": True})

    def do_GET(self):
        self._send_json({
            "ok": True,
            "message": "Commerce AI backend is running."
        })

    def do_POST(self):
        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw = self.rfile.read(content_length)

            data = json.loads(
                raw.decode("utf-8")
            )

            question = data.get("question", "")
            image = data.get("image")

            if not question and not image:
                self._send_json(
                    {
                        "error": "Please provide a question or image."
                    },
                    400
                )
                return

            # -------------------------------------------------
            # 1. Try local detailed engine first
            # -------------------------------------------------

            local_answer = None

            if question:
                local_answer = local_solve(question)

            if local_answer:
                self._send_json({
                    "answer": local_answer,
                    "source": "local_detailed_solver"
                })
                return

            # -------------------------------------------------
            # 2. AI fallback
            # -------------------------------------------------

            ai_result = ai_solve(
                question,
                image
            )

            if "error" in ai_result:
                error_text = str(ai_result["error"])

                # Friendly credit error
                if (
                    "credit" in error_text.lower()
                    or "quota" in error_text.lower()
                    or "429" in error_text
                ):
                    self._send_json({
                        "error": (
                            "AI credits are currently exhausted. "
                            "The built-in Accountancy solver can still "
                            "solve supported questions."
                        )
                    }, 429)
                    return

                self._send_json(
                    ai_result,
                    500
                )
                return

            self._send_json({
                "answer": ai_result.get("answer", ""),
                "source": "openai"
            })

        except json.JSONDecodeError:
            self._send_json({
                "error": "Invalid JSON request."
            }, 400)

        except Exception as e:
            self._send_json({
                "error": str(e)
            }, 500)


handler = Handler
