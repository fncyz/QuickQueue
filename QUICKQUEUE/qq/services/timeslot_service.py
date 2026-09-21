from datetime import time

from qq.models import TimeSlot


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
                "max_appointments": 5,
            },
        )
