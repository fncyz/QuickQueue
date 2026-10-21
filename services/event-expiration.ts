type EventDated = { event_end_date?: string | null };
type TemporaryChoice = EventDated & { is_temporary?: boolean };
type TemporaryListing = EventDated & { status?: string };

export const manilaDateKey = (now = new Date()) => {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Manila', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
};

export const eventHasExpired = (item: EventDated, today = manilaDateKey()) => (
  !item.event_end_date || item.event_end_date < today
);

export const activeTemporaryListings = <T extends TemporaryListing>(items: T[]) => items.filter(
  (item) => !eventHasExpired(item)
    && !['expired', 'cancelled', 'deactivated', 'archived'].includes(item.status || ''),
);

export const availableResidentServices = <T extends TemporaryChoice>(items: T[]) => items.filter(
  (item) => !item.is_temporary || !eventHasExpired(item),
);
