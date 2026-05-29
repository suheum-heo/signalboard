export const dynamic = "force-dynamic";

import { supabase } from "@/lib/supabase";
import GradeBadge from "@/components/GradeBadge";

type Row = {
  ticker: string;
  name: string;
  sector: string | null;
  close: number;
  signal_score: number | null;
  grade: string | null;
};

async function getLatestDate(): Promise<string | null> {
  const { data } = await supabase
    .from("snapshots")
    .select("date")
    .order("date", { ascending: false })
    .limit(1)
    .single();
  return data?.date ?? null;
}

async function getRadar(date: string): Promise<Row[]> {
  const { data, error } = await supabase
    .from("snapshots")
    .select("ticker, name, sector, close, signal_score, grade")
    .eq("date", date)
    .not("signal_score", "is", null)
    .order("signal_score", { ascending: false })
    .limit(20);
  if (error) throw error;
  return data ?? [];
}

export default async function RadarPage() {
  let date: string | null = null;
  let rows: Row[] = [];
  let errorMsg: string | null = null;

  try {
    date = await getLatestDate();
    if (date) rows = await getRadar(date);
  } catch (e) {
    errorMsg = e instanceof Error ? e.message : "Failed to load data";
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5">
        <h1 className="text-xl font-semibold">Today&apos;s Radar</h1>
        {date && <span className="text-sm text-gray-500">{date}</span>}
      </div>

      {errorMsg && (
        <div className="rounded bg-red-900/40 border border-red-700 text-red-300 px-4 py-3 text-sm">
          {errorMsg}
        </div>
      )}

      {!errorMsg && rows.length === 0 && (
        <p className="text-gray-500 text-sm">No scored data yet — run snapshot.py + score.py first.</p>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800 text-left">
                <th className="pb-2 pr-4 font-medium w-8">#</th>
                <th className="pb-2 pr-4 font-medium">Ticker</th>
                <th className="pb-2 pr-4 font-medium">Name</th>
                <th className="pb-2 pr-4 font-medium hidden sm:table-cell">Sector</th>
                <th className="pb-2 pr-4 font-medium text-right">Close (₩)</th>
                <th className="pb-2 pr-4 font-medium text-right">Score</th>
                <th className="pb-2 font-medium text-center">Grade</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={row.ticker}
                  className="border-b border-gray-800/50 hover:bg-gray-900/50 transition-colors"
                >
                  <td className="py-2.5 pr-4 text-gray-500">{i + 1}</td>
                  <td className="py-2.5 pr-4 font-mono text-gray-300">{row.ticker}</td>
                  <td className="py-2.5 pr-4 text-white">{row.name}</td>
                  <td className="py-2.5 pr-4 text-gray-400 hidden sm:table-cell">{row.sector ?? "—"}</td>
                  <td className="py-2.5 pr-4 text-right tabular-nums">
                    {row.close.toLocaleString("ko-KR")}
                  </td>
                  <td className="py-2.5 pr-4 text-right tabular-nums font-medium">
                    {row.signal_score?.toFixed(1)}
                  </td>
                  <td className="py-2.5 text-center">
                    <GradeBadge grade={row.grade} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
