import re
from typing import List, Dict
from bs4 import BeautifulSoup

def clean_policy_html(html_content: str) -> str:
    """
    Strips scripts, styles, navigation, headers, footers, forms, and iframe noise from HTML.
    """
    soup = BeautifulSoup(html_content, "lxml")

    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "svg", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Normalize whitespaces
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()

def extract_sections_from_html_or_text(html_or_text: str) -> List[Dict[str, str]]:
    """
    First checks if HTML heading tags (h1, h2, h3) exist. If so, segments by headings.
    Otherwise segments by text patterns.
    """
    sections: List[Dict[str, str]] = []

    if "<h1" in html_or_text.lower() or "<h2" in html_or_text.lower():
        soup = BeautifulSoup(html_or_text, "lxml")
        for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "svg", "form"]):
            tag.decompose()

        headings = soup.find_all(["h1", "h2", "h3", "h4"])
        for h in headings:
            title = h.get_text().strip()
            # Collect following sibling text until next heading
            content_nodes = []
            curr = h.next_sibling
            while curr and getattr(curr, 'name', None) not in ["h1", "h2", "h3", "h4"]:
                text_piece = curr.get_text() if hasattr(curr, 'get_text') else str(curr)
                content_nodes.append(text_piece.strip())
                curr = curr.next_sibling

            section_body = " ".join([c for c in content_nodes if c]).strip()
            if len(title) > 2:
                sections.append({
                    "section_name": title,
                    "text": section_body if section_body else title
                })

    if sections:
        return sections

    # Text fallback
    clean_text = clean_policy_html(html_or_text) if "<" in html_or_text else html_or_text
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    current_title = "General Policy Provisions"
    current_body = []

    for line in lines:
        is_heading = (
            len(line) < 70 and
            (any(k in line.lower() for k in ["information", "collect", "use", "sharing", "cookies", "rights", "retention", "security"])
             or line.isupper() or re.match(r'^\d+[\.\)]\s+', line))
        )
        if is_heading:
            if current_body:
                sections.append({
                    "section_name": current_title,
                    "text": " ".join(current_body)
                })
                current_body = []
            current_title = line
        else:
            current_body.append(line)

    if current_body:
        sections.append({
            "section_name": current_title,
            "text": " ".join(current_body)
        })

    return sections if sections else [{"section_name": "General Policy Provisions", "text": clean_text[:8000]}]

def segment_policy_sections(cleaned_text: str) -> List[Dict[str, str]]:
    return extract_sections_from_html_or_text(cleaned_text)
