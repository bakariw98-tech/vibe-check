#!/usr/bin/env python3
"""RETIRED (2026-09-25): /api/mcp now writes swipe decisions directly into
Edge Config via the Vercel API — no email relay, no poller needed.
Kept for reference only; do not run.

Vibe Check live poller (Gmail version).

Each swipe on the deck is relayed as an email with a machine-readable subject
("vibe-check r2 keep r2-glass-wave", "vibe-check n1 pass n1-playfeed").
This poller drains those emails, mirrors the decisions into Edge Config
(the canonical store the MCP endpoint serves), and trashes the emails so
the inbox stays clean.

Logo rounds ("r<N>") go to the "decisions" item; name rounds ("n<N>")
go to the "name_decisions" item.

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

SUBJ_RE = re.compile(r"^vibe-check ([rn]\d+) (keep|pass|undo) (\S+)$")
DONE_RE = re.compile(r"^vibe-check ([rn]\d+) complete (\d+)/(\d+) kept$")


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


def ec_read(key):
    try:
        items = api("GET", f"/v1/edge-config/{EC_ID}/items")
        if isinstance(items, dict):
            items = items.get("items", [])
        for it in items:
            if it.get("key") == key:
                return it.get("value") or {}
    except Exception as e:
        print(f"[poller] seed failed ({key}): {e}", flush=True)
    return {}


def ec_write(key, value):
    api("PATCH", f"/v1/edge-config/{EC_ID}/items",
        {"items": [{"operation": "upsert", "key": key, "value": value}]})


def poll_once(state):
    """state: {"decisions": {...}, "name_decisions": {...}} — mutated in place."""
    out = gws("+triage", "--query", 'subject:"vibe-check" newer_than:2d',
              "--max", "50", "--format", "json")
    try:
        msgs = json.loads(out) if out.strip() else []
    except Exception:
        msgs = []
    if not isinstance(msgs, list):
        msgs = msgs.get("messages", msgs.get("results", [])) if isinstance(msgs, dict) else []

    changed = set()
    trash_ids = []
    round_done = None
    for m in msgs:
        mid = m.get("id") or m.get("message_id") or m.get("messageId")
        subj = (m.get("subject") or "").strip()
        m2 = SUBJ_RE.match(subj)
        m3 = DONE_RE.match(subj)
        if m2:
            tag, dec, key = m2.group(1), m2.group(2), m2.group(3)
            store_key = "name_decisions" if tag.startswith("n") else "decisions"
            rnd = tag[1:] if tag.startswith("r") else tag
            bucket = state[store_key].setdefault(rnd, {})
            if dec == "undo":
                bucket.pop(key, None)
            else:
                bucket[key] = {"d": dec, "ts": int(time.time())}
            changed.add(store_key)
            with open(LOG, "a") as f:
                f.write(json.dumps({"round": tag, "key": key, "decision": dec}) + "\n")
            print(f"[poller] {tag} {key} -> {dec}", flush=True)
        elif m3:
            tag = m3.group(1)
            round_done = {"round": tag, "keeps": int(m3.group(2)), "total": int(m3.group(3))}
            print(f"[poller] ROUND {tag} COMPLETE: {m3.group(2)}/{m3.group(3)} kept", flush=True)
        if mid:
            trash_ids.append(mid)

    for store_key in changed:
        try:
            ec_write(store_key, state[store_key])
            n = sum(len(v) for v in state[store_key].values())
            print(f"[poller] flushed {store_key}: {n} decisions", flush=True)
        except Exception as e:
            print(f"[poller] edge-config write failed ({store_key}): {e}", flush=True)

    if trash_ids:
        gws("+trash", *[a for mid in trash_ids for a in ("--message-id", mid)])
        print(f"[poller] trashed {len(trash_ids)} relay emails", flush=True)

    with open(STATUS, "w") as f:
        json.dump({"last_poll": int(time.time()),
                   "decisions": sum(len(v) for v in state["decisions"].values()),
                   "name_decisions": sum(len(v) for v in state["name_decisions"].values()),
                   "round_done": round_done}, f)
    return round_done


def main():
    state = {"decisions": ec_read("decisions"),
             "name_decisions": ec_read("name_decisions")}
    total = sum(len(v) for v in state["decisions"].values()) + \
        sum(len(v) for v in state["name_decisions"].values())
    print(f"[poller] seeded {total} decisions", flush=True)
    if "--once" in sys.argv:
        poll_once(state)
        return
    print("[poller] live", flush=True)
    while True:
        try:
            done = poll_once(state)
            if done:
                print(f"[poller] *** ROUND {done['round']} DONE — generate next round ***", flush=True)
        except Exception as e:
            print(f"[poller] poll error: {e}", flush=True)
        time.sleep(45)


if __name__ == "__main__":
    main()
