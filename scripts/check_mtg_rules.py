#!/usr/bin/env python3
"""Track official MTG rules sources without republishing copyrighted rulebooks."""
import hashlib
import html.parser
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rules" / "manifest.json"
CHANGELOG = ROOT / "rules" / "CHANGELOG.md"
SOURCES = {
    "comprehensive_rules": "https://magic.wizards.com/en/rules",
    "commander_format": "https://magic.wizards.com/en/formats/commander",
    "banned_restricted": "https://magic.wizards.com/en/banned-restricted-list",
}
MAX_BYTES = 15 * 1024 * 1024

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encode_url(url):
    """Percent-encode unsafe URL path characters without double-encoding percent escapes."""
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parsed.path, safe="/%:@!$&'()*+,;=-._~")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))

def get(url):
    url = encode_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "MTG-Deck-Tools-rules-source-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=70) as response:
        final = response.geturl()
        if urllib.parse.urlparse(final).hostname not in ("magic.wizards.com", "media.wizards.com", "media.wizards.com"):
            raise ValueError("Unexpected redirect host: " + final)
        data = response.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Unexpected source size: " + url)
    return data, final

def discover_rule_documents(page, base):
    parser = Links()
    parser.feed(page.decode("utf-8", errors="replace"))
    found = {}
    for href in parser.links:
        url = encode_url(urllib.parse.urljoin(base, href))
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ("magic.wizards.com", "media.wizards.com"):
            continue
        if re.search(r"\.(?:pdf|docx)(?:$|[?#])", url, re.I):
            kind = "pdf" if re.search(r"\.pdf(?:$|[?#])", url, re.I) else "docx"
            found.setdefault(kind, url)
    return found

def scan():
    result = {}
    for key, url in SOURCES.items():
        page, final = get(url)
        result[key] = {"url": final, "sha256": sha(page), "bytes": len(page)}
        if key == "comprehensive_rules":
            docs = discover_rule_documents(page, final)
            if not docs:
                raise ValueError("No official PDF/DOCX rules document links found; source layout may have changed")
            for kind, doc_url in docs.items():
                content, resolved = get(doc_url)
                if kind == "pdf" and not content.startswith(b"%PDF"):
                    raise ValueError("Downloaded rules PDF has invalid signature")
                if kind == "docx" and not content.startswith(b"PK"):
                    raise ValueError("Downloaded rules DOCX has invalid signature")
                result["comprehensive_rules_" + kind] = {
                    "url": resolved, "sha256": sha(content), "bytes": len(content)
                }
    return result

HTML_SOURCE_KEYS = frozenset(SOURCES)


def classify_source_changes(previous, current, baseline_status="verified"):
    """Classify a verified snapshot without conflating HTML and rules document changes.

    Only raw HTML bytes/size changes at the *same* verified official URLs are
    informational. This does NOT establish that banlists or format rules are
    unchanged: human review is still required. Missing/new documents, changed
    document checksums, changed URLs or an unverified baseline are blocking.
    """
    if baseline_status != "verified" or not previous:
        return "blocking_review"
    changed = {key for key in set(previous) | set(current)
               if previous.get(key) != current.get(key)}
    if not changed:
        return "unchanged"
    if not changed <= HTML_SOURCE_KEYS:
        return "blocking_review"
    for key in changed:
        before, after = previous.get(key), current.get(key)
        if not isinstance(before, dict) or not isinstance(after, dict):
            return "blocking_review"
        if set(before) != {"url", "sha256", "bytes"} or set(after) != set(before):
            return "blocking_review"
        if before["url"] != after["url"]:
            return "blocking_review"
        if not isinstance(after["sha256"], str) or len(after["sha256"]) != 64:
            return "blocking_review"
        if not isinstance(after["bytes"], int) or after["bytes"] <= 0:
            return "blocking_review"
    return "html_review"


def report_step_status(status):
    """Pass a fixed classification to GitHub Actions, never arbitrary web text."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as output:
            output.write("change_type=" + status + "\n")


def main():
    old = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current = scan()  # Fail without altering any tracked files if a source cannot be verified.
    previous = old.get("sources", {})
    changed = sorted(k for k in set(previous) | set(current) if previous.get(k) != current.get(k))
    status = classify_source_changes(previous, current, old.get("status"))
    report_step_status(status)
    if status == "unchanged":
        print("Official source fingerprints unchanged; no commit required.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    MANIFEST.write_text(json.dumps({
        "schema_version": 1, "status": "verified", "last_checked_utc": stamp,
        "sources": current,
        "notice": "Checksums detect source changes, not confirmed changes to MTG rules or bans."
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not previous:
        description = "Initial verified source baseline"
    else:
        description = "Source fingerprint changes: " + ", ".join(changed)
    with CHANGELOG.open("a", encoding="utf-8") as log:
        log.write("\n- **" + stamp + "**: " + description +
                  ". Manual review required before treating this as a rules/banlist change.\n")
    print(description)
    print("Review classification: " + status)

if __name__ == "__main__":
    main()
