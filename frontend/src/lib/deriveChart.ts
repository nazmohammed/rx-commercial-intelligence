/**
 * Auto-detect a chartable shape from raw PBI rows.
 *
 * PBI returns rows where keys look like "Routes[OriginDestination]" or
 * "[Total Revenue]". We pick:
 *   - the first column whose values are mostly strings → label
 *   - the first column whose values are mostly numbers → value
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

  const labelCol = scores.find((s) => s.stringy > s.numeric);
  const valueCol = scores.find((s) => s.numeric > 0 && s.numeric >= s.stringy);

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
