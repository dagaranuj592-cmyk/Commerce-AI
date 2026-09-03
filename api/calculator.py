# Commerce AI - Advanced Calculator Engine
# Local calculations - No AI API required


# =========================================================
# MAIN CALCULATOR
# =========================================================

def calculate(data):

    calculation_type = (
        data.get("type", "")
        .lower()
        .strip()
    )


    # =====================================================
    # GOODWILL - AVERAGE PROFIT
    # =====================================================

    if calculation_type == "average_profit":

        profits = data.get("profits", [])

        if not profits:
            return error("Profits are required.")

        total = sum(profits)
        average = total / len(profits)

        return success(
            "Average Profit",
            [
                "Total Profit = "
                + " + ".join(
                    "₹" + format_number(x)
                    for x in profits
                ),

                "Total Profit = ₹"
                + format_number(total),

                "Average Profit = "
                "Total Profit ÷ Number of Years",

                "Average Profit = ₹"
                + format_number(total)
                + " ÷ "
                + str(len(profits)),

                "Average Profit = ₹"
                + format_number(average)
            ],
            average
        )


    # =====================================================
    # GOODWILL - AVERAGE PROFIT METHOD
    # =====================================================

    if calculation_type == "goodwill_average_profit":

        average_profit = data.get(
            "average_profit"
        )

        years = data.get(
            "years_purchase"
        )

        if (
            average_profit is None
            or years is None
        ):
            return error(
                "Average profit and years purchase are required."
            )

        goodwill = (
            average_profit * years
        )

        return success(
            "Goodwill - Average Profit Method",
            [
                "Goodwill = Average Profit × Years' Purchase",

                "Goodwill = ₹"
                + format_number(average_profit)
                + " × "
                + format_number(years),

                "Goodwill = ₹"
                + format_number(goodwill)
            ],
            goodwill
        )


    # =====================================================
    # NORMAL PROFIT
    # =====================================================

    if calculation_type == "normal_profit":

        capital = data.get(
            "capital_employed"
        )

        rate = data.get(
            "normal_rate"
        )

        if (
            capital is None
            or rate is None
        ):
            return error(
                "Capital employed and normal rate are required."
            )

        normal_profit = (
            capital * rate / 100
        )

        return success(
            "Normal Profit",
            [
                "Normal Profit = "
                "Capital Employed × Normal Rate / 100",

                "Normal Profit = ₹"
                + format_number(capital)
                + " × "
                + format_number(rate)
                + " / 100",

                "Normal Profit = ₹"
                + format_number(normal_profit)
            ],
            normal_profit
        )


    # =====================================================
    # SUPER PROFIT
    # =====================================================

    if calculation_type == "super_profit":

        average_profit = data.get(
            "average_profit"
        )

        capital = data.get(
            "capital_employed"
        )

        rate = data.get(
            "normal_rate"
        )

        if (
            average_profit is None
            or capital is None
            or rate is None
        ):
            return error(
                "Average profit, capital employed and normal rate are required."
            )

        normal_profit = (
            capital * rate / 100
        )

        super_profit = (
            average_profit
            - normal_profit
        )

        return success(
            "Super Profit",
            [
                "Average Profit = ₹"
                + format_number(average_profit),

                "Normal Profit = "
                "Capital Employed × Rate / 100",

                "Normal Profit = ₹"
                + format_number(normal_profit),

                "Super Profit = "
                "Average Profit − Normal Profit",

                "Super Profit = ₹"
                + format_number(average_profit)
                + " − ₹"
                + format_number(normal_profit),

                "Super Profit = ₹"
                + format_number(super_profit)
            ],
            super_profit
        )


    # =====================================================
    # GOODWILL - SUPER PROFIT
    # =====================================================

    if calculation_type == "goodwill_super_profit":

        average_profit = data.get(
            "average_profit"
        )

        capital = data.get(
            "capital_employed"
        )

        rate = data.get(
            "normal_rate"
        )

        years = data.get(
            "years_purchase"
        )

        if (
            average_profit is None
            or capital is None
            or rate is None
            or years is None
        ):
            return error(
                "All Super Profit Method values are required."
            )

        normal_profit = (
            capital * rate / 100
        )

        super_profit = (
            average_profit
            - normal_profit
        )

        goodwill = (
            super_profit * years
        )

        return success(
            "Goodwill - Super Profit Method",
            [
                "Average Profit = ₹"
                + format_number(average_profit),

                "Normal Profit = ₹"
                + format_number(normal_profit),

                "Super Profit = "
                "Average Profit − Normal Profit",

                "Super Profit = ₹"
                + format_number(super_profit),

                "Goodwill = "
                "Super Profit × Years' Purchase",

                "Goodwill = ₹"
                + format_number(super_profit)
                + " × "
                + format_number(years),

                "Goodwill = ₹"
                + format_number(goodwill)
            ],
            goodwill
        )


    # =====================================================
    # GOODWILL - CAPITALISATION OF AVERAGE PROFIT
    # =====================================================

    if calculation_type == "capitalised_average_profit":

        average_profit = data.get(
            "average_profit"
        )

        rate = data.get(
            "normal_rate"
        )

        actual_capital = data.get(
            "actual_capital_employed"
        )

        if (
            average_profit is None
            or rate is None
            or actual_capital is None
        ):
            return error(
                "Average profit, rate and actual capital employed are required."
            )

        capitalised_value = (
            average_profit * 100 / rate
        )

        goodwill = (
            capitalised_value
            - actual_capital
        )

        return success(
            "Goodwill - Capitalisation Method",
            [
                "Capitalised Value = "
                "Average Profit × 100 / Normal Rate",

                "Capitalised Value = ₹"
                + format_number(
                    capitalised_value
                ),

                "Goodwill = "
                "Capitalised Value − Actual Capital",

                "Goodwill = ₹"
                + format_number(goodwill)
            ],
            goodwill
        )


    # =====================================================
    # HIDDEN GOODWILL
    # =====================================================

    if calculation_type == "hidden_goodwill":

        capital_brought = data.get(
            "capital_brought"
        )

        share = data.get(
            "share"
        )

        if (
            capital_brought is None
            or share is None
        ):
            return error(
                "Capital brought and profit-sharing share are required."
            )

        if share == 0:
            return error(
                "Share cannot be zero."
            )

        total_capital = (
            capital_brought / share
        )

        hidden_goodwill = (
            total_capital
            - capital_brought
        )

        return success(
            "Hidden Goodwill",
            [
                "Total Capital = "
                "Capital Brought ÷ New Partner's Share",

                "Total Capital = ₹"
                + format_number(
                    total_capital
                ),

                "Hidden Goodwill = "
                "Total Capital − Capital Brought",

                "Hidden Goodwill = ₹"
                + format_number(
                    hidden_goodwill
                )
            ],
            hidden_goodwill
        )


    # =====================================================
    # SACRIFICING RATIO
    # =====================================================

    if calculation_type == "sacrificing_ratio":

        old_a = data.get("old_a")
        old_b = data.get("old_b")

        new_a = data.get("new_a")
        new_b = data.get("new_b")

        if None in (
            old_a,
            old_b,
            new_a,
            new_b
        ):
            return error(
                "Old and new ratios are required."
            )

        sacrifice_a = old_a - new_a
        sacrifice_b = old_b - new_b

        return success(
            "Sacrificing Ratio",
            [
                "A's Sacrifice = Old Share − New Share",

                "A's Sacrifice = "
                + format_fraction(sacrifice_a),

                "B's Sacrifice = Old Share − New Share",

                "B's Sacrifice = "
                + format_fraction(sacrifice_b),

                "Sacrificing Ratio = "
                + ratio_text(
                    sacrifice_a,
                    sacrifice_b
                )
            ],
            None
        )


    # =====================================================
    # GAINING RATIO
    # =====================================================

    if calculation_type == "gaining_ratio":

        old_a = data.get("old_a")
        old_b = data.get("old_b")

        new_a = data.get("new_a")
        new_b = data.get("new_b")

        if None in (
            old_a,
            old_b,
            new_a,
            new_b
        ):
            return error(
                "Old and new ratios are required."
            )

        gain_a = new_a - old_a
        gain_b = new_b - old_b

        return success(
            "Gaining Ratio",
            [
                "A's Gain = New Share − Old Share",

                "A's Gain = "
                + format_fraction(gain_a),

                "B's Gain = New Share − Old Share",

                "B's Gain = "
                + format_fraction(gain_b),

                "Gaining Ratio = "
                + ratio_text(
                    gain_a,
                    gain_b
                )
            ],
            None
        )


    # =====================================================
    # INTEREST ON CAPITAL
    # =====================================================

    if calculation_type == "interest_on_capital":

        capital = data.get("capital")
        rate = data.get("rate")
        time = data.get("time", 1)

        if capital is None or rate is None:
            return error(
                "Capital and rate are required."
            )

        interest = (
            capital * rate * time / 100
        )

        return success(
            "Interest on Capital",
            [
                "Interest = Capital × Rate × Time / 100",

                "Interest = ₹"
                + format_number(capital)
                + " × "
                + format_number(rate)
                + " × "
                + format_number(time)
                + " / 100",

                "Interest = ₹"
                + format_number(interest)
            ],
            interest
        )


    # =====================================================
    # INTEREST ON DRAWINGS
    # =====================================================

    if calculation_type == "interest_on_drawings":

        drawings = data.get("drawings")
        rate = data.get("rate")
        time = data.get("time", 1)

        if drawings is None or rate is None:
            return error(
                "Drawings and rate are required."
            )

        interest = (
            drawings * rate * time / 100
        )

        return success(
            "Interest on Drawings",
            [
                "Interest = Drawings × Rate × Time / 100",

                "Interest = ₹"
                + format_number(drawings)
                + " × "
                + format_number(rate)
                + " × "
                + format_number(time)
                + " / 100",

                "Interest = ₹"
                + format_number(interest)
            ],
            interest
        )


    # =====================================================
    # PARTNER SALARY
    # =====================================================

    if calculation_type == "partner_salary":

        profit = data.get("profit")
        salary = data.get("salary")

        if profit is None or salary is None:
            return error(
                "Profit and salary are required."
            )

        remaining = profit - salary

        return success(
            "Partner Salary",
            [
                "Profit Before Salary = ₹"
                + format_number(profit),

                "Partner Salary = ₹"
                + format_number(salary),

                "Profit After Salary = "
                "Profit − Salary",

                "Profit After Salary = ₹"
                + format_number(remaining)
            ],
            remaining
        )


    # =====================================================
    # CURRENT RATIO
    # =====================================================

    if calculation_type == "current_ratio":

        assets = data.get(
            "current_assets"
        )

        liabilities = data.get(
            "current_liabilities"
        )

        if assets is None or liabilities is None:
            return error(
                "Current assets and current liabilities are required."
            )

        if liabilities == 0:
            return error(
                "Current liabilities cannot be zero."
            )

        ratio = (
            assets / liabilities
        )

        return success(
            "Current Ratio",
            [
                "Current Ratio = "
                "Current Assets ÷ Current Liabilities",

                "Current Ratio = ₹"
                + format_number(assets)
                + " ÷ ₹"
                + format_number(liabilities),

                "Current Ratio = "
                + format_ratio(ratio)
                + " : 1"
            ],
            ratio
        )


    # =====================================================
    # QUICK RATIO
    # =====================================================

    if calculation_type == "quick_ratio":

        assets = data.get(
            "quick_assets"
        )

        liabilities = data.get(
            "current_liabilities"
        )

        if assets is None or liabilities is None:
            return error(
                "Quick assets and current liabilities are required."
            )

        if liabilities == 0:
            return error(
                "Current liabilities cannot be zero."
            )

        ratio = assets / liabilities

        return success(
            "Quick Ratio",
            [
                "Quick Ratio = "
                "Quick Assets ÷ Current Liabilities",

                "Quick Ratio = "
                + format_ratio(ratio)
                + " : 1"
            ],
            ratio
        )


    # =====================================================
    # DEBT EQUITY RATIO
    # =====================================================

    if calculation_type == "debt_equity_ratio":

        debt = data.get(
            "long_term_debt"
        )

        equity = data.get(
            "shareholders_funds"
        )

        if debt is None or equity is None:
            return error(
                "Debt and shareholders' funds are required."
            )

        if equity == 0:
            return error(
                "Shareholders' funds cannot be zero."
            )

        ratio = debt / equity

        return success(
            "Debt-Equity Ratio",
            [
                "Debt-Equity Ratio = "
                "Long-term Debt ÷ Shareholders' Funds",

                "Debt-Equity Ratio = "
                + format_ratio(ratio)
                + " : 1"
            ],
            ratio
        )


    # =====================================================
    # GROSS PROFIT RATIO
    # =====================================================

    if calculation_type == "gross_profit_ratio":

        profit = data.get(
            "gross_profit"
        )

        revenue = data.get(
            "revenue"
        )

        if profit is None or revenue is None:
            return error(
                "Gross profit and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = (
            profit / revenue * 100
        )

        return success(
            "Gross Profit Ratio",
            [
                "Gross Profit Ratio = "
                "Gross Profit ÷ Revenue × 100",

                "Gross Profit Ratio = "
                + format_number(ratio)
                + "%"
            ],
            ratio
        )


    # =====================================================
    # NET PROFIT RATIO
    # =====================================================

    if calculation_type == "net_profit_ratio":

        profit = data.get(
            "net_profit"
        )

        revenue = data.get(
            "revenue"
        )

        if profit is None or revenue is None:
            return error(
                "Net profit and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = (
            profit / revenue * 100
        )

        return success(
            "Net Profit Ratio",
            [
                "Net Profit Ratio = "
                "Net Profit ÷ Revenue × 100",

                "Net Profit Ratio = "
                + format_number(ratio)
                + "%"
            ],
            ratio
        )


    # =====================================================
    # OPERATING RATIO
    # =====================================================

    if calculation_type == "operating_ratio":

        operating_cost = data.get(
            "operating_cost"
        )

        revenue = data.get(
            "revenue"
        )

        if (
            operating_cost is None
            or revenue is None
        ):
            return error(
                "Operating cost and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = (
            operating_cost
            / revenue
            * 100
        )

        return success(
            "Operating Ratio",
            [
                "Operating Ratio = "
                "Operating Cost ÷ Revenue × 100",

                "Operating Ratio = "
                + format_number(ratio)
                + "%"
            ],
            ratio
        )


    # =====================================================
    # OPERATING PROFIT RATIO
    # =====================================================

    if calculation_type == "operating_profit_ratio":

        operating_profit = data.get(
            "operating_profit"
        )

        revenue = data.get(
            "revenue"
        )

        if (
            operating_profit is None
            or revenue is None
        ):
            return error(
                "Operating profit and revenue are required."
            )

        if revenue == 0:
            return error(
                "Revenue cannot be zero."
            )

        ratio = (
            operating_profit
            / revenue
            * 100
        )

        return success(
            "Operating Profit Ratio",
            [
                "Operating Profit Ratio = "
                "Operating Profit ÷ Revenue × 100",

                "Operating Profit Ratio = "
                + format_number(ratio)
                + "%"
            ],
            ratio
        )


    # =====================================================
    # ROI
    # =====================================================

    if calculation_type == "roi":

        profit = data.get(
            "operating_profit"
        )

        capital = data.get(
            "capital_employed"
        )

        if profit is None or capital is None:
            return error(
                "Operating profit and capital employed are required."
            )

        if capital == 0:
            return error(
                "Capital employed cannot be zero."
            )

        roi = (
            profit / capital * 100
        )

        return success(
            "Return on Investment",
            [
                "ROI = "
                "Operating Profit ÷ Capital Employed × 100",

                "ROI = "
                + format_number(roi)
                + "%"
            ],
            roi
        )


    # =====================================================
    # DEPRECIATION - STRAIGHT LINE
    # =====================================================

    if calculation_type == "depreciation_straight_line":

        cost = data.get("cost")
        residual = data.get("residual_value", 0)
        life = data.get("useful_life")

        if cost is None or life is None:
            return error(
                "Cost and useful life are required."
            )

        if life == 0:
            return error(
                "Useful life cannot be zero."
            )

        depreciation = (
            cost - residual
        ) / life

        return success(
            "Depreciation - Straight Line Method",
            [
                "Depreciation = "
                "(Cost − Residual Value) ÷ Useful Life",

                "Depreciation = (₹"
                + format_number(cost)
                + " − ₹"
                + format_number(residual)
                + ") ÷ "
                + format_number(life),

                "Annual Depreciation = ₹"
                + format_number(depreciation)
            ],
            depreciation
        )


    # =====================================================
    # DEPRECIATION - WRITTEN DOWN VALUE
    # =====================================================

    if calculation_type == "depreciation_wdv":

        opening_value = data.get(
            "opening_value"
        )

        rate = data.get("rate")

        if (
            opening_value is None
            or rate is None
        ):
            return error(
                "Opening value and rate are required."
            )

        depreciation = (
            opening_value
            * rate
            / 100
        )

        closing_value = (
            opening_value
            - depreciation
        )

        return success(
            "Depreciation - Written Down Value",
            [
                "Depreciation = "
                "Opening Value × Rate / 100",

                "Depreciation = ₹"
                + format_number(
                    depreciation
                ),

                "Closing Value = "
                "Opening Value − Depreciation",

                "Closing Value = ₹"
                + format_number(
                    closing_value
                )
            ],
            depreciation
        )


    # =====================================================
    # CONTRIBUTION
    # =====================================================

    if calculation_type == "contribution":

        sales = data.get("sales")
        variable_cost = data.get(
            "variable_cost"
        )

        if (
            sales is None
            or variable_cost is None
        ):
            return error(
                "Sales and variable cost are required."
            )

        contribution = (
            sales - variable_cost
        )

        return success(
            "Contribution",
            [
                "Contribution = "
                "Sales − Variable Cost",

                "Contribution = ₹"
                + format_number(sales)
                + " − ₹"
                + format_number(variable_cost),

                "Contribution = ₹"
                + format_number(contribution)
            ],
            contribution
        )


    # =====================================================
    # P/V RATIO
    # =====================================================

    if calculation_type == "profit_volume_ratio":

        contribution = data.get(
            "contribution"
        )

        sales = data.get("sales")

        if (
            contribution is None
            or sales is None
        ):
            return error(
                "Contribution and sales are required."
            )

        if sales == 0:
            return error(
                "Sales cannot be zero."
            )

        ratio = (
            contribution / sales * 100
        )

        return success(
            "Profit Volume Ratio",
            [
                "P/V Ratio = "
                "Contribution ÷ Sales × 100",

                "P/V Ratio = "
                + format_number(ratio)
                + "%"
            ],
            ratio
        )


    # =====================================================
    # BREAK EVEN POINT
    # =====================================================

    if calculation_type == "break_even_point":

        fixed_cost = data.get(
            "fixed_cost"
        )

        pv_ratio = data.get(
            "pv_ratio"
        )

        if (
            fixed_cost is None
            or pv_ratio is None
        ):
            return error(
                "Fixed cost and P/V ratio are required."
            )

        if pv_ratio == 0:
            return error(
                "P/V ratio cannot be zero."
            )

        bep = (
            fixed_cost
            * 100
            / pv_ratio
        )

        return success(
            "Break-Even Point",
            [
                "BEP = Fixed Cost × 100 ÷ P/V Ratio",

                "BEP = ₹"
                + format_number(
                    bep
                )
            ],
            bep
        )


    # =====================================================
    # COST OF GOODS SOLD
    # =====================================================

    if calculation_type == "cost_of_goods_sold":

        opening_stock = data.get(
            "opening_stock",
            0
        )

        purchases = data.get(
            "purchases",
            0
        )

        direct_expenses = data.get(
            "direct_expenses",
            0
        )

        closing_stock = data.get(
            "closing_stock",
            0
        )

        cogs = (
            opening_stock
            + purchases
            + direct_expenses
            - closing_stock
        )

        return success(
            "Cost of Goods Sold",
            [
                "COGS = "
                "Opening Stock + Purchases "
                "+ Direct Expenses − Closing Stock",

                "COGS = ₹"
                + format_number(
                    cogs
                )
            ],
            cogs
        )


    # =====================================================
    # GROSS PROFIT FROM SALES
    # =====================================================

    if calculation_type == "gross_profit_from_sales":

        sales = data.get("sales")
        cogs = data.get(
            "cost_of_goods_sold"
        )

        if sales is None or cogs is None:
            return error(
                "Sales and COGS are required."
            )

        gross_profit = (
            sales - cogs
        )

        return success(
            "Gross Profit",
            [
                "Gross Profit = Sales − Cost of Goods Sold",

                "Gross Profit = ₹"
                + format_number(sales)
                + " − ₹"
                + format_number(cogs),

                "Gross Profit = ₹"
                + format_number(
                    gross_profit
                )
            ],
            gross_profit
        )


    # =====================================================
    # REVENUE
    # =====================================================

    if calculation_type == "revenue":

        price = data.get("price")
        quantity = data.get("quantity")

        if price is None or quantity is None:
            return error(
                "Price and quantity are required."
            )

        revenue = (
            price * quantity
        )

        return success(
            "Revenue",
            [
                "Revenue = Price × Quantity",

                "Revenue = ₹"
                + format_number(price)
                + " × "
                + format_number(quantity),

                "Revenue = ₹"
                + format_number(revenue)
            ],
            revenue
        )


    # =====================================================
    # MPC
    # =====================================================

    if calculation_type == "mpc":

        change_consumption = data.get(
            "change_consumption"
        )

        change_income = data.get(
            "change_income"
        )

        if (
            change_consumption is None
            or change_income is None
        ):
            return error(
                "Change in consumption and income are required."
            )

        if change_income == 0:
            return error(
                "Change in income cannot be zero."
            )

        mpc = (
            change_consumption
            / change_income
        )

        return success(
            "Marginal Propensity to Consume",
            [
                "MPC = ΔC ÷ ΔY",

                "MPC = "
                + format_ratio(mpc)
            ],
            mpc
        )


    # =====================================================
    # MPS
    # =====================================================

    if calculation_type == "mps":

        change_saving = data.get(
            "change_saving"
        )

        change_income = data.get(
            "change_income"
        )

        if (
            change_saving is None
            or change_income is None
        ):
            return error(
                "Change in saving and income are required."
            )

        if change_income == 0:
            return error(
                "Change in income cannot be zero."
            )

        mps = (
            change_saving
            / change_income
        )

        return success(
            "Marginal Propensity to Save",
            [
                "MPS = ΔS ÷ ΔY",

                "MPS = "
                + format_ratio(mps)
            ],
            mps
        )


    # =====================================================
    # MPC + MPS RELATION
    # =====================================================

    if calculation_type == "mpc_mps_relation":

        mpc = data.get("mpc")
        mps = data.get("mps")

        if mpc is None and mps is None:
            return error(
                "MPC or MPS is required."
            )

        if mpc is not None:

            result = 1 - mpc

            return success(
                "MPC-MPS Relationship",
                [
                    "MPC + MPS = 1",

                    "MPS = 1 − MPC",

                    "MPS = "
                    + format_ratio(result)
                ],
                result
            )

        result = 1 - mps

        return success(
            "MPC-MPS Relationship",
            [
                "MPC + MPS = 1",

                "MPC = 1 − MPS",

                "MPC = "
                + format_ratio(result)
            ],
            result
        )


    # =====================================================
    # MULTIPLIER
    # =====================================================

    if calculation_type == "multiplier":

        mpc = data.get("mpc")

        if mpc is None:
            return error(
                "MPC is required."
            )

        if mpc >= 1:
            return error(
                "MPC must be less than 1."
            )

        multiplier = (
            1 / (1 - mpc)
        )

        return success(
            "Investment Multiplier",
            [
                "K = 1 ÷ (1 − MPC)",

                "K = "
                + format_ratio(multiplier)
            ],
            multiplier
        )


    # =====================================================
    # MONEY MULTIPLIER
    # =====================================================

    if calculation_type == "money_multiplier":

        reserve_ratio = data.get(
            "reserve_ratio"
        )

        if reserve_ratio is None:
            return error(
                "Reserve ratio is required."
            )

        if reserve_ratio == 0:
            return error(
                "Reserve ratio cannot be zero."
            )

        multiplier = (
            1 / reserve_ratio
        )

        return success(
            "Money Multiplier",
            [
                "Money Multiplier = 1 ÷ Reserve Ratio",

                "Money Multiplier = "
                + format_ratio(multiplier)
            ],
            multiplier
        )


    # =====================================================
    # UNKNOWN
    # =====================================================

    return None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_number(number):

    if isinstance(number, float):

        if number.is_integer():
            number = int(number)

    return f"{number:,}"


def format_ratio(number):

    return (
        f"{number:.2f}"
        .rstrip("0")
        .rstrip(".")
    )


def format_fraction(number):

    if number is None:
        return "0"

    return f"{number:.4f}".rstrip("0").rstrip(".")


def ratio_text(a, b):

    if a == 0 and b == 0:
        return "0 : 0"

    if a == 0:
        return "0 : 1"

    if b == 0:
        return "1 : 0"

    # Convert fractions to a simple ratio
    import math

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
        str(a_int // divisor)
        + " : "
        + str(b_int // divisor)
    )


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
