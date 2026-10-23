/**
 * PrivacyLens content script. Page inspection runs only after explicit opt-in.
 */
import { detectPolicyLinks } from './policy-detector';
import { inspectStorageSignals } from './storage-inspector';
import { extractCleanPageText } from './page-parser';

async function isMonitoringEnabled(): Promise<boolean> {
  try {
    const state = await chrome.storage.local.get({ monitoringEnabled: false });
    return state.monitoringEnabled === true;
  } catch {
    return false;
  }
}

async function performInspection() {
  if (!(await isMonitoringEnabled())) return;
  const policyLinks = detectPolicyLinks();
  const storageSignals = inspectStorageSignals();
  chrome.runtime.sendMessage({
    type: 'CONTENT_SIGNALS_DETECTED',
    payload: { url: window.location.origin, domain: window.location.hostname, policyLinks, storageSignals },
  }).catch(() => {});
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'GET_DOM_EVIDENCE') {
    void isMonitoringEnabled().then((enabled) => {
      if (!enabled) {
        sendResponse({ error: 'monitoring_paused' });
        return;
      }
      sendResponse({
        url: window.location.origin,
        domain: window.location.hostname,
        policyLinks: detectPolicyLinks(),
        storageSignals: inspectStorageSignals(),
      });
    });
    return true;
  }
  if (message.type === 'EXTRACT_POLICY_TEXT') {
    void isMonitoringEnabled().then((enabled) => {
      sendResponse(enabled ? {
        url: window.location.origin,
        domain: window.location.hostname,
        text: extractCleanPageText(),
      } : { error: 'monitoring_paused' });
    });
    return true;
  }
});

if (document.readyState === 'complete' || document.readyState === 'interactive') {
  void performInspection();
} else {
  window.addEventListener('DOMContentLoaded', () => void performInspection(), { once: true });
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.monitoringEnabled?.newValue === true) {
    void performInspection();
  }
});
