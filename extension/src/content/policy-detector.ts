/**
 * PrivacyLens — Content Script Policy Detector
 * Scans the active page for privacy policy links using heuristic anchor inspection and meta tags.
 */

const PRIVACY_KEYWORDS = [
  'privacy policy',
  'privacy notice',
  'privacy statement',
  'privacy',
  'data protection',
  'datenschutz',
  'politique de confidentialité',
  'aviso de privacidad'
];

const PRIVACY_URL_REGEX = /(?:privacy|privacy-policy|privacy_policy|datenschutz|data-protection|legal\/privacy)/i;

export interface DiscoveredPolicyLink {
  url: string;
  anchorText: string;
  source: 'footer' | 'body' | 'meta' | 'standard_link';
  confidence: number;
}

export function detectPolicyLinks(): DiscoveredPolicyLink[] {
  const candidates: DiscoveredPolicyLink[] = [];
  const origin = window.location.origin;

  // 1. Check meta tags
  const metaLink = document.querySelector('link[rel="privacy-policy"]');
  if (metaLink) {
    const href = metaLink.getAttribute('href');
    if (href) {
      try {
        const fullUrl = new URL(href, origin).href;
        candidates.push({
          url: fullUrl,
          anchorText: 'meta:link[rel=privacy-policy]',
          source: 'meta',
          confidence: 0.99
        });
      } catch {
        // ignore invalid url
      }
    }
  }

  // 2. Scan anchor tags
  const anchors = document.querySelectorAll('a[href]');
  for (const anchor of anchors) {
    const text = (anchor.textContent || '').trim().toLowerCase();
    const href = anchor.getAttribute('href') || '';
    if (!href || href.startsWith('javascript:') || href.startsWith('#')) {
      continue;
    }

    try {
      const fullUrl = new URL(href, origin).href;
      // Skip cross-domain privacy policies (e.g. Google login on a site) unless explicitly primary
      const urlMatches = PRIVACY_URL_REGEX.test(fullUrl);
      const textMatches = PRIVACY_KEYWORDS.some((kw) => text.includes(kw));

      if (urlMatches || textMatches) {
        const isFooter = !!anchor.closest('footer, [id*="footer" i], [class*="footer" i]');
        let confidence = 0.5;
        if (textMatches && urlMatches) confidence = 0.95;
        else if (textMatches) confidence = 0.85;
        else if (urlMatches) confidence = 0.75;

        if (isFooter) confidence = Math.min(1.0, confidence + 0.1);

        candidates.push({
          url: fullUrl,
          anchorText: text.slice(0, 50),
          source: isFooter ? 'footer' : 'body',
          confidence
        });
      }
    } catch {
      // Invalid URL
    }
  }

  // Sort candidates by confidence descending and deduplicate by URL
  const uniqueMap = new Map<string, DiscoveredPolicyLink>();
  candidates
    .sort((a, b) => b.confidence - a.confidence)
    .forEach((c) => {
      if (!uniqueMap.has(c.url)) {
        uniqueMap.set(c.url, c);
      }
    });

  return Array.from(uniqueMap.values());
}
