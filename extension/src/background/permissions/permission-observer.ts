/**
 * PrivacyLens — Permission Observer (Service Worker)
 * Tracks browser capability permissions associated with active domains.
 */

import { PermissionSignal } from '@shared/types';

export const MONITORED_PERMISSIONS: PermissionName[] = [
  'geolocation',
  'notifications',
  'camera' as PermissionName,
  'microphone' as PermissionName
];

export class PermissionObserver {
  private permissionCache = new Map<string, PermissionSignal[]>();

  async inspectPermissionsForOrigin(origin: string): Promise<PermissionSignal[]> {
    const signals: PermissionSignal[] = [];

    // Service worker permission status query where supported
    for (const name of MONITORED_PERMISSIONS) {
      try {
        if (navigator.permissions && navigator.permissions.query) {
          const status = await navigator.permissions.query({ name });
          signals.push({
            permission: name,
            state: status.state,
            timestamp: Date.now()
          });
        }
      } catch {
        // Some permissions query types not supported in SW context
      }
    }

    this.permissionCache.set(origin, signals);
    return signals;
  }

  getCached(origin: string): PermissionSignal[] {
    return this.permissionCache.get(origin) || [];
  }
}
