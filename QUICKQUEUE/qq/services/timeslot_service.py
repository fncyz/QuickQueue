from datetime import time

from qq.models import TimeSlot

REGULAR_TIME_SLOT_CAPACITY = 5
REGULAR_DAILY_CAPACITY = 30


def regular_slot_capacities(barangay, time_slots=None):
    """Distribute the barangay's regular daily capacity across active slots."""
    if time_slots is None:
        time_slots = TimeSlot.objects.filter(
            barangay=barangay,
            is_active=True,
        ).order_by("start_time", "pk")
    slots = sorted(
        (slot for slot in time_slots if slot.is_active),
        key=lambda slot: (slot.start_time, slot.pk),
    )
    if not slots:
        return {}
    base, remainder = divmod(regular_daily_capacity(barangay), len(slots))
    return {
        slot.pk: base + (1 if index < remainder else 0)
        for index, slot in enumerate(slots)
    }


def regular_slot_capacity(time_slot, capacities=None):
    """Return the configured share of daily capacity for one regular slot."""
    if not time_slot.is_active:
        return 0
    if capacities is None:
        capacities = regular_slot_capacities(time_slot.barangay)
    return capacities.get(time_slot.pk, 0)


def regular_daily_capacity(barangay):
    """Return the persisted regular daily capacity, retaining the legacy default."""
    return getattr(barangay, "daily_booking_capacity", REGULAR_DAILY_CAPACITY)


DEFAULT_TIME_SLOTS = (
    (time(8, 0), time(9, 0)),
    (time(9, 0), time(10, 0)),
    (time(10, 0), time(11, 0)),
    (time(13, 0), time(14, 0)),
    (time(14, 0), time(15, 0)),
    (time(15, 0), time(16, 0)),
)


def ensure_default_time_slots(barangay):
    """
    Make sure a barangay has the standard booking time slots.
    """
    for start_time, end_time in DEFAULT_TIME_SLOTS:
        TimeSlot.objects.get_or_create(
            barangay=barangay,
            start_time=start_time,
            end_time=end_time,
            defaults={
                "is_active": True,
                "max_appointments": REGULAR_TIME_SLOT_CAPACITY,
            },
        )
