/** Форматування значень для інтерфейсу. */

export function formatDuration(seconds) {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  const padded = String(rest).padStart(2, '0');

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${padded}`;
  }
  return `${minutes}:${padded}`;
}

export function formatPace(distanceKm, durationSec) {
  if (!distanceKm) {
    return '—';
  }
  const paceSec = Math.round(durationSec / distanceKm);
  const minutes = Math.floor(paceSec / 60);
  const seconds = String(paceSec % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export function shortDate(isoDate) {
  const date = new Date(isoDate);
  return `${date.getDate()}.${date.getMonth() + 1}`;
}
