/**
 * PrivacyLens — Content Script Page Parser
 * Extracts clean, readable text from active policy pages by pruning noise (scripts, styles, headers, footers).
 */

export function extractCleanPageText(): string {
  // Clone body to manipulate without affecting rendering
  const clone = document.body.cloneNode(true) as HTMLElement;

  // Remove irrelevant elements that add noise or contain executable markup
  const selectorsToRemove = [
    'script',
    'style',
    'noscript',
    'iframe',
    'svg',
    'header',
    'footer',
    'nav',
    '[role="navigation"]',
    '[role="banner"]',
    '[role="contentinfo"]',
    '.nav',
    '.navbar',
    '.header',
    '.footer',
    '.sidebar',
    '.cookie-banner',
    '.consent-banner'
  ];

  selectorsToRemove.forEach((selector) => {
    clone.querySelectorAll(selector).forEach((el) => el.remove());
  });

  // Extract clean text
  const text = clone.innerText || clone.textContent || '';
  return text
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s*\n\s*\n+/g, '\n\n')
    .trim();
}
