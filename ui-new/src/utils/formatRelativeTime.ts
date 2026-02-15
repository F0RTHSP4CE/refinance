/** Treat API timestamps without timezone as UTC (backend stores UTC). */
function ensureUtc(isoString: string): string {
  const s = isoString.trim();
  if (s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s)) return s;
  return s + 'Z';
}

export const formatRelativeTime = (dateString: string | null | undefined): string => {
  if (!dateString) return '';

  try {
    const normalized = ensureUtc(dateString);
    const dt = new Date(normalized);
    if (Number.isNaN(dt.getTime())) return dateString;

    const now = new Date();
    const diffMs = now.getTime() - dt.getTime();
    const seconds = diffMs / 1000;
    const minutes = seconds / 60;
    const hours = minutes / 60;
    const days = hours / 24;
    const weeks = days / 7;
    const months = days / 30.44;

    if (seconds < 60) return 'just now';
    if (minutes < 60) return `${Math.floor(minutes)} min${Math.floor(minutes) !== 1 ? 's' : ''} ago`;
    if (hours < 24) return `${Math.floor(hours)} hour${Math.floor(hours) !== 1 ? 's' : ''} ago`;
    if (days < 2) return 'yesterday';
    if (days < 7) return `${Math.floor(days)} day${Math.floor(days) !== 1 ? 's' : ''} ago`;
    if (weeks < 4) return `${Math.floor(weeks)} week${Math.floor(weeks) !== 1 ? 's' : ''} ago`;
    if (months < 6) return `${Math.floor(months)} month${Math.floor(months) !== 1 ? 's' : ''} ago`;

    if (dt.getFullYear() === now.getFullYear()) {
      return dt.toLocaleDateString(undefined, { day: 'numeric', month: 'long' });
    }
    return dt.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return dateString;
  }
};
