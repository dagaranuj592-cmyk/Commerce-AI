# Commerce AI - Calculator Engine
# Handles common Accountancy calculations without AI API


def calculate(data):
    """
    data example:
    {
        "type": "super_profit",
        "average_profit": 200000,
        "capital_employed": 1500000,
        "normal_rate": 10,
        "years_purchase": 3
    }
    """

    calculation_type = data.get("type", "").lower().strip()

    # -------------------------
    # GOODWILL
    # -------------------------

    if calculation_type == "average_profit":

        profits = data.get("profits", [])

        if not profits:
            return error("Profits are required.")

        total = sum(profits)
        average = total / len(profits)

        return success(
            "Average Profit",
            [
                f"Total Profit = ₹{format_number(total)}",
                f"Number of Years = {len(profits)}",
                "Average Profit = Total Profit ÷ Number of Years",
                f"Average Profit = ₹{format_number(total)} ÷ {len(profits)}",
                f"Average Profit = ₹{format_number(average)}"
            ],
            average
        )

    if calculation_type == "goodwill_average_profit":

        average_profit = data.get("average_profit")
        years = data.get("years_purchase")

        if average_profit is None or years is None:
            return error(
                "Average profit and years purchase are required."
            )

        goodwill = average_profit * years

        return success(
            "Goodwill - Average Profit Method",
            [
                "Goodwill = Average Profit × Years' Purchase",
                f"Goodwill = ₹{format_number(average_profit)} × {years}",
                f"Goodwill = ₹{format_number(goodwill)}"
            ],
            goodwill
        )

    if calculation_type == "normal_profit":

        capital = data.get("capital_employed")
        rate = data.get("normal_rate")

        if capital is None or rate is None:
            return error(
                "Capital employed and normal rate are required."
            )

        normal_profit = capital * rate / 100

        return success(
            "Normal Profit",
            [
                "Normal Profit = Capital Employed × Normal Rate / 100",
                f"Normal Profit = ₹{format_number(capital)} × {rate} / 100",
                f"Normal Profit = ₹{format_number(normal_profit)}"
            ],
            normal_profit
        )

    if calculation_type == "super_profit":

        average_profit = data.get("average_profit")
        capital = data.get("capital_employed")
        rate = data.get("normal_rate")

        if (
            average_profit is None
            or capital is None
            or rate is None
        ):
            return error(
                "Average profit, capital employed and normal rate are required."
            )

        normal_profit = capital * rate / 100
        super_profit = average_profit - normal_profit

        return success(
            "Super Profit",
            [
                f"Average Profit = ₹{format_number(average_profit)}",
                f"Capital Employed = ₹{format_number(capital)}",
                f"Normal Rate = {rate}%",
                "",
                "Normal Profit = Capital Employed × Rate / 100",
                f"Normal Profit = ₹{format_number(normal_profit)}",
                "",
                "Super Profit = Average Profit − Normal Profit",
                f"Super Profit = ₹{format_number(average_profit)} − ₹{format_number(normal_profit)}",
                f"Super Profit = ₹{format_number(super_profit)}"
            ],
            super_profit
        )

    if calculation_type == "goodwill_super_profit":

        average_profit = data.get("average_profit")
        capital = data.get("capital_employed")
        rate = data.get("normal_rate")
        years = data.get("years_purchase")

        if (
            average_profit is None
            or capital is None
            or rate is None
            or years is None
        ):
            return error(
                "All Super Profit Method values are required."
            )

        normal_profit = capital * rate / 100
        super_profit = average_profit - normal_profit
        goodwill = super_profit * years

        return success(
            "Goodwill - Super Profit Method",
            [
                f"Average Profit = ₹{format_number(average_profit)}",
                f"Normal Profit = ₹{format_number(normal_profit)}",
                f"Super Profit = ₹{format_number(super_profit)}",
                "",
                "Goodwill = Super Profit × Years' Purchase",
                f"Goodwill = ₹{format_number(super_profit)} × {years}",
                f"Goodwill = ₹{format_number(goodwill)}"
            ],
            goodwill
        )

    if calculation_type == "capitalised_average_profit":

        average_profit = data.get("average_profit")
        rate = data.get("normal_rate")
        actual_capital = data.get("actual_capital_employed")

        if (
            average_profit is None
            or rate is None
            or actual_capital is None
        ):
            return error(
                "Average profit, rate and actual capital employed are required."
            )

        capitalised_value = average_profit * 100 / rate
        goodwill = capitalised_value - actual_capital

        return success(
            "Goodwill - Capitalisation of Average Profit",
            [
                "Capitalised Value = Average Profit × 100 / Normal Rate",
                f"Capitalised Value = ₹{format_number(capitalised_value)}",
                "",
                "Goodwill = Capitalised Value − Actual Capital Employed",
                f"Goodwill = ₹{format_number(goodwill)}"
            ],
            goodwill
        )

    # -------------------------
    # RATIOS
    # -------------------------

    if calculation_type == "current_ratio":

        current_assets = data.get("current_assets")
        current_liabilities = data.get("current_liabilities")

        if current_assets is None or current_liabilities is None:
            return error(
                "Current assets and current liabilities are required."
            )

        if current_liabilities == 0:
            return error(
                "Current liabilities cannot be zero."
            )

        ratio = current_assets / current_liabilities

        return success(
            "Current Ratio",
            [
                "Current Ratio = Current Assets ÷ Current Liabilities",
                f"Current Ratio = ₹{format_number(current_assets)} ÷ ₹{format_number(current_liabilities)}",
                f"Current Ratio = {format_ratio(ratio)} : 1"
            ],
            ratio
        )

    if calculation_type == "quick_ratio":

        quick_assets = data.get("quick_assets")
        current_liabilities = data.get("current_liabilities")

        if quick_assets is None or current_liabilities is None:
            return error(
                "Quick assets and current liabilities are required."
            )

        if current_liabilities == 0:
            return error(
                "Current liabilities cannot be zero."
            )

        ratio = quick_assets / current_liabilities

        return success(
            "Quick Ratio",
            [
                "Quick Ratio = Quick Assets ÷ Current Liabilities",
                f"Quick Ratio = ₹{format_number(quick_assets)} ÷ ₹{format_number(current_liabilities)}",
                f"Quick Ratio = {format_ratio(ratio)} : 1"
            ],
            ratio
        )

    if calculation_type == "debt_equity_ratio":

        debt = data.get("long_term_debt")
        equity = data.get("shareholders_funds")

        if debt is None or equity is None:
            return error(
                "Long-term debt and shareholders' funds are required."
            )

        if equity == 0:
            return error(
                "Shareholders' funds cannot be zero."
            )

        ratio = debt / equity

        return success(
            "Debt-Equity Ratio",
            [
                "Debt-Equity Ratio = Long-term Debt ÷ Shareholders' Funds",
                f"Debt-Equity Ratio = ₹{format_number(debt)} ÷ ₹{format_number(equity)}",
                f"Debt-Equity Ratio = {format_ratio(ratio)} : 1"
            ],
            ratio
        )

    # -------------------------
    # PROFITABILITY RATIOS
    # -------------------------

    if calculation_type == "gross_profit_ratio":

        gross_profit = data.get("gross_profit")
        revenue = data.get("revenue")

        if gross_profit is None or revenue is None:
            return error(
                "Gross profit and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = gross_profit / revenue * 100

        return success(
            "Gross Profit Ratio",
            [
                "Gross Profit Ratio = Gross Profit ÷ Revenue × 100",
                f"Gross Profit Ratio = ₹{format_number(gross_profit)} ÷ ₹{format_number(revenue)} × 100",
                f"Gross Profit Ratio = {format_number(ratio)}%"
            ],
            ratio
        )

    if calculation_type == "net_profit_ratio":

        net_profit = data.get("net_profit")
        revenue = data.get("revenue")

        if net_profit is None or revenue is None:
            return error(
                "Net profit and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = net_profit / revenue * 100

        return success(
            "Net Profit Ratio",
            [
                "Net Profit Ratio = Net Profit ÷ Revenue × 100",
                f"Net Profit Ratio = ₹{format_number(net_profit)} ÷ ₹{format_number(revenue)} × 100",
                f"Net Profit Ratio = {format_number(ratio)}%"
            ],
            ratio
        )

    # -------------------------
    # ROI
    # -------------------------

    if calculation_type == "roi":

        operating_profit = data.get("operating_profit")
        capital_employed = data.get("capital_employed")

        if operating_profit is None or capital_employed is None:
            return error(
                "Operating profit and capital employed are required."
            )

        if capital_employed == 0:
            return error(
                "Capital employed cannot be zero."
            )

        roi = operating_profit / capital_employed * 100

        return success(
            "Return on Investment",
            [
                "ROI = Operating Profit ÷ Capital Employed × 100",
                f"ROI = ₹{format_number(operating_profit)} ÷ ₹{format_number(capital_employed)} × 100",
                f"ROI = {format_number(roi)}%"
            ],
            roi
        )

    # -------------------------
    # INTEREST
    # -------------------------

    if calculation_type == "interest_on_capital":

        capital = data.get("capital")
        rate = data.get("rate")
        time = data.get("time", 1)

        if capital is None or rate is None:
            return error(
                "Capital and rate are required."
            )

        interest = capital * rate * time / 100

        return success(
            "Interest on Capital",
            [
                "Interest = Capital × Rate × Time / 100",
                f"Interest = ₹{format_number(capital)} × {rate} × {time} / 100",
                f"Interest = ₹{format_number(interest)}"
            ],
            interest
        )

    if calculation_type == "interest_on_drawings":

        drawings = data.get("drawings")
        rate = data.get("rate")
        time = data.get("time", 1)

        if drawings is None or rate is None:
            return error(
                "Drawings and rate are required."
            )

        interest = drawings * rate * time / 100

        return success(
            "Interest on Drawings",
            [
                "Interest = Drawings × Rate × Time / 100",
                f"Interest = ₹{format_number(drawings)} × {rate} × {time} / 100",
                f"Interest = ₹{format_number(interest)}"
            ],
            interest
        )

    # -------------------------
    # UNKNOWN
    # -------------------------

    return None


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def format_number(number):

    if isinstance(number, float):

        if number.is_integer():
            number = int(number)

    return f"{number:,}"


def format_ratio(number):

    return f"{number:.2f}".rstrip("0").rstrip(".")


def success(title, steps, value):

    return {
        "success": True,
        "title": title,
        "steps": steps,
        "value": value
    }


def error(message):

    return {
        "success": False,
        "error": message
      }
