"""Tool 2: URL extraction + marketplace-impersonation check. Pure code, no network, ever.

- Finds links in the pasted text (with or without http://, including punycode and non-ASCII hosts).
- Decodes punycode (xn--) back to the characters the scammer chose, then compares the host with the
  official marketplace whitelist by "skeleton" (homoglyphs / digits folded to Latin) and edit distance.
- Short links are NEVER expanded (expanding = opening the scammer's link). They are a red flag as such.

Nothing in this module resolves DNS or opens a connection; tests run with the network blocked.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit

# ---------------------------------------------------------------- whitelist / lists (keep in sync with docs)
# Registrable domains. Subdomains of these are official too (e.g. mall.shopee.tw).
# Meeting whitelist: shopee.tw / shopee.sg / carousell / ruten. Other Shopee & Carousell country sites are
# added so a real regional link is not called impersonation. Full list to be confirmed by Quinn's eval set.
OFFICIAL_DOMAINS: dict[str, set[str]] = {
    "shopee": {"shopee.tw", "shopee.sg", "shopee.com.my", "shopee.ph", "shopee.co.id", "shopee.co.th", "shopee.vn"},
    "carousell": {"carousell.sg", "carousell.com", "carousell.com.my", "carousell.ph", "carousell.com.hk"},
    "ruten": {"ruten.com.tw"},
}
BRAND_LABEL = {"shopee": "Shopee", "carousell": "Carousell", "ruten": "Ruten"}

# Never expanded. shp.ee is Shopee's own shortener but we cannot see where it points without opening it.
SHORTENERS = {
    "bit.ly", "bit.do", "reurl.cc", "tinyurl.com", "t.co", "goo.gl", "is.gd", "v.gd", "x.gd", "ppt.cc",
    "lihi.cc", "lihi1.cc", "lihi2.cc", "lihi3.cc", "pse.is", "0rz.tw", "rb.gy", "cutt.ly", "shorturl.at",
    "s.id", "ow.ly", "t.ly", "tiny.cc", "shp.ee", "lin.ee", "maac.io", "reurl.tw",
}

# Two-label public suffixes we meet in this market (avoids tldextract, which downloads the PSL at runtime).
MULTI_SUFFIXES = {
    "com.tw", "net.tw", "org.tw", "idv.tw", "com.sg", "com.my", "co.id", "co.th", "com.ph", "com.hk",
    "com.vn", "co.uk", "com.au",
}

# Bare domains (no http://) are only recognised with these TLDs, so "Mr.Smith" or "photo.jpg" are not links.
BARE_TLDS = {
    "com", "net", "org", "tw", "sg", "my", "ph", "id", "th", "vn", "hk", "cn", "jp", "kr", "us", "uk", "au",
    "cc", "co", "io", "me", "ly", "gl", "gd", "at", "ee", "to", "ws", "pw", "tk", "ml", "ga", "cf", "gq",
    "xyz", "top", "info", "biz", "shop", "store", "site", "online", "app", "link", "click", "vip", "live",
    "club", "icu", "asia", "buzz", "fun", "life", "today", "support", "help", "services", "cloud", "page",
    # cheap TLDs common in phishing (docs/qa/bugs.md BUG-002)
    "sbs", "cyou", "bond", "cfd", "ru", "work", "pro", "lol", "win", "rest", "quest", "mom", "zip", "mov",
    "one", "tech", "website", "space", "ltd", "xin", "ink", "wang", "red", "kim", "men", "loan", "cam",
}
# Any other TLD still counts for a bare domain when it looks like a link: a path after it, a hyphen in the
# name, or a marketplace brand in the name. File names ("photo.jpg", "invoice.pdf") never count.
FILE_EXTS = {
    "jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "bmp", "svg", "pdf", "txt", "doc", "docx", "xls", "xlsx",
    "ppt", "pptx", "csv", "mp3", "mp4", "m4a", "wav", "avi", "mkv", "html", "htm", "js", "py", "exe", "apk",
    "rar", "7z", "gz", "json", "xml",
}

# Homoglyphs folded to the Latin letter they imitate (Cyrillic / Greek / IPA), plus digit look-alikes.
CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s",
    "һ": "h", "ԁ": "d", "ӏ": "l", "к": "k", "м": "m", "н": "h", "т": "t", "в": "b", "г": "r", "ո": "n",
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "κ": "k", "ν": "v", "τ": "t", "υ": "u", "ι": "i",
    "ɡ": "g", "ı": "i", "ł": "l", "ø": "o",
    "0": "o", "1": "l", "3": "e", "5": "s", "@": "a",
})

# ---------------------------------------------------------------- extraction
_L = r"a-zA-Z0-9\-À-ɏͰ-ϿЀ-ӿԀ-ԯḀ-ỿɐ-ʯ"
_STOP = r"\s<>\"'）)】」』，。、！？；"
# No \b: CJK counts as a word character, so "請點https://..." would not match with \b.
_SCHEME_RE = re.compile(rf"(?i)(?<![a-z])(?:https?|hxxps?)://[^{_STOP}]+")
_BARE_RE = re.compile(
    rf"(?<![{_L}@.])((?:[{_L}]{{1,63}}\.)+(?:[a-zA-Z]{{2,24}}|xn--[a-zA-Z0-9\-]{{2,59}}))"
    rf"(?![{_L}])(?::\d{{2,5}})?(?:/[^{_STOP}]*)?"
)
_TRAILING = ".,;:!?…"
_DOTS = str.maketrans({"。": ".", "．": ".", "｡": "."})  # browsers treat these as "." in hostnames


@dataclass
class Finding:
    code: str      # short_link | idn_domain | brand_impersonation | lookalike_domain | userinfo_trick | bad_punycode
    reason: str    # English, shown in the red-flag list


@dataclass
class UrlInfo:
    raw: str             # as written in the message (display only, never fetched)
    host: str            # lowercase, punycode decoded (what the scammer wants the seller to read)
    host_ascii: str      # punycode form
    lookup_url: str      # what the reputation API gets (a string; we never request it)
    official: bool
    findings: list[Finding] = field(default_factory=list)


def _prep(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(_DOTS)


def _linky_bare(host: str, whole: str, tld: str) -> bool:
    """Bare domain with a TLD not in BARE_TLDS (e.g. .sbs-style new TLDs we have not listed yet)."""
    if tld in FILE_EXTS:
        return False
    if len(whole) > len(host):  # has a path or port
        return True
    name, raw_tld = host.rsplit(".", 1)
    name = skeleton(name)  # without a path the TLD must be lowercase, so "Anne-Marie.Lee" is not a link
    return raw_tld.islower() and ("-" in name or any(b in name for b in OFFICIAL_DOMAINS))


def extract_urls(text: str) -> list[str]:
    """Links in order of appearance, de-duplicated. Emails are not links."""
    work = _prep(text)
    found: list[tuple[int, str]] = []
    for m in _SCHEME_RE.finditer(work):
        found.append((m.start(), m.group(0).rstrip(_TRAILING)))
    masked = _SCHEME_RE.sub(lambda m: " " * len(m.group(0)), work)
    for m in _BARE_RE.finditer(masked):
        tld = m.group(1).rsplit(".", 1)[-1].lower()
        if tld in BARE_TLDS or tld.startswith("xn--") or _linky_bare(m.group(1), m.group(0), tld):
            found.append((m.start(), m.group(0).rstrip(_TRAILING)))
    seen, out = set(), []
    for _, u in sorted(found):
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out


# ---------------------------------------------------------------- normalisation helpers
def _decode_host(host: str) -> tuple[str, bool, bool]:
    """(unicode host, was_idn, bad_punycode)."""
    labels, idn, bad = [], False, False
    for label in host.split("."):
        if label.startswith("xn--"):
            idn = True
            try:
                label = label.encode("ascii").decode("idna")
            except (UnicodeError, ValueError):
                bad = True
        elif not label.isascii():
            idn = True
        labels.append(label)
    return ".".join(labels), idn, bad


def _to_ascii(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        return host


def skeleton(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.translate(CONFUSABLES)


def registrable(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _is_under(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


# ---------------------------------------------------------------- the check
def check_url(raw: str) -> UrlInfo:
    has_scheme = "://" in raw
    parts = urlsplit(raw if has_scheme else "http://" + raw)
    host = (parts.hostname or "").lower().rstrip(".")
    host_u, idn, bad_puny = _decode_host(host)
    host_u = host_u.lower()
    host_a = _to_ascii(host_u) if not bad_puny else host
    path = parts.path + (("?" + parts.query) if parts.query else "")
    info = UrlInfo(raw=raw, host=host_u, host_ascii=host_a, lookup_url=f"http://{host_a}{path}",
                   official=False)

    if "@" in parts.netloc:
        info.findings.append(Finding("userinfo_trick",
                                     f"The real site is {host_u}; the text before '@' is only a disguise."))
    for domain in SHORTENERS:
        if _is_under(host_u, domain):
            info.findings.append(Finding("short_link",
                                         "Short link hides the real destination. RepSafe does not open it."))
            return info  # nothing else to learn without expanding it
    for brand, domains in OFFICIAL_DOMAINS.items():
        if any(_is_under(host_u, d) for d in domains) and not idn and not info.findings:
            info.official = True
            return info

    if bad_puny:
        info.findings.append(Finding("bad_punycode", "Malformed international domain name (xn--)."))
    if idn:
        info.findings.append(Finding("idn_domain",
                                     f"Uses non-Latin look-alike letters: {host_u} (xn-- form: {host_a})."))

    reg = registrable(host_u)
    suffix_len = len(reg.split(".")) - 1
    labels = [lab for lab in host_u.split(".")[: -suffix_len or None] if lab and lab != "www"]
    brand_hit = None
    for brand in OFFICIAL_DOMAINS:
        label_name = BRAND_LABEL[brand]
        for lab in labels:
            sk = skeleton(lab)
            squashed = sk.replace("-", "").replace("_", "")
            if brand in sk or brand in squashed:
                brand_hit = (brand, "brand_impersonation",
                             f"Uses the name {label_name} but is not an official {label_name} domain ({reg}).")
                break
            limit = 2 if len(brand) >= 8 else 1
            # whole label, then each "-" / "_" part: "shoppee-tw" -> "shoppee" (typo + country suffix, BUG-004)
            parts = [squashed] + [p for p in re.split(r"[-_]", sk) if len(p) >= 4]
            if any(abs(len(p) - len(brand)) <= limit and levenshtein(p, brand) <= limit for p in parts):
                brand_hit = (brand, "lookalike_domain",
                             f"Looks like {label_name} with letters changed ({reg}); not an official domain.")
                break
        if brand_hit:
            break
    if brand_hit:
        info.findings.append(Finding(brand_hit[1], brand_hit[2]))
    return info


def check_text(text: str) -> list[UrlInfo]:
    return [check_url(u) for u in extract_urls(text)]


# Function declaration (for Gemini function calling if we switch to it; see docs/engineering/architecture.md 4)
FUNCTION_DECLARATION = {
    "name": "check_domain_impersonation",
    "description": "Decode punycode and compare a link's host with official Shopee / Carousell / Ruten domains. "
                   "Never opens the link.",
    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
}
