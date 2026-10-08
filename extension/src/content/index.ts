/**
 * PrivacyLens — Content Script Entrypoint
 * Coordinates policy link detection, storage inspection, and text extraction.
 */

import { detectPolicyLinks } from './policy-detector';
import { inspectStorageSignals } from './storage-inspector';
import { extractCleanPageText } from './page-parser';

// Perform initial passive scan on document_idle
function performInspection() {
  const policyLinks = detectPolicyLinks();
  const storageSignals = inspectStorageSignals();

  // Send metadata to background worker
  chrome.runtime.sendMessage({
    type: 'CONTENT_SIGNALS_DETECTED',
    payload: {
      url: window.location.href,
      domain: window.location.hostname,
      policyLinks,
      storageSignals
    }
  }).catch(() => {
    // Background worker may be dormant
  });
}

// Listen for direct queries from Popup or Background
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'GET_DOM_EVIDENCE') {
    const policyLinks = detectPolicyLinks();
    const storageSignals = inspectStorageSignals();
    sendResponse({
      url: window.location.href,
      domain: window.location.hostname,
      policyLinks,
      storageSignals
    });
    return true;
  }

  if (message.type === 'EXTRACT_POLICY_TEXT') {
    const cleanText = extractCleanPageText();
    sendResponse({
      url: window.location.href,
      domain: window.location.hostname,
      text: cleanText
    });
    return true;
  }
});

// Run inspection on load
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  performInspection();
} else {
  window.addEventListener('DOMContentLoaded', performInspection);
}
