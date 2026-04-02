import sys
import os
import math
from datetime import datetime
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.columns import Columns
    from rich.style import Style
except ImportError:
    print("Error: 'rich' library required. Install with: pip install rich")
    sys.exit(1)

console = Console()
notation = "Rp "
PAGE_SIZE = 10


def show_help():
    text = """
[1] CORE MONEY FLOW

Total Spent
  This is the total money that left your pocket.
  If this number is high, you are consuming a lot.

Total Earned
  This is the total money that came in.
  This is your input stream.

Net Change
  Earned minus Spent.

  If positive → you are growing your money.
  If negative → you are slowly draining it.

  Think of this as:
    "Am I moving forward or backward financially?"

------------------------------------------------------------

[2] CENTRAL TENDENCY (WHAT IS “NORMAL” FOR YOU?)

Average (Mean)
  Add all your expenses, divide by count.

  Problem:
    One large purchase (like {notation200) can distort this heavily.

  Use it for:
    General sense of spending level.

  Do NOT trust it alone.

---

Median (50th Percentile)
  The true “middle” expense.

  Example:
    5, 10, 100 → median = 10

  Why it matters:
    It ignores extreme values.

  This answers:
    "What do I usually spend?"

  If median << average:
    You have occasional large spikes.

------------------------------------------------------------

[3] DISTRIBUTION (HOW YOUR SPENDING IS SHAPED)

25th Percentile (P25)
  25% of your expenses are below this.

  Think:
    "This is my cheap spending zone."

---

75th Percentile (P75)
  75% of your expenses are below this.

  Think:
    "Most of my spending stays under this."

---

90th Percentile (P90)
  Only top 10% exceed this.

  Think:
    "This is where my big purchases begin."

---

IQR (Interquartile Range)
  P75 - P25

  This shows your “normal range”.

  Small IQR:
    You spend consistently.

  Large IQR:
    Your spending varies a lot.

------------------------------------------------------------

[4] VARIABILITY (HOW STABLE YOU ARE)

Standard Deviation
  Measures how far your spending moves from average.

  Low:
    You spend similar amounts each time.

  High:
    Your spending is unpredictable.

---

Volatility (Coefficient of Variation)
  Std Dev ÷ Mean

  This normalizes variability.

  Why this matters:
    $10 variation is huge if you spend $5 normally,
    but small if you spend $500.

  High volatility:
    Chaotic spending behavior.

------------------------------------------------------------

[5] SHAPE OF BEHAVIOR

Skewness
  Shows direction of your outliers.

  Positive skew:
    Mostly small purchases, occasional large spikes.
    (common pattern)

  Negative skew:
    Mostly large spending, rare small ones.

  This answers:
    "Do I sometimes lose control?"

------------------------------------------------------------

[6] BEHAVIORAL SIGNALS

Impulse Buys (<5)
  Small, frequent spending.

  These feel harmless but accumulate.

  High count:
    Habit-driven spending.

---

Big Purchases (>50)
  Large, noticeable spending.

  These define your financial risk moments.

------------------------------------------------------------

[7] TIME-BASED ANALYSIS

Burn Rate
  Average money spent per day.

  This is critical.

  It answers:
    "How fast am I burning money?"

---

Days Over Average
  Days where spending exceeded your normal level.

  Many such days:
    You are frequently overspending.

---

Highest / Lowest Day
  Shows extremes of your daily behavior.

------------------------------------------------------------

[8] EFFICIENCY METRICS

Savings Rate
  % of income you keep.

  Example:
    Earn 100, spend 80 → save 20 → 20%

  High savings rate:
    Strong financial control.

---

Expense Ratio
  % of income you spend.

  Opposite of savings rate.

  High ratio:
    You consume most of what you earn.

------------------------------------------------------------

[9] SURVIVAL METRIC

Runway
  How many days your money will last
  if you continue spending at current rate.

  Example:
    You have $1000, burn $50/day → 20 days.

  This answers:
    "How long before I hit zero?"

------------------------------------------------------------
"""
    console.print(
        Panel(text.strip(), title="[bold yellow]HELP[/]", border_style="cyan")
    )


def colorize(value, good=None, warn=None, reverse=False, is_percent=False):
    """
    Generic color function
    good: threshold for green
    warn: threshold for yellow
    reverse: if True, lower is better (e.g. error)
    """
    if value is None:
        return "[dim]N/A[/]"

    v = value * 100 if is_percent else value

    if reverse:
        if v <= good:
            color = "green"
        elif v <= warn:
            color = "yellow"
        else:
            color = "red"
    else:
        if v >= good:
            color = "green"
        elif v >= warn:
            color = "yellow"
        else:
            color = "red"

    return f"[{color}]{value:.2f}{'%' if is_percent else ''}[/]"


def paginate(transactions, page, show_all):
    if show_all:
        return transactions, 1, 1

    total = len(transactions)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    page = max(1, min(page, total_pages))

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    return transactions[start:end], page, total_pages


def parse_date(date_str):
    parts = date_str.strip().split("/")
    if len(parts) == 2:
        return datetime(datetime.now().year, int(parts[0]), int(parts[1]))
    elif len(parts) == 3:
        year = int(parts[2])
        return datetime(
            year + 2000 if year < 100 else year, int(parts[0]), int(parts[1])
        )
    raise ValueError(f"Invalid date: {date_str}")


def parse_file(filename):
    """Parse transaction file with balance, limit, and +/- transactions"""
    transactions = []
    balance = 0
    limit = None
    current_date = None
    current_date_str = None

    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse balance=XXX
        if line.lower().startswith("balance="):
            try:
                balance = float(line.split("=")[1].strip())
            except:
                pass
            continue

        # Parse limit=XXX
        if line.lower().startswith("limit="):
            try:
                limit = float(line.split("=")[1].strip())
            except:
                pass
            continue

        # Date header
        if line.startswith("#"):
            date_str = line[1:].strip()
            if date_str:
                try:
                    current_date = parse_date(date_str)
                    current_date_str = date_str
                except:
                    pass
            continue

        # Skip header lines
        if "price" in line.lower() and "name" in line.lower():
            continue

        if current_date is None:
            continue

        # Parse transaction: [+]price - name - description
        parts = [p.strip() for p in line.split("-", 2)]
        if len(parts) < 2:
            continue

        try:
            price_str = parts[0]
            is_income = price_str.startswith("+")
            price = float(price_str.replace("+", ""))
            name = parts[1]
            description = parts[2] if len(parts) > 2 else ""
            tag = None

            if "#" in description:
                parts_desc = description.rsplit("#", 1)
                description = parts_desc[0].strip()
                tag = parts_desc[1].strip().lower()

            transactions.append(
                {
                    "date": current_date,
                    "date_str": current_date_str,
                    "amount": price if is_income else -price,
                    "price": price,
                    "name": name,
                    "description": description,
                    "tag": tag,
                    "is_income": is_income,
                }
            )
        except:
            continue

    transactions.sort(key=lambda x: x["date"])
    return transactions, balance, limit


def calculate_stats(transactions):
    """Calculate comprehensive statistics"""
    if not transactions:
        return {}

    expenses = [t for t in transactions if not t["is_income"]]
    incomes = [t for t in transactions if t["is_income"]]

    expense_amounts = sorted([t["price"] for t in expenses])
    income_amounts = [t["price"] for t in incomes]

    # Daily totals
    daily_net = defaultdict(float)
    daily_expense = defaultdict(float)
    daily_income = defaultdict(float)
    for t in transactions:
        daily_net[t["date_str"]] += t["amount"]
        if t["is_income"]:
            daily_income[t["date_str"]] += t["price"]
        else:
            daily_expense[t["date_str"]] += t["price"]

    daily_net_values = list(daily_net.values())
    daily_expense_values = list(daily_expense.values())

    stats = {
        "total_transactions": len(transactions),
        "total_expenses": len(expenses),
        "total_incomes": len(incomes),
        "total_days": len(set(t["date_str"] for t in transactions)),
        "total_spent": sum(expense_amounts) if expense_amounts else 0,
        "total_earned": sum(income_amounts) if income_amounts else 0,
        "net_change": sum(t["amount"] for t in transactions),
    }

    # Expense stats
    if expense_amounts:
        n = len(expense_amounts)
        stats["avg_expense"] = sum(expense_amounts) / n

        # Percentiles
        stats["p25"] = expense_amounts[int(n * 0.25)]
        stats["median"] = stats["p50"] = expense_amounts[int(n * 0.5)]
        stats["p75"] = expense_amounts[int(n * 0.75)]
        stats["p90"] = expense_amounts[int(n * 0.9)]

        stats["iqr"] = stats["p75"] - stats["p25"]

        # Standard deviation
        mean = stats["avg_expense"]
        variance = sum((x - mean) ** 2 for x in expense_amounts) / n
        stats["stddev_expense"] = math.sqrt(variance)
        stats["volatility"] = (stats["stddev_expense"] / mean * 100) if mean > 0 else 0

        # Skewness
        stats["skew"] = (
            sum(((x - mean) / stats["stddev_expense"]) ** 3 for x in expense_amounts)
            / n
        )

        # Purchase categories
        stats["impulse_buys"] = sum(1 for x in expense_amounts if x < 20)
        stats["big_purchases"] = sum(1 for x in expense_amounts if x >= 50)

        stats["max_expense"] = max(expenses, key=lambda x: x["price"])
        stats["min_expense"] = min(expenses, key=lambda x: x["price"])

        # --- Reliability Metrics ---

        # Standard Error (how stable the mean is)
        stats["stderr"] = stats["stddev_expense"] / math.sqrt(n) if n > 1 else 0

        # 95% Confidence Interval for mean (approx, assumes normal-ish data)
        ci_margin = 1.96 * stats["stderr"] if n > 1 else 0
        stats["ci_low"] = mean - ci_margin
        stats["ci_high"] = mean + ci_margin

        # Relative error (how big the uncertainty is vs mean)
        stats["relative_error"] = (stats["stderr"] / mean * 100) if mean > 0 else 0

        # Median-Mean gap (skew / instability signal)
        stats["mean_median_gap"] = abs(mean - stats["median"])

        # Sample size quality
        if n < 5:
            stats["sample_quality"] = "very_low"
        elif n < 15:
            stats["sample_quality"] = "low"
        elif n < 30:
            stats["sample_quality"] = "moderate"
        else:
            stats["sample_quality"] = "good"

        # --- Outlier detection (IQR method) ---
        q1 = stats["p25"]
        q3 = stats["p75"]
        iqr = stats["iqr"]

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [x for x in expense_amounts if x < lower_bound or x > upper_bound]

        stats["outlier_count"] = len(outliers)
        stats["outlier_ratio"] = (len(outliers) / n * 100) if n > 0 else 0

    # Advanced finance stats
    if len(daily_expense_values) > 0:
        stats["avg_daily"] = sum(daily_expense_values) / len(daily_expense_values)
        stats["max_daily_spend"] = max(daily_expense_values)
        stats["min_daily_spend"] = min(daily_expense_values)
        stats["max_daily_change"] = max(daily_net_values, key=abs)

        stats["days_over_average"] = sum(
            1 for v in daily_expense_values if v > stats["avg_daily"]
        )

        # Burn rate and runway
        stats["burn_rate"] = stats["avg_daily"]

    if stats["total_earned"] > 0:
        stats["savings_rate"] = (1 - stats["total_spent"] / stats["total_earned"]) * 100
        stats["expense_ratio"] = (stats["total_spent"] / stats["total_earned"]) * 100

    # Daily stats
    if daily_expense:
        daily_vals = list(daily_expense.items())
        stats["highest_day"] = max(daily_vals, key=lambda x: x[1])
        stats["lowest_day"] = min(daily_vals, key=lambda x: x[1])

    return stats


def display_transactions(transactions, initial_balance, limit, show_tag=True):
    """Display transaction table with before:after balance"""
    table = Table(
        title="[bold yellow]TRANSACTION LOG[/]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=False,
        padding=(0, 1),
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Date", style="blue", width=8)
    table.add_column("Amount", width=12, justify="right")
    table.add_column("Name", width=16)
    table.add_column("Desc", width=20)
    if show_tag:
        table.add_column("Tag", width=10)
    table.add_column("Balance", width=14, justify="center")

    balance = initial_balance

    for i, t in enumerate(transactions, 1):
        before = balance
        balance += t["amount"]
        after = balance

        # Amount formatting
        if t["is_income"]:
            amt_str = f"[bold green]+{notation}{t['price']:.2f}[/]"
        else:
            amt_str = f"[red]-{notation}{t['price']:.2f}[/]"

        # Balance color based on status
        if after < 0:
            bal_style = "bold red"
        elif limit and after < limit * 0.2:
            bal_style = "yellow"
        else:
            bal_style = "white"

        bal_str = f"[dim]{before:.0f}[/]→[{bal_style}]{after:.0f}[/]"

        # Truncate name if needed
        name = t["name"][:15] + ".." if len(t["name"]) > 15 else t["name"]

        # Description with rich markup support (short)
        desc = (
            t["description"][:18] + ".."
            if len(t["description"]) > 18
            else t["description"]
        )
        desc = f"[dim italic]{desc}[/]" if desc else ""

        # Tags
        tag_str = f"[magenta]{t['tag']}[/]" if t.get("tag") else ""

        row = [
            str(i),
            t["date_str"],
            amt_str,
            name,
            desc,
        ]

        if show_tag:
            row.append(tag_str)

        row.append(bal_str)

        table.add_row(*row)

    console.print()
    console.print(table)

    return balance


def display_bar_graph(transactions, initial_balance, width=40):
    """Display horizontal bar graph with daily balance"""
    if not transactions:
        return

    # Group by date and track order
    daily = defaultdict(lambda: {"expense": 0, "income": 0})
    date_order = []

    for t in transactions:
        if t["date_str"] not in date_order:
            date_order.append(t["date_str"])
        if t["is_income"]:
            daily[t["date_str"]]["income"] += t["price"]
        else:
            daily[t["date_str"]]["expense"] += t["price"]

    max_val = max(max(d["expense"], d["income"]) for d in daily.values())
    if max_val == 0:
        max_val = 1

    # Build graph lines
    lines = []
    balance = initial_balance

    for date_str in date_order:
        vals = daily[date_str]
        net_change = vals["income"] - vals["expense"]
        balance += net_change

        # Expense bar
        exp_len = int((vals["expense"] / max_val) * width)
        exp_bar = "[red]" + "█" * exp_len + "[dim]" + "░" * (width - exp_len) + "[/]"

        # Balance indicator
        if balance < 0:
            bal_style = "bold red"
        elif balance < initial_balance * 0.3:
            bal_style = "yellow"
        else:
            bal_style = "green"

        lines.append(
            f"[blue]{date_str:<7}[/] {exp_bar} [white]{notation}{vals['expense']:<6.0f}[/] → [{bal_style}]{notation}{balance:.0f}[/]"
        )

        # Income bar (if any)
        if vals["income"] > 0:
            inc_len = int((vals["income"] / max_val) * width)
            inc_bar = "[green]" + "█" * inc_len + "[/]"
            lines.append(
                f"[dim]{'':>7}[/] {inc_bar} [green]+{notation}{vals['income']:.0f}[/]"
            )

    # Add legend
    lines.append("")
    lines.append("[red]█[/] Expense    [green]█[/] Income    [dim]→[/] Balance after")

    panel = Panel(
        "\n".join(lines),
        title="[bold yellow]DAILY SPENDING[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)


def display_stats(stats, initial_balance, final_balance, limit, hide_right=False):
    """Display statistics panel"""

    # Left column - Balance info
    left_rows = [
        ("Starting Balance", f"[white]{notation}{initial_balance:.2f}[/]"),
        ("Final Balance", f"[bold white]{notation}{final_balance:.2f}[/]"),
    ]

    if limit:
        remaining = limit - stats.get("total_spent", 0)
        pct_used = (stats.get("total_spent", 0) / limit * 100) if limit > 0 else 0

        if pct_used > 100:
            limit_style = "bold red"
        elif pct_used > 80:
            limit_style = "yellow"
        else:
            limit_style = "green"

        left_rows.append(("Budget Limit", f"[white]{notation}{limit:.2f}[/]"))
        left_rows.append(
            (
                "Remaining",
                f"[{limit_style}]{notation}{remaining:.2f} ({100 - pct_used:.0f}%)[/]",
            )
        )

    left_rows.extend(
        [
            ("", ""),
            ("Total Spent", f"[red]{notation}{stats.get('total_spent', 0):.2f}[/]"),
            ("Total Earned", f"[green]{notation}{stats.get('total_earned', 0):.2f}[/]"),
            ("Net Change", f"[bold]{notation}{stats.get('net_change', 0):.2f}[/]"),
        ]
    )

    # Right column - Statistics
    right_rows = [
        (
            "Transactions",
            f"{stats.get('total_transactions', 0)} [dim]({stats.get('total_expenses', 0)} exp, {stats.get('total_incomes', 0)} inc)[/]",
        ),
        ("Days Tracked", str(stats.get("total_days", 0))),
    ]

    right_rows.extend(
        [
            ("", ""),
            (
                "SE",
                colorize(
                    stats["stderr"],
                    good=stats["avg_expense"] * 0.1,
                    warn=stats["avg_expense"] * 0.3,
                    reverse=True,
                ),
            ),
            (
                "95% CI",
                f"[cyan]{notation}{stats['ci_low']:.2f} - {notation}{stats['ci_high']:.2f}[/]",
            ),
            (
                "Rel Error",
                colorize(
                    stats["relative_error"],
                    good=10,
                    warn=30,
                    reverse=True,
                    is_percent=True,
                ),
            ),
            (
                "Mean-Median Gap",
                colorize(
                    stats["mean_median_gap"],
                    good=stats["stddev_expense"] * 0.3,
                    warn=stats["stddev_expense"],
                    reverse=True,
                ),
            ),
            (
                "Sample Quality",
                (
                    "[green]good[/]"
                    if stats["sample_quality"] == "good"
                    else "[yellow]mid[/]"
                    if stats["sample_quality"] == "moderate"
                    else "[orange1]bad[/]"
                    if stats["sample_quality"] == "low"
                    else "[red]foul[/]"
                ),
            ),
            (
                "Outliers",
                colorize(
                    stats["outlier_ratio"],
                    good=5,
                    warn=15,
                    reverse=True,
                    is_percent=True,
                ),
            ),
        ]
    )
    if "avg_expense" in stats:
        right_rows.extend(
            [
                ("", ""),
                ("Avg Expense", f"{notation}{stats['avg_expense']:.2f}"),
                (
                    "Median",
                    f"[white]{notation}{stats['median']:.2f}[/]"
                    if stats["mean_median_gap"] < stats["stddev_expense"]
                    else f"[yellow]{notation}{stats['median']:.2f}[/]",
                ),
                ("Std Dev", f"{notation}{stats['stddev_expense']:.2f}"),
                (
                    "Volatility",
                    colorize(
                        stats["volatility"],
                        good=20,
                        warn=50,
                        reverse=True,
                        is_percent=True,
                    ),
                ),
            ]
        )
    if "savings_rate" in stats:
        left_rows.extend(
            [
                ("", ""),
                ("Savings Rate", f"{stats['savings_rate']:.1f}%"),
                ("Expense Ratio", f"{stats['expense_ratio']:.1f}%"),
                ("Burn Rate", f"{notation}{stats['burn_rate']:.2f}/day"),
            ]
        )
    if "max_expense" in stats:
        max_e = stats["max_expense"]
        min_e = stats["min_expense"]
        right_rows.extend(
            [
                ("", ""),
                (
                    "Highest",
                    f"[red]{notation}{max_e['price']:.2f}[/] [dim]({max_e['name'][:10]})[/]",
                ),
                (
                    "Lowest",
                    f"[green]{notation}{min_e['price']:.2f}[/] [dim]({min_e['name'][:10]})[/]",
                ),
            ]
        )

    if "highest_day" in stats:
        h = stats["highest_day"]
        l = stats["lowest_day"]
        right_rows.extend(
            [
                ("", ""),
                ("25th Percentile", f"{stats['p25']:.2f}"),
                ("75th Percentile", f"{stats['p75']:.2f}"),
                ("90th Percentile", f"{stats['p90']:.2f}"),
                ("IQR Spread", f"{stats['iqr']:.2f}"),
                ("Skewness", f"{stats['skew']:.2f}"),
                ("", ""),
                ("Impulse Buys <20", f"{stats['impulse_buys']}"),
                ("Big Purchases >50", f"{stats['big_purchases']}"),
                (
                    "Days over average",
                    f"{stats['days_over_average']} / {stats['total_days']}",
                ),
            ]
        )

    if final_balance > 0 and "burn_rate" in stats:
        runway = final_balance / stats["burn_rate"]
        right_rows.append(("Runway", f"{runway:.0f} days"))

    # Build tables
    left_table = Table(box=None, show_header=False, padding=(0, 1))
    left_table.add_column("Label", style="cyan")
    left_table.add_column("Value", justify="right")
    for label, value in left_rows:
        if label == "":
            left_table.add_row("", "")
        else:
            left_table.add_row(label, value)

    right_table = Table(box=None, show_header=False, padding=(0, 1))
    right_table.add_column("Label", style="cyan")
    right_table.add_column("Value", justify="right")
    for label, value in right_rows:
        if label == "":
            right_table.add_row("", "")
        else:
            right_table.add_row(label, value)

    # Combine into panel

    if hide_right:  # shit i thought its hide-left, its hide-right.
        columns = Columns([left_table], padding=4, expand=True)
    else:
        columns = Columns([left_table, right_table], padding=4, expand=True)
    panel = Panel(
        columns,
        title="[bold yellow]STATISTICS[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)


def display_warnings(final_balance, limit, stats):
    """Display any warnings"""
    warnings = []

    if final_balance < 0:
        warnings.append(
            f"[bold red]⚠ NEGATIVE BALANCE:[/] [red]{notation}{final_balance:.2f}[/]"
        )

    if limit:
        spent = stats.get("total_spent", 0)
        if spent > limit:
            warnings.append(
                f"[bold red]⚠ OVER BUDGET[/] by [red]{notation}{spent - limit:.2f}[/]"
            )
        elif spent > limit * 0.9:
            warnings.append(f"[yellow]⚠ Warning:[/] 90%+ of budget used")

    if stats.get("volatility", 0) > 100:
        warnings.append(
            f"[yellow]⚠ High spending volatility[/] [dim]({stats['volatility']:.0f}% CV)[/]"
        )

    if warnings:
        panel = Panel(
            "\n".join(warnings),
            title="[bold red]WARNINGS[/]",
            border_style="red",
            box=box.ROUNDED,
            padding=(0, 2),
        )
        console.print()
        console.print(panel)

    # -- Reliability Warning --
    if stats.get("sample_quality") == "very_low":
        warnings.append("[yellow]⚠ Very low sample size → stats unreliable[/]")
    elif stats.get("sample_quality") == "low":
        warnings.append("[yellow]⚠ Low sample size → interpret cautiously[/]")

    if stats.get("relative_error", 0) > 50:
        warnings.append("[yellow]⚠ High uncertainty in mean (high standard error)[/]")

    if stats.get("mean_median_gap", 0) > stats.get("stddev_expense", 0):
        warnings.append("[yellow]⚠ Mean far from median → skewed data[/]")

    if stats.get("outlier_ratio", 0) > 20:
        warnings.append("[yellow]⚠ Many outliers → unstable distribution[/]")


def display_header(filename, initial_balance, limit, count):
    """Display header"""
    info = f"[white]File:[/] {filename}\n"
    info += f"[white]Balance:[/] [green]{notation}{initial_balance:.2f}[/]"
    if limit:
        info += f"  [dim]|[/]  [white]Limit:[/] [yellow]{notation}{limit:.2f}[/]"
    info += f"\n[white]Transactions:[/] {count}"

    panel = Panel(
        info,
        title="[bold yellow]💰 MONEY TRACKER[/]",
        border_style="cyan",
        box=box.DOUBLE,
        padding=(0, 2),
    )
    console.print()
    console.print(panel)


def parse_args(argv):
    page = 1
    show_all = True
    tag_filter = None
    no_stat = False

    for arg in argv[2:]:
        if arg.startswith("p-"):
            val = arg[2:]

            if val == "all":
                show_all = True
            else:
                try:
                    page = int(val)
                    show_all = False  # ← ONLY paginate if number is given
                except:
                    pass

        elif arg.startswith("t-"):
            tag_filter = arg[2:].lower()

        elif arg == "--nostat":
            no_stat = True

    return page, show_all, tag_filter, no_stat


def main():
    if os.name == "nt":
        os.system("")

    if len(sys.argv) < 2:
        console.print(
            Panel(
                "[white]Usage:[/] money_graph.py [cyan]<file.txt>[/]\n\n"
                "[dim]File format:[/]\n"
                "  [yellow]balance=100[/]        [dim]# starting balance[/]\n"
                "  [yellow]limit=500[/]          [dim]# budget limit (optional)[/]\n"
                "  \n"
                "  [magenta]# 4/1/26[/]           [dim]# date header[/]\n"
                "  [white]10 - Coffee - tasty[/] [dim]# expense[/]\n"
                "  [green]+50 - Refund[/]        [dim]# income (with +)[/]",
                title="[bold yellow]💰 MONEY TRACKER[/]",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.exists(filename):
        console.print(f"[bold red]Error:[/] File not found: {filename}")
        sys.exit(1)

    # Parse and process
    transactions, initial_balance, limit = parse_file(filename)

    if not transactions:
        console.print("[bold red]Error:[/] No transactions found.")
        sys.exit(1)

    page, show_all, tag_filter, no_stat = parse_args(sys.argv)

    if tag_filter:
        transactions = [t for t in transactions if t.get("tag") == tag_filter]

    paged_tx, current_page, total_pages = paginate(transactions, page, show_all)

    console.print(f"[dim]Page {current_page}/{total_pages}[/]\n")

    final_balance = display_transactions(
        paged_tx,
        initial_balance,
        limit,
        show_tag=True,  # <--- THIS enforces tags!
    )
    display_bar_graph(transactions, initial_balance)

    stats = calculate_stats(transactions)
    display_stats(stats, initial_balance, final_balance, limit, hide_right=no_stat)
    display_warnings(final_balance, limit, stats)

    console.print()


if __name__ == "__main__":
    if "--help" in sys.argv:
        show_help()
        sys.exit(0)
    main()
