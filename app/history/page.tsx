"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { supabase } from "@/lib/supabase";
import GradeBadge from "@/components/GradeBadge";

const ScoreChart = dynamic(() => import("./ScoreChart"), { ssr: false });

type Ticker = { ticker: string; name: string };
type Point  = { date: string; signal_score: number | null; grade: string | null };

export default function HistoryPage() {
  const [tickers, setTickers]       = useState<Ticker[]>([]);
  const [selected, setSelected]     = useState<string>("");
  const [points, setPoints]         = useState<Point[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);

  // Load ticker list on mount
  useEffect(() => {
    async function loadTickers() {
      const { data: dateRow } = await supabase
        .from("snapshots")
        .select("date")
        .order("date", { ascending: false })
        .limit(1)
        .single();
      if (!dateRow) return;

      const { data } = await supabase
        .from("snapshots")
        .select("ticker, name")
        .eq("date", dateRow.date)
        .order("ticker");
      setTickers(data ?? []);
    }
    loadTickers();
  }, []);

  // Load history when ticker changes
  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setError(null);

    supabase
      .from("snapshots")
      .select("date, signal_score, grade")
      .eq("ticker", selected)
      .not("signal_score", "is", null)
      .order("date", { ascending: true })
      .limit(30)
      .then(({ data, error: err }) => {
        if (err) setError(err.message);
        else setPoints(data ?? []);
        setLoading(false);
      });
  }, [selected]);

  const currentGrade = points.at(-1)?.grade ?? null;
  const currentScore = points.at(-1)?.signal_score ?? null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-5">
        <h1 className="text-xl font-semibold">Score History</h1>
        {currentScore !== null && (
          <span className="flex items-center gap-2 text-sm text-gray-400">
            Score: <span className="text-white font-medium">{currentScore.toFixed(1)}</span>
            <GradeBadge grade={currentGrade} />
          </span>
        )}
      </div>

      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="mb-6 bg-gray-800 border border-gray-700 text-white rounded px-3 py-2 text-sm w-full sm:w-72 focus:outline-none focus:border-blue-500"
      >
        <option value="">Select a ticker…</option>
        {tickers.map((t) => (
          <option key={t.ticker} value={t.ticker}>
            {t.ticker} — {t.name}
          </option>
        ))}
      </select>

      {error && (
        <div className="rounded bg-red-900/40 border border-red-700 text-red-300 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {loading && <p className="text-gray-500 text-sm">Loading…</p>}

      {!loading && !error && selected && points.length === 0 && (
        <p className="text-gray-500 text-sm">No score history found for {selected}.</p>
      )}

      {!loading && !error && points.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <ScoreChart points={points} />
        </div>
      )}

      {!selected && (
        <p className="text-gray-600 text-sm">Pick a ticker to see its signal score over the last 30 days.</p>
      )}
    </div>
  );
}
