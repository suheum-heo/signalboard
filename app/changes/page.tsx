export const dynamic = "force-dynamic";

import { supabase } from "@/lib/supabase";
import GradeBadge from "@/components/GradeBadge";

type SnapshotRow = { ticker: string; name: string; signal_score: number | null; grade: string | null };
type GradeRow    = { ticker: string; grade: string | null };

type Change = SnapshotRow & { old_grade: string | null };

const GRADE_ORDER: Record<string, number> = { S: 5, A: 4, B: 3, C: 2, D: 1 };
const direction = (from: string | null, to: string | null) =>
  (GRADE_ORDER[to ?? ""] ?? 0) > (GRADE_ORDER[from ?? ""] ?? 0) ? "up" : "down";

async function getLastTwoDates(): Promise<[string, string] | null> {
  const { data } = await supabase
    .from("snapshots")
    .select("date")
    .eq("ticker", "005930") // anchor on Samsung to find available dates
    .order("date", { ascending: false })
    .limit(2);
  if (!data || data.length < 2) return null;
  return [data[0].date, data[1].date]; // [latest, previous]
}

async function getChanges(): Promise<{ changes: Change[]; today: string; yesterday: string } | null> {
  const dates = await getLastTwoDates();
  if (!dates) return null;
  const [today, yesterday] = dates;

  const [todayResp, yesterdayResp] = await Promise.all([
    supabase
      .from("snapshots")
      .select("ticker, name, signal_score, grade")
      .eq("date", today)
      .not("grade", "is", null),
    supabase
      .from("snapshots")
      .select("ticker, grade")
      .eq("date", yesterday)
      .not("grade", "is", null),
  ]);

  const todayRows: SnapshotRow[]  = todayResp.data ?? [];
  const prevMap = new Map<string, string | null>(
    (yesterdayResp.data as GradeRow[] ?? []).map((r) => [r.ticker, r.grade])
  );

  const changes: Change[] = todayRows
    .filter((r) => prevMap.has(r.ticker) && prevMap.get(r.ticker) !== r.grade)
    .map((r) => ({ ...r, old_grade: prevMap.get(r.ticker) ?? null }))
    .sort((a, b) => (b.signal_score ?? 0) - (a.signal_score ?? 0));

  return { changes, today, yesterday };
}

export default async function ChangesPage() {
  let result: Awaited<ReturnType<typeof getChanges>> = null;
  let errorMsg: string | null = null;

  try {
    result = await getChanges();
  } catch (e) {
    errorMsg = e instanceof Error ? e.message : "Failed to load data";
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5">
        <h1 className="text-xl font-semibold">Grade Changes</h1>
        {result && (
          <span className="text-sm text-gray-500">
            {result.yesterday} → {result.today}
          </span>
        )}
      </div>

      {errorMsg && (
        <div className="rounded bg-red-900/40 border border-red-700 text-red-300 px-4 py-3 text-sm">
          {errorMsg}
        </div>
      )}

      {!errorMsg && !result && (
        <p className="text-gray-500 text-sm">Need at least 2 days of scored data.</p>
      )}

      {result && result.changes.length === 0 && (
        <p className="text-gray-500 text-sm">No grade changes between {result.yesterday} and {result.today}.</p>
      )}

      {result && result.changes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800 text-left">
                <th className="pb-2 pr-4 font-medium">Ticker</th>
                <th className="pb-2 pr-4 font-medium">Name</th>
                <th className="pb-2 pr-4 font-medium">Change</th>
                <th className="pb-2 font-medium text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {result.changes.map((row) => {
                const dir = direction(row.old_grade, row.grade);
                return (
                  <tr
                    key={row.ticker}
                    className="border-b border-gray-800/50 hover:bg-gray-900/50 transition-colors"
                  >
                    <td className="py-2.5 pr-4 font-mono text-gray-300">{row.ticker}</td>
                    <td className="py-2.5 pr-4 text-white">{row.name}</td>
                    <td className="py-2.5 pr-4">
                      <span className="flex items-center gap-2">
                        <GradeBadge grade={row.old_grade} />
                        <span className={`text-xs font-bold ${dir === "up" ? "text-green-400" : "text-red-400"}`}>
                          {dir === "up" ? "▲" : "▼"}
                        </span>
                        <GradeBadge grade={row.grade} />
                      </span>
                    </td>
                    <td className="py-2.5 text-right tabular-nums font-medium">
                      {row.signal_score?.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
