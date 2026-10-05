import test from "node:test";
import assert from "node:assert/strict";
import { MATH_CALCULATORS, generateMathDrill, mathAnswerMatches, solveMath } from "../js/math.js";

test("Math Lab exposes all twelve guided calculators", () => {
  assert.equal(Object.keys(MATH_CALCULATORS).length, 12);
});

test("percentage, average and ratio solutions explain their steps", () => {
  const percent = solveMath("percent_of", { rate: "15", number: "240" });
  assert.equal(percent.value, "36");
  assert.match(percent.steps[1], /36/);
  const average = solveMath("average", { numbers: "12, 18, 30" });
  assert.equal(average.value, "20");
  const ratio = solveMath("ratio_share", { partA: "2", partB: "3", total: "500", which: "B" });
  assert.equal(ratio.value, "300");
});

test("interest, profit, discount and speed-distance-time formulas are correct", () => {
  assert.equal(solveMath("simple_interest", { principal: "5000", rate: "8", years: "2" }).value, "800");
  assert.equal(solveMath("profit_loss", { cost: "800", selling: "920" }).value, "15");
  assert.equal(solveMath("discount_price", { markedPrice: "1200", discountRate: "15" }).value, "1,020");
  assert.equal(solveMath("speed_distance_time", { target: "distance", speed: "60", time: "2.5" }).value, "150");
  assert.equal(solveMath("speed_distance_time", { target: "speed", distance: "150", time: "2.5" }).value, "60");
  assert.equal(solveMath("speed_distance_time", { target: "time", distance: "150", speed: "60" }).value, "2.5");
});

test("time-work, HCF/LCM, rectangle and fraction tools give transparent answers", () => {
  assert.equal(solveMath("time_work", { daysA: "12", daysB: "18" }).value, "7.2");
  assert.equal(solveMath("hcf_lcm", { first: "24", second: "36" }).value, "12 / 72");
  assert.equal(solveMath("rectangle", { length: "12", width: "7" }).value, "84 / 38");
  assert.equal(solveMath("fraction_percent", { numerator: "3", denominator: "8" }).value, "37.5");
});

test("invalid divisions, non-integers and out-of-range inputs are explained", () => {
  assert.throws(() => solveMath("speed_distance_time", { target: "speed", distance: "20", time: "0" }), /greater than zero/i);
  assert.throws(() => solveMath("hcf_lcm", { first: "3.5", second: "6" }), /whole numbers/i);
  assert.throws(() => solveMath("discount_price", { markedPrice: "100", discountRate: "110" }), /more than 100/i);
  assert.throws(() => solveMath("average", { numbers: "hello, 2" }), /valid number/i);
});

test("fresh mental-maths drills use worked steps and tolerant numeric answers", () => {
  for (let index = 0; index < 40; index += 1) {
    const drill = generateMathDrill();
    assert.equal(typeof drill.prompt, "string");
    assert.equal(drill.steps.length >= 2, true);
    assert.equal(mathAnswerMatches(String(drill.answer), drill.answer), true);
    assert.equal(mathAnswerMatches("", drill.answer), false);
  }
  assert.equal(mathAnswerMatches("₹1,020", 1020), true);
  assert.equal(mathAnswerMatches("12", 12.5, 0.01), false);
});
