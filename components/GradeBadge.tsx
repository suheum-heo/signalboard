const styles: Record<string, string> = {
  S: "bg-purple-500 text-white",
  A: "bg-green-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-yellow-400 text-black",
  D: "bg-red-500 text-white",
};

export default function GradeBadge({ grade }: { grade: string | null }) {
  if (!grade) return <span className="text-gray-500">—</span>;
  return (
    <span
      className={`inline-block w-7 text-center rounded font-bold text-sm py-0.5 ${styles[grade] ?? "bg-gray-600 text-white"}`}
    >
      {grade}
    </span>
  );
}
