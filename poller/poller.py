#!/usr/bin/env python3
"""Vibe Check live poller (Gmail version).

Each swipe on the deck is relayed as an email with a machine-readable subject
("vibe-check r2 keep r2-glass-wave"). This poller drains those emails, mirrors
the decisions into Edge Config (the canonical store the MCP endpoint serves),
and trashes the emails so the inbox stays clean.

Usage: python3 poller.py [--once]
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.error

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "decisions.jsonl")
STATUS = os.path.join(BASE, "status.json")
EC_ID = "ecfg_xkfara8rxvmpzdhdzzqdjf3ynkmh"
GWS = "/opt/hatch/bin/hatch_gws_cli"

SUBJ_RE = re.compile(r"^vibe-check r(\d+) (keep|pass|undo) (\S+)$")
DONE_RE = re.compile(r"^vibe-check r(\d+) complete (\d+)/(\d+) kept$")


def gws(*args):
    p = subprocess.run([GWS, "gmail", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        print(f"[poller] gmail cli failed: {p.stderr[:200]}", flush=True)
        return ""
    return p.stdout


def api(method, path, data=None):
    url = "https://api.vercel.com" + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    add_surrogate_to_request(req, "custom.vercel", allowed_hosts=["api.vercel.com"])
    return read_json_response(urllib.request.urlopen(req, timeout=30))


def ec_read_decisions():
    try:
        items = api("GET", f"/v1/edge-config/{EC_ID}/items").get("items", [])
        for it in items:
            if it.get("key") == "decisions":
                return it.get("value") or {}
    except Exception as e:
        print(f"[poller] seed failed: {e}", flush=True)
    return {}


def ec_write_decisions(decisions):
    api("PATCH", f"/v1/edge-config/{EC_ID}/items",
        {"items": [{"operation": "upsert", "key": "decisions", "value": decisions}]})


def poll_once(decisions):
    out = gws("+triage", "--query", 'subject:"vibe-check" newer_than:2d',
              "--max", "50", "--format", "json")
    try:
        msgs = json.loads(out) if out.strip() else []
    except Exception:
        msgs = []
    if not isinstance(msgs, list):
        msgs = msgs.get("messages", msgs.get("results", [])) if isinstance(msgs, dict) else []

    changed = False
    trash_ids = []
    round_done = None
    for m in msgs:
        mid = m.get("id") or m.get("message_id") or m.get("messageId")
        subj = (m.get("subject") or "").strip()
        m2 = SUBJ_RE.match(subj)
        m3 = DONE_RE.match(subj)
        if m2:
            rnd, dec, key = m2.group(1), m2.group(2), m2.group(3)
            decisions.setdefault(rnd, {})
            if dec == "undo":
                decisions[rnd].pop(key, None)
            else:
                decisions[rnd][key] = {"d": dec, "ts": int(time.time())}
            changed = True
            with open(LOG, "a") as f:
                f.write(json.dumps({"round": int(rnd), "key": key, "decision": dec}) + "\n")
            print(f"[poller] r{rnd} {key} -> {dec}", flush=True)
        elif m3:
            rnd = m3.group(1)
            round_done = {"round": int(rnd), "keeps": int(m3.group(2)), "total": int(m3.group(3))}
            print(f"[poller] ROUND {rnd} COMPLETE: {m3.group(2)}/{m3.group(3)} kept", flush=True)
        if mid:
            trash_ids.append(mid)

    if changed:
        try:
            ec_write_decisions(decisions)
            print(f"[poller] flushed {sum(len(v) for v in decisions.values())} decisions", flush=True)
        except Exception as e:
            print(f"[poller] edge-config write failed: {e}", flush=True)

    if trash_ids:
        gws("+trash", *[a for mid in trash_ids for a in ("--message-id", mid)])
        print(f"[poller] trashed {len(trash_ids)} relay emails", flush=True)

    with open(STATUS, "w") as f:
        json.dump({"last_poll": int(time.time()), "decisions": sum(len(v) for v in decisions.values()),
                   "round_done": round_done}, f)
    return round_done


def main():
    decisions = ec_read_decisions()
    print(f"[poller] seeded {sum(len(v) for v in decisions.values())} decisions", flush=True)
    if "--once" in sys.argv:
        poll_once(decisions)
        return
    print("[poller] live", flush=True)
    while True:
        try:
            done = poll_once(decisions)
            if done:
                print(f"[poller] *** ROUND {done['round']} DONE — generate next round ***", flush=True)
        except Exception as e:
            print(f"[poller] poll error: {e}", flush=True)
        time.sleep(45)


if __name__ == "__main__":
    main()
