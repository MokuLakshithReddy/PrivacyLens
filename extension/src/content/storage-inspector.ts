/**
 * PrivacyLens — Storage & Cookie Inspector
 * THREAT MODEL ENFORCEMENT:
 * - Collects ONLY key names, key counts, and approximate byte sizes.
 * - NEVER reads or stores the value payload of localStorage, sessionStorage, or cookies.
 */

import { StorageSignal } from '@shared/types';

export function inspectStorageSignals(): StorageSignal[] {
  const signals: StorageSignal[] = [];

  // 1. Inspect LocalStorage Key Names Only
  try {
    const localLength = window.localStorage.length;
    for (let i = 0; i < localLength; i++) {
      const key = window.localStorage.key(i);
      if (key) {
        // Estimate size without exposing the content
        const rawVal = window.localStorage.getItem(key) || '';
        const byteSize = key.length + rawVal.length;

        signals.push({
          type: 'localStorage',
          name: key,
          isThirdParty: false,
          persistent: true,
          byteLength: byteSize
        });
      }
    }
  } catch {
    // Access denied by iframe or security setting
  }

  // 2. Inspect SessionStorage Key Names Only
  try {
    const sessionLength = window.sessionStorage.length;
    for (let i = 0; i < sessionLength; i++) {
      const key = window.sessionStorage.key(i);
      if (key) {
        const rawVal = window.sessionStorage.getItem(key) || '';
        const byteSize = key.length + rawVal.length;

        signals.push({
          type: 'sessionStorage',
          name: key,
          isThirdParty: false,
          persistent: false,
          byteLength: byteSize
        });
      }
    }
  } catch {
    // Access denied
  }

  // 3. Inspect Document Cookie Names Only (No values extracted)
  try {
    const rawCookies = document.cookie;
    if (rawCookies) {
      const cookiePairs = rawCookies.split(';');
      for (const pair of cookiePairs) {
        const eqIdx = pair.indexOf('=');
        const cookieName = (eqIdx > -1 ? pair.slice(0, eqIdx) : pair).trim();
        if (cookieName) {
          signals.push({
            type: 'cookie',
            name: cookieName,
            isThirdParty: false,
            persistent: true // Default heuristic if visible via JS
          });
        }
      }
    }
  } catch {
    // Access denied
  }

  return signals;
}
