export const MATH_CALCULATORS = {
  percent_of: {
    title: "Percentage of a number",
    fields: [{ id: "rate", label: "Percentage (%)", placeholder: "15" }, { id: "number", label: "Number", placeholder: "240" }],
  },
  percent_change: {
    title: "Percentage increase or decrease",
    fields: [{ id: "before", label: "Original value", placeholder: "80" }, { id: "after", label: "New value", placeholder: "100" }],
  },
  average: {
    title: "Average",
    fields: [{ id: "numbers", label: "Numbers (comma or space separated)", placeholder: "12, 18, 20, 30", type: "text" }],
  },
  ratio_share: {
    title: "Share an amount by ratio",
    fields: [
      { id: "partA", label: "First ratio part", placeholder: "2" },
      { id: "partB", label: "Second ratio part", placeholder: "3" },
      { id: "total", label: "Total amount", placeholder: "500" },
      { id: "which", label: "Which share?", type: "select", options: [["A", "First share"], ["B", "Second share"]] },
    ],
  },
  simple_interest: {
    title: "Simple interest",
    fields: [{ id: "principal", label: "Principal (P)", placeholder: "5000" }, { id: "rate", label: "Annual rate (%)", placeholder: "8" }, { id: "years", label: "Time (years)", placeholder: "2" }],
  },
  profit_loss: {
    title: "Profit or loss percentage",
    fields: [{ id: "cost", label: "Cost price", placeholder: "800" }, { id: "selling", label: "Selling price", placeholder: "920" }],
  },
  speed_distance_time: {
    title: "Speed, distance and time",
    target: true,
    fields: [{ id: "distance", label: "Distance (km)", placeholder: "150" }, { id: "speed", label: "Speed (km/h)", placeholder: "60" }, { id: "time", label: "Time (hours)", placeholder: "2.5" }],
  },
  time_work: {
    title: "Time and work together",
    fields: [{ id: "daysA", label: "Worker A days alone", placeholder: "12" }, { id: "daysB", label: "Worker B days alone", placeholder: "18" }],
  },
  discount_price: {
    title: "Discount and sale price",
    fields: [{ id: "markedPrice", label: "Marked price", placeholder: "1200" }, { id: "discountRate", label: "Discount (%)", placeholder: "15" }],
  },
  hcf_lcm: {
    title: "HCF and LCM",
    fields: [{ id: "first", label: "First whole number", placeholder: "24" }, { id: "second", label: "Second whole number", placeholder: "36" }],
  },
  rectangle: {
    title: "Rectangle area and perimeter",
    fields: [{ id: "length", label: "Length", placeholder: "12" }, { id: "width", label: "Width", placeholder: "7" }],
  },
  fraction_percent: {
    title: "Fraction to percentage",
    fields: [{ id: "numerator", label: "Numerator", placeholder: "3" }, { id: "denominator", label: "Denominator", placeholder: "8" }],
  },
};

export function formatMathNumber(value) {
  if (!Number.isFinite(Number(value))) return String(value);
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function readNumber(raw, label) {
  const cleaned = String(raw ?? "").replaceAll(",", "").replace(/\s*(₹|rs\.?|km\/h|km|hours?|days?)\s*/gi, "").trim();
  const value = Number(cleaned);
  if (!cleaned || !Number.isFinite(value)) throw new Error(`${label} needs a valid number.`);
  return value;
}

function nonnegative(value, label) {
  if (value < 0) throw new Error(`${label} cannot be negative.`);
  return value;
}

function positive(value, label) {
  if (value <= 0) throw new Error(`${label} must be greater than zero.`);
  return value;
}

function result(title, value, unit, steps, memory) {
  return { title, value: formatMathNumber(value), unit, steps, memory };
}

export function solveMath(kind, input) {
  if (!Object.hasOwn(MATH_CALCULATORS, kind)) throw new Error("Choose a calculator from the list.");
  const n = (key, label = key) => readNumber(input[key], label);
  switch (kind) {
    case "percent_of": {
      const rate = nonnegative(n("rate", "Percentage"), "Percentage");
      const number = n("number", "Number");
      const answer = rate * number / 100;
      return result(`${rate}% of ${formatMathNumber(number)} =`, answer, "", [`10% of ${formatMathNumber(number)} = ${formatMathNumber(number / 10)}.`, `1% = ${formatMathNumber(number / 100)}; ${rate}% = ${formatMathNumber(answer)}.`], "10% is one-tenth; 5% is half of 10%; 1% is one-hundredth.");
    }
    case "percent_change": {
      const before = n("before", "Original value");
      const after = n("after", "New value");
      if (before === 0) throw new Error("The original value must not be zero for percentage change.");
      const change = after - before;
      const percentage = change / Math.abs(before) * 100;
      const direction = change > 0 ? "increase" : change < 0 ? "decrease" : "no change";
      return result(`${direction[0].toUpperCase()}${direction.slice(1)} =`, Math.abs(percentage), "%", [`Change = ${formatMathNumber(after)} − ${formatMathNumber(before)} = ${formatMathNumber(change)}.`, `Percentage change = (change ÷ original value) × 100 = ${formatMathNumber(percentage)}%.`], "Always divide by the original value—not the new value.");
    }
    case "average": {
      const values = String(input.numbers || "").split(/[\s,;]+/).filter(Boolean).map((item) => readNumber(item, "Each value"));
      if (values.length < 2 || values.length > 100) throw new Error("Enter between 2 and 100 comma- or space-separated numbers.");
      const sum = values.reduce((total, value) => total + value, 0);
      const mean = sum / values.length;
      return result("Average =", mean, "", [`Add: ${values.map(formatMathNumber).join(" + ")} = ${formatMathNumber(sum)}.`, `Divide by the ${values.length} values: ${formatMathNumber(sum)} ÷ ${values.length} = ${formatMathNumber(mean)}.`], "Average × count = total; total ÷ count = average.");
    }
    case "ratio_share": {
      const first = positive(n("partA", "First ratio part"), "First ratio part");
      const second = positive(n("partB", "Second ratio part"), "Second ratio part");
      const total = n("total", "Total amount");
      const which = input.which === "B" ? second : first;
      const share = total * which / (first + second);
      return result(`Share ${formatMathNumber(which)} part${which === 1 ? "" : "s"} =`, share, "", [`Total ratio parts = ${first} + ${second} = ${first + second}.`, `One part = ${formatMathNumber(total)} ÷ ${first + second} = ${formatMathNumber(total / (first + second))}.`, `Multiply by ${which}: share = ${formatMathNumber(share)}.`], "Add the parts, find one part, then multiply by the part you need.");
    }
    case "simple_interest": {
      const principal = nonnegative(n("principal", "Principal"), "Principal");
      const rate = nonnegative(n("rate", "Rate"), "Rate");
      const years = nonnegative(n("years", "Time"), "Time");
      const interest = principal * rate * years / 100;
      return result("Simple interest =", interest, "", [`SI = P × R × T ÷ 100.`, `SI = ${formatMathNumber(principal)} × ${rate} × ${years} ÷ 100 = ${formatMathNumber(interest)}.`, `Total amount = principal + interest = ${formatMathNumber(principal + interest)}.`], "P-R-T, then divide by 100.");
    }
    case "profit_loss": {
      const cost = positive(n("cost", "Cost price"), "Cost price");
      const selling = nonnegative(n("selling", "Selling price"), "Selling price");
      const difference = selling - cost;
      const percentage = Math.abs(difference) / cost * 100;
      const label = difference > 0 ? "Profit" : difference < 0 ? "Loss" : "Break-even";
      const value = difference === 0 ? 0 : percentage;
      return result(`${label} percentage =`, value, "%", [`Difference = selling price − cost price = ${formatMathNumber(difference)}.`, `${label} % = (absolute difference ÷ cost price) × 100 = ${formatMathNumber(value)}%.`], "Profit or loss percentage uses cost price as the base.");
    }
    case "speed_distance_time": {
      const target = ["distance", "speed", "time"].includes(input.target) ? input.target : "distance";
      const units = { distance: "km", speed: "km/h", time: "hours" };
      const values = {};
      for (const key of ["distance", "speed", "time"]) {
        if (key === target) continue;
        values[key] = nonnegative(n(key, units[key]), units[key]);
      }
      let value;
      let formula;
      if (target === "distance") {
        value = values.speed * values.time;
        formula = `Distance = speed × time = ${formatMathNumber(values.speed)} × ${formatMathNumber(values.time)}.`;
      } else if (target === "speed") {
        value = values.distance / positive(values.time, "Time");
        formula = `Speed = distance ÷ time = ${formatMathNumber(values.distance)} ÷ ${formatMathNumber(values.time)}.`;
      } else {
        value = values.distance / positive(values.speed, "Speed");
        formula = `Time = distance ÷ speed = ${formatMathNumber(values.distance)} ÷ ${formatMathNumber(values.speed)}.`;
      }
      return result(`${target[0].toUpperCase()}${target.slice(1)} =`, value, units[target], ["Remember: distance = speed × time.", formula], "D-S-T: multiply to find distance; divide to find speed or time.");
    }
    case "time_work": {
      const daysA = positive(n("daysA", "Worker A days"), "Worker A days");
      const daysB = positive(n("daysB", "Worker B days"), "Worker B days");
      const combinedRate = 1 / daysA + 1 / daysB;
      const days = 1 / combinedRate;
      return result("Together they finish in", days, "days", [`A's one-day work = 1/${formatMathNumber(daysA)}.`, `B's one-day work = 1/${formatMathNumber(daysB)}.`, `Combined rate = ${formatMathNumber(combinedRate)} of the job per day; time = 1 ÷ rate = ${formatMathNumber(days)} days.`], "Add the workers' daily rates, then take 1 ÷ the combined rate.");
    }
    case "discount_price": {
      const marked = nonnegative(n("markedPrice", "Marked price"), "Marked price");
      const rate = nonnegative(n("discountRate", "Discount rate"), "Discount rate");
      if (rate > 100) throw new Error("Discount cannot be more than 100%.");
      const discount = marked * rate / 100;
      return result("Sale price =", marked - discount, "", [`Discount = ${rate}% of ${formatMathNumber(marked)} = ${formatMathNumber(discount)}.`, `Sale price = marked price − discount = ${formatMathNumber(marked)} − ${formatMathNumber(discount)} = ${formatMathNumber(marked - discount)}.`], "First find the discount; subtract it from the marked price.");
    }
    case "hcf_lcm": {
      const first = positive(n("first", "First number"), "First number");
      const second = positive(n("second", "Second number"), "Second number");
      if (!Number.isInteger(first) || !Number.isInteger(second)) throw new Error("HCF and LCM use whole numbers.");
      let a = first; let b = second;
      while (b) [a, b] = [b, a % b];
      const hcf = a;
      const lcm = first / hcf * second;
      return result("HCF / LCM =", `${hcf} / ${lcm}`, "", [`Use Euclid's method: repeatedly divide and keep the remainder. HCF(${first}, ${second}) = ${hcf}.`, `LCM × HCF = first number × second number. LCM = ${first} × ${second} ÷ ${hcf} = ${lcm}.`], "For two positive integers: HCF × LCM = their product.");
    }
    case "rectangle": {
      const length = nonnegative(n("length", "Length"), "Length");
      const width = nonnegative(n("width", "Width"), "Width");
      const area = length * width;
      const perimeter = 2 * (length + width);
      return result("Area / perimeter =", `${formatMathNumber(area)} / ${formatMathNumber(perimeter)}`, "", [`Area = length × width = ${formatMathNumber(length)} × ${formatMathNumber(width)} = ${formatMathNumber(area)} square units.`, `Perimeter = 2 × (length + width) = 2 × (${formatMathNumber(length)} + ${formatMathNumber(width)}) = ${formatMathNumber(perimeter)} units.`], "Area covers the inside (square units); perimeter measures the boundary (units).");
    }
    case "fraction_percent": {
      const numerator = n("numerator", "Numerator");
      const denominator = positive(n("denominator", "Denominator"), "Denominator");
      const decimal = numerator / denominator;
      const percentage = decimal * 100;
      return result("Fraction as a percentage =", percentage, "%", [`Divide: ${formatMathNumber(numerator)} ÷ ${formatMathNumber(denominator)} = ${formatMathNumber(decimal)}.`, `Multiply the decimal by 100: ${formatMathNumber(decimal)} × 100 = ${formatMathNumber(percentage)}%.`], "Fraction → decimal → percentage: divide first, then multiply by 100.");
    }
    default:
      throw new Error("That calculator is not available.");
  }
}

export function generateMathDrill(random = Math.random) {
  const templates = [
    () => {
      const rate = [5, 10, 15, 20, 25][Math.floor(random() * 5)];
      const number = (Math.floor(random() * 18) + 2) * 100;
      const answer = rate * number / 100;
      return { prompt: `What is ${rate}% of ${number}?`, answer, steps: [`10% of ${number} = ${number / 10}.`, `${rate}% = ${answer}.`], memory: "10% is one-tenth; halve it for 5%, or scale it for other percentages." };
    },
    () => {
      const a = Math.floor(random() * 8) + 2;
      const b = Math.floor(random() * 8) + 2;
      const answer = 1 / (1 / a + 1 / b);
      return { prompt: `A can finish in ${a} days and B in ${b} days. How many days together?`, answer, steps: [`Add rates: 1/${a} + 1/${b} = ${(a + b)}/${a * b} of the work per day.`, `Time = 1 ÷ combined rate = ${formatMathNumber(answer)} days.`], memory: "Add daily work rates first; invert the combined rate to get days." };
    },
    () => {
      const a = Math.floor(random() * 40) + 10;
      const b = Math.floor(random() * 40) + 10;
      const c = Math.floor(random() * 40) + 10;
      const answer = (a + b + c) / 3;
      return { prompt: `Find the average of ${a}, ${b} and ${c}.`, answer, steps: [`Total = ${a} + ${b} + ${c} = ${a + b + c}.`, `Average = total ÷ count = ${a + b + c} ÷ 3 = ${formatMathNumber(answer)}.`], memory: "Average × count = total; total ÷ count = average." };
    },
    () => {
      const p = (Math.floor(random() * 9) + 2) * 1000;
      const r = [5, 8, 10, 12][Math.floor(random() * 4)];
      const t = Math.floor(random() * 4) + 1;
      const answer = p * r * t / 100;
      return { prompt: `Simple interest on ₹${p} at ${r}% for ${t} years?`, answer, steps: [`SI = P × R × T ÷ 100.`, `SI = ${p} × ${r} × ${t} ÷ 100 = ₹${formatMathNumber(answer)}.`], memory: "P-R-T, then divide by 100." };
    },
  ];
  const chosen = templates[Math.floor(random() * templates.length)]();
  return { ...chosen, answer: Number(chosen.answer), tolerance: 0.011 };
}

export function mathAnswerMatches(raw, expected, tolerance = 0.011) {
  const cleaned = String(raw ?? "").replace(/[₹,%\s,]/g, "").trim();
  if (!cleaned) return false;
  const value = Number(cleaned);
  return Number.isFinite(value) && Math.abs(value - expected) <= Math.max(tolerance, Math.abs(expected) * 0.0001);
}
