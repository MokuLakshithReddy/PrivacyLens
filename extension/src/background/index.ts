/**
 * PrivacyLens — Background Service Worker Entrypoint
 * Coordinates passive network observation, permission tracking, and tab state management.
 */

import { parseRequestSignal } from './network/traffic-observer';
import { PermissionObserver } from './permissions/permission-observer';
import { TabObservationStore } from './messaging/message-router';

const store = new TabObservationStore();
const permissions = new PermissionObserver();

// Tab navigation lifecycle
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading' && tab.url) {
    store.initTab(tabId, tab.url);
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
        // Auto-initialize session if tab was opened before extension worker woke up
        let session = store.getSession(details.tabId);
        if (!session && details.initiator) {
          session = store.initTab(details.tabId, details.initiator);
        }
        store.addRequest(details.tabId, signal);
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

        sendResponse({ analysis });
      } catch (err: any) {
        sendResponse({ error: err.message });
      }
    })();

    return true; // Keep channel open for async response
  }
});

console.log('[PrivacyLens] Background Service Worker active.');
