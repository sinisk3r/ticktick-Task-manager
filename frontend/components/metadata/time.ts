export function formatMinutes(minutes?: number | null): string {
  if (minutes === undefined || minutes === null) return "—"
  const total = Math.max(0, Math.floor(minutes))
  const hours = Math.floor(total / 60)
  const mins = total % 60

  const parts = []
  if (hours) parts.push(`${hours}h`)
  if (mins) parts.push(`${mins}m`)
  if (!parts.length) return "0m"
  return parts.join(" ")
}

