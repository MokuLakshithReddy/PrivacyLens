/**
 * PrivacyLens — Background Service Worker Entrypoint
 * Coordinates passive network observation, permission tracking, live toolbar badges, and tab state management.
 */

import { parseRequestSignal } from './network/traffic-observer';
import { PermissionObserver } from './permissions/permission-observer';
import { TabObservationStore } from './messaging/message-router';

const store = new TabObservationStore();
const permissions = new PermissionObserver();

/**
 * Updates the extension badge on the browser toolbar with the calculated risk score
 */
function updateTabBadge(tabId: number, score: number) {
  try {
    const text = score.toString();
    chrome.action.setBadgeText({ tabId, text });

    // Dynamic color coding: Green (<=25), Amber (26-60), Red (>60)
    let color = '#10b981'; // Green
    if (score > 60) {
      color = '#ef4444'; // Red
    } else if (score > 25) {
      color = '#f59e0b'; // Amber
    }

    chrome.action.setBadgeBackgroundColor({ tabId, color });
  } catch {
    // Tab may have closed
  }
}

// Tab navigation lifecycle
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading' && tab.url) {
    store.initTab(tabId, tab.url);
    // Reset badge while loading
    chrome.action.setBadgeText({ tabId, text: '' }).catch(() => {});
  }
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const session = store.getSession(activeInfo.tabId);
  if (session) {
    const analysis = store.evaluateLocally(session);
    updateTabBadge(activeInfo.tabId, analysis.riskScore);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  store.clearTab(tabId);
});

// Passive network traffic observation
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    // Only capture requests associated with standard tabs (tabId >= 0)
    if (details.tabId >= 0) {
      const signal = parseRequestSignal(details);
      if (signal) {
        let session = store.getSession(details.tabId);
        if (!session && details.initiator) {
          session = store.initTab(details.tabId, details.initiator);
        }
        store.addRequest(details.tabId, signal);

        // Update live badge periodically as network requests accumulate
        if (session && session.requests.length % 3 === 0) {
          const quickAnalysis = store.evaluateLocally(session);
          updateTabBadge(details.tabId, quickAnalysis.riskScore);
        }
      }
    }
  },
  { urls: ['<all_urls>'] }
);

// Messaging listener for content script signals and popup queries
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const tabId = sender.tab?.id;

  if (message.type === 'CONTENT_SIGNALS_DETECTED' && tabId !== undefined) {
    const { policyLinks, storageSignals } = message.payload;
    if (policyLinks && policyLinks.length > 0) {
      store.setPolicyUrl(tabId, policyLinks[0].url);
    }
    if (storageSignals) {
      store.setStorageSignals(tabId, storageSignals);
    }
    sendResponse({ status: 'acknowledged' });
    return true;
  }

  if (message.type === 'GET_TAB_SIGNALS') {
    const targetTabId = message.tabId;
    const session = store.getSession(targetTabId);
    sendResponse({ session: session || null });
    return true;
  }

  if (message.type === 'ANALYZE_ACTIVE_TAB') {
    const targetTabId = message.tabId;

    (async () => {
      try {
        let session = store.getSession(targetTabId);

        // If session was not initialized yet, query active tab info
        if (!session) {
          const tab = await chrome.tabs.get(targetTabId);
          if (tab.url) {
            session = store.initTab(targetTabId, tab.url);
          }
        }

        if (!session) {
          sendResponse({ error: 'Could not determine tab origin.' });
          return;
        }

        // Try querying live DOM evidence from content script to ensure latest storage/policy
        try {
          const domEvidence = await chrome.tabs.sendMessage(targetTabId, { type: 'GET_DOM_EVIDENCE' });
          if (domEvidence) {
            if (domEvidence.policyLinks && domEvidence.policyLinks.length > 0) {
              store.setPolicyUrl(targetTabId, domEvidence.policyLinks[0].url);
            }
            if (domEvidence.storageSignals) {
              store.setStorageSignals(targetTabId, domEvidence.storageSignals);
            }
          }
        } catch {
          // Content script may not be loaded on restricted internal pages
        }

        // Inspect permissions
        const permSignals = await permissions.inspectPermissionsForOrigin(session.domain);
        store.setPermissions(targetTabId, permSignals);

        // Try syncing with FastAPI backend; if offline, run dynamic local edge evaluation
        let analysis = await store.syncWithBackend(session);
        if (!analysis) {
          analysis = store.evaluateLocally(session);
        }

        // Update live badge with verified score
        updateTabBadge(targetTabId, analysis.riskScore);

        sendResponse({ analysis });
      } catch (err: any) {
        sendResponse({ error: err.message });
      }
    })();

    return true; // Keep channel open for async response
  }
});

console.log('[PrivacyLens] Background Service Worker active with live badge support.');
