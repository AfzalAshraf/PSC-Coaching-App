"""Step-by-step, offline arithmetic tools for PSC exam preparation."""

from __future__ import annotations

import random
import re
from math import gcd
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping


CENT = Decimal("0.01")
ANSWER_TOLERANCE = Decimal("0.01")


@dataclass(frozen=True)
class MathSolution:
    """A learner-facing answer with explicit working and one recall cue."""

    label: str
    value: Decimal
    unit: str
    steps: tuple[str, ...]
    memory_tip: str

    @property
    def formatted_value(self) -> str:
        return format_number(self.value)

    @property
    def display_value(self) -> str:
        if self.unit == "₹":
            return f"₹{self.formatted_value}"
        if self.unit == "%":
            return f"{self.formatted_value}%"
        return f"{self.formatted_value} {self.unit}".strip()


@dataclass(frozen=True)
class MathDrill:
    """One generated mental-maths practice item."""

    topic: str
    prompt: str
    answer: Decimal
    unit: str
    steps: tuple[str, ...]
    memory_tip: str

    @property
    def formatted_answer(self) -> str:
        return format_number(self.answer)

    @property
    def display_answer(self) -> str:
        if self.unit == "₹":
            return f"₹{self.formatted_answer}"
        return f"{self.formatted_answer} {self.unit}".strip()


def format_number(value: Decimal | int | str) -> str:
    """Render a decimal without scientific notation or unnecessary zeroes."""
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    rounded = number.quantize(CENT, rounding=ROUND_HALF_UP)
    if rounded == rounded.to_integral_value():
        return format(rounded.quantize(Decimal("1")), "f")
    return format(rounded.normalize(), "f")


def _number(raw: Any, field: str) -> Decimal:
    text = str(raw).strip().replace(",", "")
    text = re.sub(r"(?:km/?h|hours?|hrs?|km|rupees?|rs\.?|inr|₹|%)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    if not text:
        raise ValueError(f"Enter a value for {field}.")
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a number, for example 12 or 12.5.") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite number.")
    return result


def _nonnegative(value: Decimal, field: str) -> Decimal:
    if value < 0:
        raise ValueError(f"{field} cannot be negative.")
    return value


def _positive(value: Decimal, field: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return value


def _solution(label: str, value: Decimal, unit: str, steps: list[str], tip: str) -> MathSolution:
    return MathSolution(label, value, unit, tuple(steps), tip)


def solve_calculation(kind: str, values: Mapping[str, Any]) -> MathSolution:
    """Solve one supported arithmetic calculator and return teachable steps.

    ``kind`` selects a percentage, average, ratio, interest, profit/loss,
    speed-distance-time, time/work, discount, HCF/LCM, rectangle or fraction
    calculator. Invalid or impossible inputs raise ``ValueError``
    with a message suitable for displaying to a learner.
    """
    if kind == "percent_of":
        rate = _nonnegative(_number(values.get("rate", ""), "Percentage"), "Percentage")
        number = _nonnegative(_number(values.get("number", ""), "Number"), "Number")
        value = number * rate / Decimal(100)
        one_percent = number / Decimal(100)
        return _solution(
            "Result",
            value,
            "",
            [
                f"1% of {format_number(number)} = {format_number(number)} ÷ 100 = {format_number(one_percent)}.",
                f"{format_number(rate)}% = {format_number(one_percent)} × {format_number(rate)} = {format_number(value)}.",
            ],
            "Find 10% by dividing by 10; 5% is half of 10%, and 1% is divide by 100.",
        )

    if kind == "percent_change":
        before = _positive(_number(values.get("before", ""), "Original value"), "Original value")
        after = _number(values.get("after", ""), "New value")
        change = after - before
        rate = abs(change) / before * Decimal(100)
        label = "Increase" if change > 0 else "Decrease" if change < 0 else "No change"
        steps = [
            f"Change = new value − original value = {format_number(after)} − {format_number(before)} = {format_number(change)}.",
            f"Percentage change = |change| ÷ original value × 100 = {format_number(abs(change))} ÷ {format_number(before)} × 100 = {format_number(rate)}%.",
        ]
        if change == 0:
            steps = ["The new value equals the original value, so there is no change."]
        return _solution(label, rate, "%", steps, "Percentage change is measured against the original value, not the new value.")

    if kind == "average":
        raw_values = str(values.get("numbers", "")).strip()
        parts = [item for item in re.split(r"[,;\s]+", raw_values) if item]
        if len(parts) < 2:
            raise ValueError("Enter at least two numbers, separated by commas.")
        numbers = [_number(item, f"Number {index}") for index, item in enumerate(parts, start=1)]
        total = sum(numbers, Decimal(0))
        value = total / Decimal(len(numbers))
        preview = " + ".join(format_number(item) for item in numbers)
        return _solution(
            "Average",
            value,
            "",
            [f"Add the values: {preview} = {format_number(total)}.", f"Divide by how many values: {format_number(total)} ÷ {len(numbers)} = {format_number(value)}."],
            "Average = total ÷ count. To check, average × count should give the total.",
        )

    if kind == "ratio_share":
        first = _nonnegative(_number(values.get("first", ""), "First ratio part"), "First ratio part")
        second = _nonnegative(_number(values.get("second", ""), "Second ratio part"), "Second ratio part")
        total = _nonnegative(_number(values.get("total", ""), "Total amount"), "Total amount")
        parts = first + second
        if parts == 0:
            raise ValueError("The ratio parts cannot both be zero.")
        which = str(values.get("share", "second")).strip().lower()
        if which not in {"first", "second"}:
            raise ValueError("Choose whether to find the first or second share.")
        target = first if which == "first" else second
        one_part = total / parts
        share = one_part * target
        return _solution(
            f"{which.title()} share",
            share,
            "",
            [f"Total ratio parts = {format_number(first)} + {format_number(second)} = {format_number(parts)}.", f"Value of one part = total ÷ parts = {format_number(total)} ÷ {format_number(parts)} = {format_number(one_part)}.", f"{which.title()} share = {format_number(target)} × {format_number(one_part)} = {format_number(share)}."],
            "Add the ratio parts → find the value of one part → multiply by the part you need.",
        )

    if kind == "simple_interest":
        principal = _nonnegative(_number(values.get("principal", ""), "Principal"), "Principal")
        rate = _nonnegative(_number(values.get("rate", ""), "Annual rate"), "Annual rate")
        years = _nonnegative(_number(values.get("years", ""), "Time in years"), "Time in years")
        interest = principal * rate * years / Decimal(100)
        total = principal + interest
        return _solution(
            "Simple interest",
            interest,
            "",
            [f"Use SI = P × R × T ÷ 100.", f"SI = {format_number(principal)} × {format_number(rate)} × {format_number(years)} ÷ 100 = {format_number(interest)}.", f"Total amount = principal + interest = {format_number(principal)} + {format_number(interest)} = {format_number(total)}."],
            "Remember P-R-T: Principal × Rate × Time, then divide by 100.",
        )

    if kind == "profit_loss":
        cost = _positive(_number(values.get("cost", ""), "Cost price"), "Cost price")
        selling = _nonnegative(_number(values.get("selling", ""), "Selling price"), "Selling price")
        difference = selling - cost
        rate = abs(difference) / cost * Decimal(100)
        label = "Profit" if difference > 0 else "Loss" if difference < 0 else "Break-even"
        if difference == 0:
            steps = [f"Selling price equals cost price ({format_number(cost)}), so there is no profit or loss."]
        else:
            kind_name = "profit" if difference > 0 else "loss"
            steps = [f"{kind_name.title()} = |selling price − cost price| = |{format_number(selling)} − {format_number(cost)}| = {format_number(abs(difference))}.", f"{kind_name.title()}% = {kind_name} ÷ cost price × 100 = {format_number(abs(difference))} ÷ {format_number(cost)} × 100 = {format_number(rate)}%."]
        return _solution(label, rate, "%", steps, "Profit or loss percentage uses cost price as the base.")

    if kind == "speed_distance_time":
        target = str(values.get("solve_for", "distance")).strip().lower()
        if target not in {"distance", "speed", "time"}:
            raise ValueError("Choose whether to find distance, speed or time.")
        distance_raw, speed_raw, time_raw = (str(values.get(key, "")).strip() for key in ("distance", "speed", "time"))
        if target == "distance":
            speed = _nonnegative(_number(speed_raw, "Speed"), "Speed")
            time = _nonnegative(_number(time_raw, "Time"), "Time")
            value = speed * time
            steps = ["Use distance = speed × time.", f"Distance = {format_number(speed)} × {format_number(time)} = {format_number(value)}."]
        elif target == "speed":
            distance = _nonnegative(_number(distance_raw, "Distance"), "Distance")
            time = _positive(_number(time_raw, "Time"), "Time")
            value = distance / time
            steps = ["Rearrange the formula: speed = distance ÷ time.", f"Speed = {format_number(distance)} ÷ {format_number(time)} = {format_number(value)}."]
        else:
            distance = _nonnegative(_number(distance_raw, "Distance"), "Distance")
            speed = _positive(_number(speed_raw, "Speed"), "Speed")
            value = distance / speed
            steps = ["Rearrange the formula: time = distance ÷ speed.", f"Time = {format_number(distance)} ÷ {format_number(speed)} = {format_number(value)}."]
        units = {"distance": "km", "speed": "km/h", "time": "hours"}
        return _solution(target.title(), value, units[target], steps, "Use the D-S-T triangle: distance = speed × time; divide to find either of the other two.")

    if kind == "time_work":
        days_a = _positive(_number(values.get("days_a", ""), "Worker A days"), "Worker A days")
        days_b = _positive(_number(values.get("days_b", ""), "Worker B days"), "Worker B days")
        rate_a = Decimal(1) / days_a
        rate_b = Decimal(1) / days_b
        combined_rate = rate_a + rate_b
        days = Decimal(1) / combined_rate
        return _solution(
            "Time together",
            days,
            "days",
            [f"A's one-day work rate = 1 ÷ {format_number(days_a)} = {format_number(rate_a)} of the job.", f"B's one-day work rate = 1 ÷ {format_number(days_b)} = {format_number(rate_b)} of the job.", f"Add the rates, then invert: 1 ÷ ({format_number(rate_a)} + {format_number(rate_b)}) = {format_number(days)} days."],
            "Work rate = 1 ÷ days. Add the workers' daily rates, then take 1 ÷ the combined rate.",
        )

    if kind == "discount_price":
        marked = _nonnegative(_number(values.get("marked_price", ""), "Marked price"), "Marked price")
        rate = _nonnegative(_number(values.get("discount_rate", ""), "Discount percentage"), "Discount percentage")
        if rate > 100:
            raise ValueError("Discount cannot be more than 100%.")
        discount = marked * rate / Decimal(100)
        sale_price = marked - discount
        return _solution(
            "Sale price",
            sale_price,
            "",
            [f"Discount = marked price × rate ÷ 100 = {format_number(marked)} × {format_number(rate)} ÷ 100 = {format_number(discount)}.", f"Sale price = marked price − discount = {format_number(marked)} − {format_number(discount)} = {format_number(sale_price)}."],
            "Find the discount first; subtract it from the marked price to get the sale price.",
        )

    if kind == "hcf_lcm":
        first = _positive(_number(values.get("first_number", ""), "First whole number"), "First whole number")
        second = _positive(_number(values.get("second_number", ""), "Second whole number"), "Second whole number")
        if first != first.to_integral_value() or second != second.to_integral_value():
            raise ValueError("HCF and LCM need whole numbers.")
        first_int, second_int = int(first), int(second)
        highest = gcd(first_int, second_int)
        lowest = first_int * second_int // highest
        return _solution(
            "LCM",
            Decimal(lowest),
            "",
            [f"HCF of {first_int} and {second_int} = {highest}.", f"LCM = first number × second number ÷ HCF = {first_int} × {second_int} ÷ {highest} = {lowest}."],
            "For two positive whole numbers: HCF × LCM = their product.",
        )

    if kind == "rectangle":
        length = _positive(_number(values.get("length", ""), "Length"), "Length")
        width = _positive(_number(values.get("width", ""), "Width"), "Width")
        area = length * width
        perimeter = Decimal(2) * (length + width)
        return _solution(
            "Area",
            area,
            "square units",
            [f"Area = length × width = {format_number(length)} × {format_number(width)} = {format_number(area)} square units.", f"Perimeter = 2 × (length + width) = 2 × ({format_number(length)} + {format_number(width)}) = {format_number(perimeter)} units."],
            "Area fills the inside; perimeter measures the boundary around it.",
        )

    if kind == "fraction_percent":
        numerator = _number(values.get("numerator", ""), "Numerator")
        denominator = _number(values.get("denominator", ""), "Denominator")
        if denominator == 0:
            raise ValueError("The denominator cannot be zero.")
        value = numerator / denominator * Decimal(100)
        return _solution(
            "Percentage",
            value,
            "%",
            [f"Divide numerator by denominator: {format_number(numerator)} ÷ {format_number(denominator)} = {format_number(numerator / denominator)}.", f"Multiply by 100: {format_number(numerator / denominator)} × 100 = {format_number(value)}%."],
            "Fraction to percent: numerator ÷ denominator × 100.",
        )

    raise ValueError(f"Unknown calculator: {kind}.")


def answer_matches(raw_answer: str, expected: Decimal, *, tolerance: Decimal = ANSWER_TOLERANCE) -> bool:
    """Check a typed numeric answer, allowing harmless rounding to 2 decimals."""
    try:
        value = _number(raw_answer, "Your answer")
    except ValueError:
        return False
    return abs(value - expected) <= tolerance


def generate_math_drill(rng: random.Random | None = None) -> MathDrill:
    """Generate one whole-number, worked arithmetic question for a quick drill."""
    rng = rng or random.Random()
    kind = rng.choice(("percent", "average", "ratio", "interest", "speed", "discount"))

    if kind == "percent":
        rate = rng.choice((5, 10, 15, 20, 25, 40, 50))
        base = rng.choice((200, 240, 300, 400, 600, 800, 1_000))
        value = Decimal(base * rate // 100)
        return MathDrill(
            "Percentages",
            f"What is {rate}% of {base}?",
            value,
            "",
            (f"10% of {base} is {base // 10}.", f"{rate}% of {base} = {base} × {rate} ÷ 100 = {format_number(value)}."),
            "10% is divide by 10; 5% is half of 10%.",
        )

    if kind == "average":
        average = rng.randint(20, 90)
        first_offset = rng.randint(2, 12)
        second_offset = rng.randint(2, 12)
        values = [average + first_offset, average - first_offset, average + second_offset, average - second_offset]
        rng.shuffle(values)
        total = sum(values)
        return MathDrill(
            "Average",
            f"Find the average of {', '.join(map(str, values))}.",
            Decimal(average),
            "",
            (f"Add the numbers: {values[0]} + {values[1]} + {values[2]} + {values[3]} = {total}.", f"Divide by 4 numbers: {total} ÷ 4 = {average}."),
            "Average = total ÷ count; check by multiplying the average by the count.",
        )

    if kind == "ratio":
        first, second = rng.choice(((2, 3), (3, 5), (4, 7), (5, 3), (7, 5)))
        one_part = rng.randint(4, 20)
        total = (first + second) * one_part
        answer = second * one_part
        return MathDrill(
            "Ratio and proportion",
            f"A total of {total} is divided in the ratio {first}:{second}. What is the second share?",
            Decimal(answer),
            "",
            (f"Total parts = {first} + {second} = {first + second}.", f"One part = {total} ÷ {first + second} = {one_part}.", f"Second share = {second} × {one_part} = {answer}."),
            "Add parts → find one part → multiply by the part you need.",
        )

    if kind == "interest":
        principal = rng.choice((1_000, 2_000, 3_000, 4_000, 5_000))
        rate = rng.choice((4, 5, 6, 8, 10, 12))
        years = rng.randint(1, 5)
        interest = principal * rate * years // 100
        return MathDrill(
            "Simple interest",
            f"Find the simple interest on ₹{principal} at {rate}% per year for {years} years.",
            Decimal(interest),
            "₹",
            ("Use SI = P × R × T ÷ 100.", f"SI = {principal} × {rate} × {years} ÷ 100 = ₹{interest}."),
            "P-R-T, then divide by 100: Principal × Rate × Time ÷ 100.",
        )

    if kind == "speed":
        speed = rng.randint(25, 90)
        hours = rng.randint(2, 8)
        distance = speed * hours
        return MathDrill(
            "Speed, distance and time",
            f"A bus travels at {speed} km/h for {hours} hours. How far does it travel?",
            Decimal(distance),
            "km",
            ("Use distance = speed × time.", f"Distance = {speed} × {hours} = {distance} km."),
            "D-S-T: distance = speed × time.",
        )

    cost = rng.randrange(200, 1_001, 100)
    discount_rate = rng.choice((10, 20, 25, 50))
    discount = cost * discount_rate // 100
    selling = cost - discount
    return MathDrill(
        "Discounts",
        f"A bag marked ₹{cost} gets a {discount_rate}% discount. What is the sale price?",
        Decimal(selling),
        "₹",
        (f"Discount = {discount_rate}% of ₹{cost} = ₹{discount}.", f"Sale price = marked price − discount = ₹{cost} − ₹{discount} = ₹{selling}."),
        "Find the discount first, then subtract it from the marked price.",
    )
