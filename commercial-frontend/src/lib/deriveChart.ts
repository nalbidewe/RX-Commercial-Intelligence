/**
 * Auto-detect a chartable shape from raw PBI rows.
 *
 * PBI returns rows where keys look like "Routes[OriginDestination]" or
 * "[Total Revenue]". We pick:
 *   - the first column whose values are mostly strings → label
 *   - the best numeric column → value, chosen by:
 *       1. must have varying values (skip Year=2026, Year=2026, Year=2026)
 *       2. must not look like a calendar dimension (year 1900-2100, month/day 1-31)
 *       3. among survivors, prefer the highest average absolute value (revenue >> count)
 *       4. fall back progressively if no ideal candidate exists
 *
 * Returns null if no usable pair is found, in which case the UI falls back
 * to just showing the Adaptive Card (no chart).
 */

export interface ChartPoint {
  label: string;
  value: number;
  raw: Record<string, unknown>;
}

export interface DerivedChart {
  labelKey: string;
  valueKey: string;
  points: ChartPoint[];
  /** Friendly column names (with table prefix and brackets stripped). */
  labelName: string;
  valueName: string;
}

const MAX_POINTS = 20;

function prettyColumn(raw: string): string {
  // "Routes[OriginDestination]" → "OriginDestination"
  // "[Total Revenue]"           → "Total Revenue"
  const m = raw.match(/\[([^\]]+)\]\s*$/);
  return m ? m[1] : raw;
}

function isNumberLike(v: unknown): boolean {
  if (typeof v === 'number' && Number.isFinite(v)) return true;
  if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return true;
  return false;
}

function toNumber(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') return Number(v);
  return NaN;
}

/** True if every value looks like a calendar year (integer 1900–2100). */
function isYearLike(vals: number[]): boolean {
  return vals.length > 0 && vals.every((v) => Number.isInteger(v) && v >= 1900 && v <= 2100);
}

/**
 * True if every value looks like a small date-part integer:
 * month (1-12), day (1-31), quarter (1-4).
 * Guards against month-number columns being picked as a measure.
 */
function isDatePartLike(vals: number[]): boolean {
  return vals.length > 0 && vals.every((v) => Number.isInteger(v) && v >= 1 && v <= 31);
}

function avgAbs(vals: number[]): number {
  if (vals.length === 0) return 0;
  return vals.reduce((s, v) => s + Math.abs(v), 0) / vals.length;
}

/**
 * Coefficient of variation: stddev / |mean|.
 * High CV → values genuinely differ across rows (per-cabin revenue).
 * Low CV  → same value repeated (route total repeated on every cabin row).
 */
function coefficientOfVariation(vals: number[]): number {
  if (vals.length === 0) return 0;
  const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
  const absMean = Math.abs(mean);
  if (absMean === 0) return 0;
  const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length;
  return Math.sqrt(variance) / absMean;
}

/**
 * Pick the best value column from numeric candidates.
 *
 * Priority:
 *   1. Varying + not a calendar dimension → sorted by highest coefficient of
 *      variation, tiebroken by highest avg absolute value.
 *      CV prefers the column that actually differentiates the bars (e.g.
 *      per-cabin revenue) over a repeated aggregate total that has near-zero
 *      variation across rows.
 *   2. Varying (even if year/date-part) → same CV sort
 *   3. First candidate regardless (last-resort fallback)
 */
function pickValueCol(
  candidates: { key: string; numeric: number; stringy: number }[],
  sample: Record<string, unknown>[]
): { key: string; numeric: number; stringy: number } | undefined {
  if (candidates.length === 0) return undefined;

  const annotated = candidates.map((c) => ({
    col: c,
    vals: sample.map((r) => toNumber(r[c.key])).filter(Number.isFinite),
  }));

  // Step 1: columns where values actually differ across rows
  const varying = annotated.filter((a) => new Set(a.vals).size > 1);

  // Step 2: exclude calendar dimension columns (year, month, day, quarter)
  const measures = varying.filter(
    (a) => !isYearLike(a.vals) && !isDatePartLike(a.vals)
  );

  // Step 3: sort by CV descending — column that varies most across rows wins.
  // Tiebreak with avgAbs so revenue (millions) beats counts (tens) when CVs match.
  const pool = measures.length > 0 ? measures : varying.length > 0 ? varying : annotated;
  const sorted = [...pool].sort(
    (a, b) =>
      coefficientOfVariation(b.vals) - coefficientOfVariation(a.vals) ||
      avgAbs(b.vals) - avgAbs(a.vals)
  );

  return sorted[0]?.col;
}

export function deriveChart(
  rows: Record<string, unknown>[] | undefined | null
): DerivedChart | null {
  if (!rows || rows.length === 0) return null;

  const sample = rows.slice(0, Math.min(rows.length, 10));
  const keys = Array.from(
    new Set(sample.flatMap((r) => Object.keys(r)))
  );
  if (keys.length === 0) return null;

  // Score each column: how many sampled values are numeric vs string-y
  const scores = keys.map((k) => {
    let numeric = 0;
    let stringy = 0;
    for (const row of sample) {
      const v = row[k];
      if (v === null || v === undefined || v === '') continue;
      if (isNumberLike(v) && typeof v !== 'boolean') numeric++;
      else if (typeof v === 'string') stringy++;
    }
    return { key: k, numeric, stringy };
  });

  // Pick the string column with the most distinct values — avoids picking a
  // low-cardinality dimension (e.g. a single repeated route) over a richer one
  // (e.g. cabin class with Business / Economy / Premium Economy).
  const stringCandidates = scores.filter((s) => s.stringy > s.numeric);
  const labelCol = stringCandidates.length === 0
    ? undefined
    : stringCandidates
        .map((s) => ({
          ...s,
          uniqueCount: new Set(sample.map((r) => String(r[s.key] ?? ''))).size,
        }))
        .sort((a, b) => b.uniqueCount - a.uniqueCount || b.stringy - a.stringy)[0];

  const numericCandidates = scores.filter(
    (s) => s.numeric > 0 && s.numeric >= s.stringy
  );
  const valueCol = pickValueCol(numericCandidates, sample);

  if (!labelCol || !valueCol || labelCol.key === valueCol.key) return null;

  const points: ChartPoint[] = [];
  for (const row of rows.slice(0, MAX_POINTS)) {
    const label = String(row[labelCol.key] ?? '');
    const value = toNumber(row[valueCol.key]);
    if (label && Number.isFinite(value)) {
      points.push({ label, value, raw: row });
    }
  }

  if (points.length < 2) return null;

  return {
    labelKey: labelCol.key,
    valueKey: valueCol.key,
    points,
    labelName: prettyColumn(labelCol.key),
    valueName: prettyColumn(valueCol.key),
  };
}
