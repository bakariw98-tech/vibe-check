#!/usr/bin/env python3
"""Vibe Check watcher: checks Edge Config for swipe activity and completed rounds.

Compares against watcher/state.json watermark. Prints a report ONLY when
there's something actionable:
  - a round just completed (round_events entry, or all cards decided)
  - 8+ new decisions since last check
Otherwise prints "quiet".

Run: python3 watcher/watch.py
"""
import json, os, sys, urllib.request

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
ROOT = os.path.dirname(HERE)
EC_ID = "ecfg_xkfara8rxvmpzdhdzzqdjf3ynkmh"
NEW_DECISION_THRESHOLD = 8


def api(method, path):
    req = urllib.request.Request(f"https://api.vercel.com{path}", method=method,
                                 headers={"Content-Type": "application/json"})
    add_surrogate_to_request(req, "custom.vercel", allowed_hosts=["api.vercel.com"])
    return read_json_response(urllib.request.urlopen(req, timeout=30))


def ec_items():
    items = api("GET", f"/v1/edge-config/{EC_ID}/items")
    if isinstance(items, dict):
        items = items.get("items", [])
    return {it["key"]: it.get("value") for it in items}


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"decided": {}, "events_seen": []}


def main():
    items = ec_items()
    decisions = items.get("decisions", {}) or {}
    name_decisions = items.get("name_decisions", {}) or {}
    name_rounds = items.get("name_rounds", {}) or {}
    events = items.get("round_events", {}) or {}
    state = load_state()
    seen = state.get("decided", {})
    events_seen = set(state.get("events_seen", []))
    reports = []

    # Logo rounds: card counts from local rounds.json (deploys from here).
    try:
        with open(os.path.join(ROOT, "public/data/rounds.json")) as f:
            rounds = json.load(f).get("rounds", {})
    except Exception:
        rounds = {}

    def check(tag, bucket_key, store, card_count):
        dec = store.get(bucket_key, {}) or {}
        n = len(dec)
        prev = seen.get(tag, 0)
        # completed?
        if n >= card_count and card_count > 0 and tag not in events_seen:
            ev = events.get(tag)
            keeps = [k for k, v in dec.items() if (v or {}).get("d") == "keep"]
            reports.append(
                f"ROUND COMPLETE {tag}: {n}/{card_count} decided, "
                f"{len(keeps)} keeps ({', '.join(keeps) or 'none'})"
                + (f" [event recorded {ev.get('completed_at')}]" if ev else " [no event yet]")
            )
            events_seen.add(tag)
        elif n - prev >= NEW_DECISION_THRESHOLD:
            reports.append(f"ACTIVITY {tag}: {n - prev} new decisions ({prev} -> {n} of {card_count})")
        seen[tag] = n

    for rn, rd in rounds.items():
        cards = rd.get("cards") or []
        if cards:
            check("r" + str(rn), str(rn), decisions, len(cards))
    for n, rd in (name_rounds.get("rounds") or {}).items():
        cards = rd.get("cards") or []
        if cards:
            check("n" + str(n), "n" + str(n), name_decisions, len(cards))

    # Catch round_events entries the count check missed (e.g. events written
    # by complete_round before all decisions synced).
    for tag in events:
        if tag not in events_seen:
            events_seen.add(tag)
            if not any(r.startswith("ROUND COMPLETE " + tag) for r in reports):
                ev = events[tag]
                reports.append(f"ROUND COMPLETE {tag}: event recorded "
                               f"({ev.get('keeps')}/{ev.get('total')} kept)")

    state["decided"] = seen
    state["events_seen"] = sorted(events_seen)
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2)

    if reports:
        print("\n".join(reports))
    else:
        print("quiet")


if __name__ == "__main__":
    main()
