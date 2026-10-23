/**
 * PrivacyLens — Network Traffic Observer (Service Worker)
 * Passively captures network request metadata without inspecting payloads.
 */

import { NetworkSignal, RequestCategory } from '@shared/types';

// Host-suffix rules only. Matching is performed on parsed hostnames, never URL text.
const CATEGORY_SUFFIXES: Record<Exclude<RequestCategory, 'unknown'>, string[]> = {
  analytics: ['google-analytics.com', 'googletagmanager.com', 'hotjar.com', 'mixpanel.com', 'segment.io', 'amplitude.com', 'heap.io', 'clarity.ms'],
  advertising: ['doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'adnxs.com', 'criteo.com', 'pubmatic.com', 'rubiconproject.com', 'amazon-adsystem.com', 'taboola.com', 'outbrain.com'],
  social: ['connect.facebook.net', 'facebook.com', 'platform.twitter.com', 'x.com', 'linkedin.com', 'pinterest.com'],
  cdn: ['cloudflare.com', 'akamai.net', 'fastly.net', 'cloudfront.net', 'jsdelivr.net', 'unpkg.com', 'cdnjs.com'],
  essential: [],
  telemetry: ['sentry.io', 'bugsnag.com', 'datadoghq.com', 'newrelic.com', 'rollbar.com']
};

const MULTI_LABEL_SUFFIXES = new Set([
  'ac.uk', 'co.uk', 'gov.uk', 'org.uk', 'com.au', 'net.au', 'org.au', 'co.nz',
  'co.jp', 'com.br', 'com.cn', 'co.in', 'co.za', 'com.sg', 'com.hk', 'com.mx',
  'com.tr', 'co.kr', 'github.io'
]);

function normalizeHost(host: string): string {
  return host.toLowerCase().replace(/\.$/, '');
}

function hasHostSuffix(host: string, suffix: string): boolean {
  const normalizedHost = normalizeHost(host);
  return normalizedHost === suffix || normalizedHost.endsWith(`.${suffix}`);
}

export function getRegistrableDomain(host: string): string {
  const normalized = normalizeHost(host);
  if (!normalized || /^\[?[^.]+:\d*\]?$/.test(normalized) || /^\d+(?:\.\d+){3}$/.test(normalized)) return normalized;
  const parts = normalized.split('.');
  if (parts.length <= 2) return normalized;
  const lastTwo = parts.slice(-2).join('.');
  const suffixLength = MULTI_LABEL_SUFFIXES.has(lastTwo) ? 2 : 1;
  return parts.slice(-(suffixLength + 1)).join('.');
}

export function classifyDomain(targetDomain: string): RequestCategory {
  const host = normalizeHost(targetDomain);
  for (const [category, suffixes] of Object.entries(CATEGORY_SUFFIXES) as [Exclude<RequestCategory, 'unknown'>, string[]][]) {
    if (suffixes.some((suffix) => hasHostSuffix(host, suffix))) return category;
  }
  return 'unknown';
}

export function isThirdPartyDomain(initiatorHostname: string, targetHostname: string): boolean {
  if (!initiatorHostname || !targetHostname) return false;
  return getRegistrableDomain(initiatorHostname) !== getRegistrableDomain(targetHostname);
}

export function parseRequestSignal(
  details: chrome.webRequest.WebRequestBodyDetails
): NetworkSignal | null {
  try {
    const targetUrl = new URL(details.url);
    if (targetUrl.protocol !== 'http:' && targetUrl.protocol !== 'https:') return null;
    const targetDomain = targetUrl.hostname;

    let initiatorHost = '';
    if (details.initiator) {
      initiatorHost = new URL(details.initiator).hostname;
    }

    const isThirdParty = isThirdPartyDomain(initiatorHost, targetDomain);
    const category = classifyDomain(targetDomain);

    return {
      requestId: details.requestId,
      url: targetUrl.origin, // Paths can contain identifiers and secrets; retain only the origin.
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
