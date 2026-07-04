#!/usr/bin/env python3
"""LinkedIn job search via public jobs-guest endpoints. No auth, no browser, stdlib only.

Personal use only — automated access is against LinkedIn's ToS. Keep volume low.

Usage:
  linkedin_jobs.py search --query "product manager intern" --location "United States" \
                          [--jobage 7] [--remote remote|hybrid|onsite] [--page 1] [--limit 20]
  linkedin_jobs.py detail <jobId | jobs/view URL | urn:li:jobPosting:ID>

search: prints {"meta":..., "results":[{id,title,company,location,date,url}, ...]}
        results are sorted newest-first by posting date (freshness).
detail: prints {id,title,company,location,description,criteria,url,applyUrl}
Errors go to stderr as {"error","code"} with exit code 1.
"""
import argparse
import html as _html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# posted-within window (seconds) — LinkedIn f_TPR
JOBAGE = {1: "r86400", 7: "r604800", 14: "r1209600", 30: "r2592000"}
# workplace type — LinkedIn f_WT
WT = {"onsite": "1", "remote": "2", "hybrid": "3"}
# experience level — LinkedIn f_E: 1 Internship, 2 Entry, 3 Associate, 4 Mid-Senior, 5 Director, 6 Exec


def title_ok(title, include, exclude):
    """Keep card only if title has >=1 include term (when given) and no exclude term."""
    t = (title or "").lower()
    inc = [w.strip().lower() for w in include.split(",") if w.strip()]
    exc = [w.strip().lower() for w in exclude.split(",") if w.strip()]
    if inc and not any(w in t for w in inc):
        return False
    if exc and any(w in t for w in exc):
        return False
    return True


def die(msg, code):
    sys.stderr.write(json.dumps({"error": msg, "code": code}) + "\n")
    sys.exit(1)


def fetch(url, tries=4):
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                return ""
            if e.code in (429, 500, 502, 503, 504):  # rate-limit / transient -> back off
                time.sleep(2 ** i)
                continue
            die(f"HTTP {e.code} from LinkedIn", f"HTTP_{e.code}")
        except Exception as e:  # noqa: BLE001 - network/timeout -> retry
            last = e
            time.sleep(2 ** i)
    die(f"request failed: {last}", "FETCH_FAILED")


def clean(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)  # strip tags
    return _html.unescape(re.sub(r"\s+", " ", s)).strip()


def parse_cards(page):
    out = []
    parts = re.split(r'data-entity-urn="urn:li:jobPosting:(\d+)"', page)
    # parts = [prefix, id1, chunk1, id2, chunk2, ...]
    for i in range(1, len(parts), 2):
        jid = parts[i]
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        title = re.search(r'base-search-card__title"[^>]*>(.*?)</h3>', chunk, re.S)
        comp = re.search(r'base-search-card__subtitle"[^>]*>\s*<a[^>]*>(.*?)</a>', chunk, re.S)
        if not comp:
            comp = re.search(r'base-search-card__subtitle"[^>]*>(.*?)</h4>', chunk, re.S)
        loc = re.search(r'job-search-card__location"[^>]*>(.*?)</span>', chunk, re.S)
        date = re.search(r'listdate[^"]*"\s+datetime="([^"]*)"', chunk)
        url = re.search(r'base-card__full-link"[^>]*href="([^"]*)"', chunk)
        if not url:
            url = re.search(r'href="(https://[^"]*/jobs/view/[^"]*)"', chunk)
        out.append({
            "id": jid,
            "title": clean(title.group(1)) if title else "",
            "company": clean(comp.group(1)) if comp else "",
            "location": clean(loc.group(1)) if loc else "",
            "date": date.group(1) if date else "",
            "url": (url.group(1).split("?")[0] if url else f"https://www.linkedin.com/jobs/view/{jid}"),
        })
    return out


def cmd_search(a):
    p = {}
    if a.query:
        p["keywords"] = a.query
    if a.location:
        p["location"] = a.location
    if a.jobage:
        if a.jobage not in JOBAGE:
            die(f"--jobage must be one of {sorted(JOBAGE)}", "BAD_ARG")
        p["f_TPR"] = JOBAGE[a.jobage]
    if a.remote:
        if a.remote not in WT:
            die("--remote must be remote|hybrid|onsite", "BAD_ARG")
        p["f_WT"] = WT[a.remote]
    if a.explevel:
        p["f_E"] = a.explevel  # e.g. "1" (Internship) or "1,2"
    p["start"] = str((a.page - 1) * 10)
    url = SEARCH_URL + "?" + urllib.parse.urlencode(p)
    cards = parse_cards(fetch(url))
    if a.title_include or a.title_exclude:
        cards = [c for c in cards if title_ok(c["title"], a.title_include, a.title_exclude)]
    cards.sort(key=lambda c: c.get("date") or "", reverse=True)  # newest first
    if a.limit and a.limit > 0:
        cards = cards[: a.limit]
    print(json.dumps(
        {"meta": {"count": len(cards), "page": a.page, "url": url}, "results": cards},
        ensure_ascii=False, indent=2,
    ))


def normalize_id(s):
    for pat in (r"urn:li:jobPosting:(\d+)", r"-(\d{6,})(?:\?|$|/)", r"/(\d{6,})(?:\?|$|/)", r"^(\d{6,})$"):
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return None


def cmd_detail(a):
    jid = normalize_id(a.id)
    if not jid:
        die(f'could not parse a job id from "{a.id}"', "BAD_ID")
    page = fetch(f"{DETAIL_URL}/{jid}")
    if not page:
        die("job not found", "NOT_FOUND")

    def one(pat):
        m = re.search(pat, page, re.S)
        return clean(m.group(1)) if m else ""

    title = one(r'topcard__title"[^>]*>(.*?)</h[12]>')
    company = one(r'topcard__org-name-link[^>]*>(.*?)</a>')
    location = one(r'topcard__flavor--bullet"[^>]*>(.*?)</span>')
    desc = one(r'show-more-less-html__markup[^>]*>(.*?)</div>') or one(r'description__text[^>]*>(.*?)</section>')
    crit = re.findall(
        r'description__job-criteria-subheader"[^>]*>(.*?)</h3>\s*<span[^>]*description__job-criteria-text[^>]*>(.*?)</span>',
        page, re.S,
    )
    criteria = {clean(k): clean(v) for k, v in crit}
    # apply type: offsite (external ATS) jobs carry an "apply-link-offsite" marker in the
    # guest view; Easy Apply jobs do not. Heuristic, but reliable in practice.
    apply_type = "offsite" if "apply-link-offsite" in page else "easy_apply"
    apply_m = re.search(r'href="([^"]*)"[^>]*data-tracking-control-name="public_jobs_apply-link', page)
    print(json.dumps({
        "id": jid,
        "title": title,
        "company": company,
        "location": location,
        "description": desc,
        "criteria": criteria,
        "url": f"https://www.linkedin.com/jobs/view/{jid}",
        "applyType": apply_type,
        "applyUrl": clean(apply_m.group(1)) if apply_m else "",
        "applyNote": (
            "Easy Apply — submitted on LinkedIn while logged in; screening questions are "
            "not readable via the public endpoint. Kit points to the LinkedIn URL."
            if apply_type == "easy_apply" else
            "Offsite — the real apply URL and form are on the company ATS, not LinkedIn. "
            "Resolve the company's Greenhouse/Lever posting (ats_form.py) for the fields."
        ),
    }, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(prog="linkedin_jobs.py", add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="search job listings")
    s.add_argument("--query", "-q", default="")
    s.add_argument("--location", "-l", default="")
    s.add_argument("--jobage", type=int, default=0, help="posted within N days: 1, 7, 14, 30")
    s.add_argument("--remote", default="", help="remote|hybrid|onsite")
    s.add_argument("--explevel", default="", help="LinkedIn f_E: 1 Internship, 2 Entry, 3 Associate (comma-ok, e.g. 1,2)")
    s.add_argument("--title-include", dest="title_include", default="", help="keep only titles containing >=1 of these comma-separated terms")
    s.add_argument("--title-exclude", dest="title_exclude", default="", help="drop titles containing any of these comma-separated terms")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--limit", "-n", type=int, default=0)
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("detail", help="fetch one job's full detail")
    d.add_argument("id", help="jobId, jobs/view URL, or urn:li:jobPosting:ID")
    d.set_defaults(func=cmd_detail)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
