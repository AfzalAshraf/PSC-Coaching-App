from __future__ import annotations

import random
import unittest
from decimal import Decimal

from psc_coach.math_tools import answer_matches, format_number, generate_math_drill, solve_calculation


class StepByStepCalculatorTests(unittest.TestCase):
    def test_percentage_of_number_shows_a_mental_shortcut(self):
        result = solve_calculation("percent_of", {"rate": "25", "number": "240"})
        self.assertEqual(result.value, Decimal("60"))
        self.assertEqual(result.formatted_value, "60")
        self.assertIn("10%", result.memory_tip)
        self.assertEqual(len(result.steps), 2)

    def test_percentage_change_uses_the_original_value_as_the_base(self):
        increase = solve_calculation("percent_change", {"before": "80", "after": "100"})
        decrease = solve_calculation("percent_change", {"before": "100", "after": "80"})
        self.assertEqual((increase.label, increase.value), ("Increase", Decimal("25")))
        self.assertEqual((decrease.label, decrease.value), ("Decrease", Decimal("20")))
        self.assertIn("original value", increase.memory_tip)

    def test_average_accepts_comma_or_space_separated_numbers(self):
        result = solve_calculation("average", {"numbers": "12, 18, 24, 30"})
        self.assertEqual(result.value, Decimal("21"))
        spaced = solve_calculation("average", {"numbers": "12 18 24 30"})
        self.assertEqual(spaced.value, result.value)

    def test_ratio_share_explains_the_one_part_method(self):
        result = solve_calculation("ratio_share", {"first": "2", "second": "3", "total": "250", "share": "second"})
        self.assertEqual(result.value, Decimal("150"))
        self.assertIn("one part", result.memory_tip)
        first = solve_calculation("ratio_share", {"first": "2", "second": "3", "total": "250", "share": "first"})
        self.assertEqual(first.value, Decimal("100"))

    def test_simple_interest_includes_total_amount_step(self):
        result = solve_calculation("simple_interest", {"principal": "2000", "rate": "5", "years": "3"})
        self.assertEqual(result.value, Decimal("300"))
        self.assertIn("amount", result.steps[-1])
        self.assertIn("P-R-T", result.memory_tip)

    def test_profit_percentage_is_based_on_cost_price(self):
        profit = solve_calculation("profit_loss", {"cost": "500", "selling": "600"})
        loss = solve_calculation("profit_loss", {"cost": "500", "selling": "400"})
        self.assertEqual((profit.label, profit.value), ("Profit", Decimal("20")))
        self.assertEqual((loss.label, loss.value), ("Loss", Decimal("20")))
        self.assertIn("cost price", loss.memory_tip)

    def test_speed_distance_time_solves_each_unknown(self):
        distance = solve_calculation("speed_distance_time", {"solve_for": "distance", "speed": "60", "time": "2.5"})
        speed = solve_calculation("speed_distance_time", {"solve_for": "speed", "distance": "150", "time": "2.5"})
        time = solve_calculation("speed_distance_time", {"solve_for": "time", "distance": "150", "speed": "60"})
        self.assertEqual((distance.value, distance.unit), (Decimal("150.0"), "km"))
        self.assertEqual((speed.value, speed.unit), (Decimal("60"), "km/h"))
        self.assertEqual((time.value, time.unit), (Decimal("2.5"), "hours"))
        self.assertEqual(distance.display_value, "150 km")

    def test_time_and_work_adds_daily_rates_then_inverts(self):
        result = solve_calculation("time_work", {"days_a": "4", "days_b": "6"})
        self.assertEqual(result.value, Decimal("2.4"))
        self.assertEqual(result.display_value, "2.4 days")
        self.assertIn("combined rate", result.memory_tip)

    def test_discount_and_sale_price_show_both_steps(self):
        result = solve_calculation("discount_price", {"marked_price": "2000", "discount_rate": "25"})
        self.assertEqual(result.value, Decimal("1500"))
        self.assertIn("discount", result.steps[0].lower())
        with self.assertRaisesRegex(ValueError, "more than 100%"):
            solve_calculation("discount_price", {"marked_price": "100", "discount_rate": "101"})

    def test_hcf_and_lcm_require_whole_numbers(self):
        result = solve_calculation("hcf_lcm", {"first_number": "12", "second_number": "18"})
        self.assertEqual(result.value, Decimal("36"))
        self.assertIn("HCF of 12 and 18 = 6", result.steps[0])
        with self.assertRaisesRegex(ValueError, "whole numbers"):
            solve_calculation("hcf_lcm", {"first_number": "12.5", "second_number": "18"})

    def test_rectangle_tool_teaches_area_and_perimeter(self):
        result = solve_calculation("rectangle", {"length": "5", "width": "3"})
        self.assertEqual(result.value, Decimal("15"))
        self.assertEqual(result.display_value, "15 square units")
        self.assertIn("Perimeter =", result.steps[1])

    def test_fraction_conversion_and_formatting(self):
        result = solve_calculation("fraction_percent", {"numerator": "3", "denominator": "8"})
        self.assertEqual(result.formatted_value, "37.5")
        self.assertEqual(format_number(Decimal("12.500")), "12.5")

    def test_invalid_inputs_produce_clear_errors(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            solve_calculation("percent_change", {"before": "0", "after": "10"})
        with self.assertRaisesRegex(ValueError, "denominator cannot be zero"):
            solve_calculation("fraction_percent", {"numerator": "3", "denominator": "0"})
        with self.assertRaisesRegex(ValueError, "at least two"):
            solve_calculation("average", {"numbers": "4"})

    def test_answers_allow_currency_commas_and_small_rounding(self):
        self.assertTrue(answer_matches("₹1,250", Decimal("1250")))
        self.assertTrue(answer_matches("150 km", Decimal("150")))
        self.assertTrue(answer_matches("60 km/h", Decimal("60")))
        self.assertTrue(answer_matches("37.51", Decimal("37.5")))
        self.assertFalse(answer_matches("37.6", Decimal("37.5")))
        self.assertFalse(answer_matches("not a number", Decimal("5")))

    def test_seeded_drills_are_reproducible_and_include_working(self):
        first = generate_math_drill(random.Random(214))
        second = generate_math_drill(random.Random(214))
        self.assertEqual(first, second)
        self.assertTrue(first.prompt)
        self.assertGreaterEqual(len(first.steps), 2)
        self.assertTrue(first.memory_tip)
        self.assertTrue(answer_matches(first.formatted_answer, first.answer))

    def test_many_generated_drills_have_valid_numeric_answers(self):
        rng = random.Random(7)
        for _ in range(200):
            drill = generate_math_drill(rng)
            self.assertGreaterEqual(drill.answer, 0)
            self.assertTrue(answer_matches(drill.formatted_answer, drill.answer), drill)
            self.assertTrue(answer_matches(drill.display_answer, drill.answer), drill)
            self.assertTrue(drill.steps)


if __name__ == "__main__":
    unittest.main()
