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
  matchRank: number;
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
          matchRank: 0.99
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
        let matchRank = 0.5;
        if (textMatches && urlMatches) matchRank = 0.95;
        else if (textMatches) matchRank = 0.85;
        else if (urlMatches) matchRank = 0.75;

        if (isFooter) matchRank = Math.min(1.0, matchRank + 0.1);

        candidates.push({
          url: fullUrl,
          anchorText: text.slice(0, 50),
          source: isFooter ? 'footer' : 'body',
          matchRank
        });
      }
    } catch {
      // Invalid URL
    }
  }

  // Sort candidates by matchRank descending and deduplicate by URL
  const uniqueMap = new Map<string, DiscoveredPolicyLink>();
  candidates
    .sort((a, b) => b.matchRank - a.matchRank)
    .forEach((c) => {
      if (!uniqueMap.has(c.url)) {
        uniqueMap.set(c.url, c);
      }
    });

  return Array.from(uniqueMap.values());
}
