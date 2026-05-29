"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

type Point = { date: string; signal_score: number | null };

export default function ScoreChart({ points }: { points: Point[] }) {
  const labels = points.map((p) => p.date.slice(5)); // MM-DD
  const scores = points.map((p) => p.signal_score ?? null);

  const data = {
    labels,
    datasets: [
      {
        label: "Signal Score",
        data: scores,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.15)",
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: { color: "#9ca3af" },
        grid: { color: "#1f2937" },
      },
      x: {
        ticks: { color: "#9ca3af", maxTicksLimit: 10 },
        grid: { color: "#1f2937" },
      },
    },
  };

  return <Line data={data} options={options} />;
}
