/**
 * PrivacyLens — Storage Inspector
 * Collects storage-area item counts only. It does not enumerate keys,
 * read storage values, or inspect cookies.
 */
import { StorageSignal } from '@shared/types';

export function inspectStorageSignals(): StorageSignal[] {
  const signals: StorageSignal[] = [];
  try {
    const count = window.localStorage.length;
    if (count > 0) signals.push({ type: 'localStorage', count, isThirdParty: false, persistent: true });
  } catch {
    // Storage may be unavailable in a sandboxed or restricted document.
  }
  try {
    const count = window.sessionStorage.length;
    if (count > 0) signals.push({ type: 'sessionStorage', count, isThirdParty: false, persistent: false });
  } catch {
    // Storage may be unavailable in a sandboxed or restricted document.
  }
  return signals;
}
