"use client";

interface QuadrantPickerProps {
  onSelect: (quadrant: string) => void;
  onCancel: () => void;
}

export function QuadrantPicker({ onSelect, onCancel }: QuadrantPickerProps) {
  const quadrants = [
    { id: "Q1", label: "Q1: Urgent & Important", color: "red" },
    { id: "Q2", label: "Q2: Important, Not Urgent", color: "blue" },
    { id: "Q3", label: "Q3: Urgent, Not Important", color: "yellow" },
    { id: "Q4", label: "Q4: Neither", color: "gray" },
  ];

  const colorClasses = {
    red: "bg-red-600 hover:bg-red-700 text-white",
    blue: "bg-blue-600 hover:bg-blue-700 text-white",
    yellow: "bg-yellow-600 hover:bg-yellow-700 text-white",
    gray: "bg-gray-600 hover:bg-gray-700 text-white",
  };

  return (
    <div className="mt-3 p-3 bg-popover rounded border border-border shadow-md">
      <p className="text-sm text-muted-foreground mb-2">Select quadrant:</p>
      <div className="grid grid-cols-2 gap-2 mb-2">
        {quadrants.map((q) => (
          <button
            key={q.id}
            onClick={() => onSelect(q.id)}
            className={`px-3 py-2 text-sm rounded transition-colors ${colorClasses[q.color as keyof typeof colorClasses]
              }`}
          >
            {q.label}
          </button>
        ))}
      </div>
      <button
        onClick={onCancel}
        className="w-full px-3 py-1.5 bg-secondary text-secondary-foreground text-sm rounded hover:bg-secondary/80 transition-colors"
      >
        Cancel
      </button>
    </div>
  );
}
