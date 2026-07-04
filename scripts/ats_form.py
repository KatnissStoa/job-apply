#!/usr/bin/env python3
"""Fetch the real application form for a job on a public ATS. No auth, no browser, stdlib only.

Greenhouse returns the FULL form (every field, required flag, type, dropdown options).
Lever's public API does not expose custom questions, so it returns the apply URL + the
standard fields only — read the apply page or flag "needs human start" for custom questions.

Usage:
  ats_form.py <url>                         # a Greenhouse or Lever job URL
  ats_form.py greenhouse <token> <job_id>
  ats_form.py lever <company> <posting_id>

Output JSON: {ats, title, company, location, applyUrl,
              fields:[{label, required, type, options}], note}
Errors -> stderr {"error","code"}, exit 1.
"""
import html as _html
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
GH_TYPE = {
    "input_text": "text",
    "textarea": "long_text",
    "input_file": "file",
    "multi_value_single_select": "select",
    "multi_value_multi_select": "multiselect",
}


def die(msg, code):
    sys.stderr.write(json.dumps({"error": msg, "code": code}) + "\n")
    sys.exit(1)


def get_json(url, tries=4):
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                die("job not found on this ATS", "NOT_FOUND")
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            die(f"HTTP {e.code} from ATS", f"HTTP_{e.code}")
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                die(f"request failed: {e}", "FETCH_FAILED")
            time.sleep(2 ** i)


def greenhouse(token, job_id):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}?questions=true")
    fields = []
    for q in d.get("questions", []):
        f = (q.get("fields") or [{}])[0]
        opts = [v.get("label") for v in (f.get("values") or []) if v.get("label")]
        fields.append({
            "label": q.get("label", ""),
            "required": bool(q.get("required")),
            "type": GH_TYPE.get(f.get("type"), f.get("type") or "text"),
            "options": opts,
        })
    jd = re.sub(r"<[^>]+>", " ", _html.unescape(d.get("content", "")))
    jd = re.sub(r"[ \t]+", " ", _html.unescape(jd)).strip()
    return {
        "ats": "greenhouse",
        "title": d.get("title", ""),
        "company": d.get("company_name", ""),
        "location": (d.get("location") or {}).get("name", ""),
        "applyUrl": d.get("absolute_url", ""),
        "jd": jd,
        "fields": fields,
        "note": "",
    }


def lever(company, posting_id):
    d = get_json(f"https://api.lever.co/v0/postings/{company}/{posting_id}")
    cats = d.get("categories") or {}
    # Lever's public API exposes standard fields only; custom questions are not returned.
    std = [
        {"label": "Full name", "required": True, "type": "text", "options": []},
        {"label": "Email", "required": True, "type": "text", "options": []},
        {"label": "Resume/CV", "required": True, "type": "file", "options": []},
        {"label": "Phone", "required": False, "type": "text", "options": []},
        {"label": "LinkedIn / other URLs", "required": False, "type": "text", "options": []},
    ]
    return {
        "ats": "lever",
        "title": d.get("text", ""),
        "company": company,
        "location": cats.get("location", ""),
        "applyUrl": d.get("applyUrl") or (d.get("hostedUrl", "") + "/apply"),
        "fields": std,
        "note": "Lever's public API does not expose custom application questions. "
                "These are the standard fields; read the apply page for any custom "
                "questions, or flag needs-human-start.",
    }


def from_url(url):
    if "greenhouse.io" in url:
        m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?#]+).*?jobs/(\d+)", url) \
            or re.search(r"greenhouse\.io/([^/?#]+)/jobs/(\d+)", url)
        if not m:
            die("could not parse Greenhouse token/job_id from URL", "BAD_URL")
        return greenhouse(m.group(1), m.group(2))
    if "lever.co" in url:
        m = re.search(r"lever\.co/([^/?#]+)/([0-9a-f\-]{8,})", url)
        if not m:
            die("could not parse Lever company/posting_id from URL", "BAD_URL")
        return lever(m.group(1), m.group(2))
    die("URL is not a recognized Greenhouse or Lever job URL", "UNKNOWN_ATS")


def main():
    a = sys.argv[1:]
    if not a:
        die("usage: ats_form.py <url> | greenhouse <token> <id> | lever <company> <id>", "USAGE")
    if a[0] == "greenhouse" and len(a) == 3:
        out = greenhouse(a[1], a[2])
    elif a[0] == "lever" and len(a) == 3:
        out = lever(a[1], a[2])
    else:
        out = from_url(a[0])
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
