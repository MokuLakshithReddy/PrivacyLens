/**
 * PrivacyLens — Network Traffic Observer (Service Worker)
 * Passively captures network request metadata without inspecting payloads.
 */

import { NetworkSignal, RequestCategory } from '@shared/types';

// High-confidence domain category lookup rules
const TRACKER_RULES: { pattern: RegExp; category: RequestCategory }[] = [
  { pattern: /(?:google-analytics|googletagmanager|analytics\.google|hotjar|mixpanel|segment\.io|amplitude|heap\.io|clarity\.ms)/i, category: 'analytics' },
  { pattern: /(?:doubleclick|googlesyndication|adservice\.google|adnxs|criteo|pubmatic|rubiconproject|amazon-adsystem|taboola|outbrain|facebook\.com\/tr)/i, category: 'advertising' },
  { pattern: /(?:connect\.facebook|platform\.twitter|linkedin\.com\/px|pinterest\.com\/ct)/i, category: 'social' },
  { pattern: /(?:cloudflare|akamai|fastly|cloudfront|jsdelivr|unpkg|cdnjs)/i, category: 'cdn' },
  { pattern: /(?:sentry\.io|bugsnag|datadog|newrelic|rollbar)/i, category: 'telemetry' }
];

export function classifyDomain(targetDomain: string): RequestCategory {
  for (const rule of TRACKER_RULES) {
    if (rule.pattern.test(targetDomain)) {
      return rule.category;
    }
  }
  return 'unknown';
}

export function isThirdPartyDomain(initiatorHostname: string, targetHostname: string): boolean {
  if (!initiatorHostname || !targetHostname) return false;
  
  // Extract base domain (e.g. example.com from sub.example.com)
  const getBaseDomain = (host: string) => {
    const parts = host.split('.');
    if (parts.length <= 2) return host;
    return parts.slice(-2).join('.');
  };

  return getBaseDomain(initiatorHostname) !== getBaseDomain(targetHostname);
}

export function parseRequestSignal(
  details: chrome.webRequest.WebRequestBodyDetails
): NetworkSignal | null {
  try {
    const targetUrl = new URL(details.url);
    const targetDomain = targetUrl.hostname;

    let initiatorHost = '';
    if (details.initiator) {
      initiatorHost = new URL(details.initiator).hostname;
    }

    const isThirdParty = isThirdPartyDomain(initiatorHost, targetDomain);
    const category = classifyDomain(targetDomain);

    return {
      requestId: details.requestId,
      url: `${targetUrl.protocol}//${targetUrl.hostname}${targetUrl.pathname}`, // strip query params & hashes
      targetDomain,
      initiator: initiatorHost,
      isThirdParty,
      category,
      method: details.method,
      timestamp: Math.floor(details.timeStamp || Date.now())
    };
  } catch {
    return null;
  }
}
