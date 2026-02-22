import { formatRelativeTime } from './formatRelativeTime';

export const formatRelativeDate = formatRelativeTime;

function ensureUtc(isoString: string): string {
  const s = isoString.trim();
  if (s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s)) return s;
  return s + 'Z';
}

export const formatDateTime = (isoString: string | null | undefined): string => {
  if (!isoString) return '';
  try {
    const normalized = ensureUtc(isoString);
    const dt = new Date(normalized);
    if (Number.isNaN(dt.getTime())) return isoString;
    return dt.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return isoString;
  }
};
