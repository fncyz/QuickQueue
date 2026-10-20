import { api } from '@/services/api';
import { writeActiveAppointmentCache } from '@/services/offline-cache';

export type QueueStatusAppointment = {
  id: number;
  appointment_id: string;
  name: string;
  service: string;
  service_fee: string;
  date: string;
  time_slot: string;
  barangay: string;
  queue_number: string;
  status: string;
  status_code: string;
  now_serving: string;
  people_ahead: number;
  estimated_wait: number;
  checked_in: boolean;
};

type QueueStatusResponse = { appointment: QueueStatusAppointment | null };
type QueueStatusResult = QueueStatusResponse & { fetchedAt: number; fromNetwork: boolean };

let latest: (QueueStatusResponse & { fetchedAt: number; token: string }) | null = null;
let inFlight: { token: string; promise: Promise<QueueStatusResult> } | null = null;
let requestSequence = 0;
let appliedSequence = 0;

export async function refreshQueueStatus(
  token: string,
  options: { maxAgeMs?: number } = {},
): Promise<QueueStatusResult> {
  const maxAgeMs = options.maxAgeMs ?? 0;
  if (latest?.token === token && Date.now() - latest.fetchedAt <= maxAgeMs) {
    return { appointment: latest.appointment, fetchedAt: latest.fetchedAt, fromNetwork: false };
  }
  if (inFlight?.token === token) return inFlight.promise;

  const sequence = ++requestSequence;
  const promise = api.get<QueueStatusResponse>(
    'queue-status/',
    { headers: { Authorization: `Bearer ${token}` } },
  ).then(async (response) => {
    const fetchedAt = Date.now();
    if (sequence < appliedSequence) throw new Error('Superseded queue-status response');
    appliedSequence = sequence;
    latest = { appointment: response.data.appointment, fetchedAt, token };
    await writeActiveAppointmentCache(response.data.appointment);
    return {
      appointment: response.data.appointment,
      fetchedAt,
      fromNetwork: true,
    };
  }).finally(() => {
    if (inFlight?.promise === promise) inFlight = null;
  });

  inFlight = { token, promise };
  return promise;
}

export function invalidateQueueStatus(token?: string) {
  if (!token || latest?.token === token) latest = null;
  if (!token || inFlight?.token === token) inFlight = null;
  appliedSequence = ++requestSequence;
}
