#!/usr/bin/env python3
"""Seed / append a Vibe Check name round in Edge Config.

Usage: python3 seed_names.py <round_number>
Writes the batch defined in BATCHES[round_number] into the "name_rounds"
Edge Config item (merging with existing rounds).

Round 1 is the hand-built three-team seed:
  team a — the real brief, asked as "what does the experience feel like?"
  team b — metaphor team: adjacent worlds (arcade, playground, stage, fair)
  team c — wrong team: unrelated categories (sport, music, neighborhood,
           physical object, natural phenomenon), briefed on the product after
"""
import json, sys, urllib.request

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

EC_ID = "ecfg_xkfara8rxvmpzdhdzzqdjf3ynkmh"


def api(method, path, data=None):
    url = "https://api.vercel.com" + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    add_surrogate_to_request(req, "custom.vercel", allowed_hosts=["api.vercel.com"])
    return read_json_response(urllib.request.urlopen(req, timeout=30))


def card(key, name, team, note):
    return {"key": key, "name": name, "team": team, "note": note}


BATCHES = {
    1: [
        # team a — the brief as feeling (VIBE: discover like TikTok, try like Roblox, creator-owned)
        card("n1-vibefeed", "Vibefeed", "a", "the anchor — current name, the feeling to beat"),
        card("n1-playfeed", "Playfeed", "a", "the feed you play, not scroll"),
        card("n1-freq", "Freq", "a", "tune into the frequency of what people are making"),
        card("n1-trybal", "Trybal", "a", "try + tribal — the community that tries things"),
        card("n1-livewire", "Livewire", "a", "electric, live, happening now"),
        card("n1-frontrow", "Frontrow", "a", "front row to the creators you follow"),
        card("n1-unboxed", "Unboxed", "a", "try it straight out of the box"),
        card("n1-firstplay", "Firstplay", "a", "be the first to play what someone built"),
        # team b — metaphor team (arcade / playground / stage / fair)
        card("n1-arcade", "Arcade", "b", "a room full of things to try"),
        card("n1-fairground", "Fairground", "b", "wander, try every booth"),
        card("n1-openmic", "Openmic", "b", "anyone can take the stage"),
        card("n1-sideshow", "Sideshow", "b", "the weird wonderful acts down the row"),
        card("n1-playground", "Playground", "b", "built for trying, not watching"),
        card("n1-encore", "Encore", "b", "the crowd loved it — run it back"),
        # team c — wrong team (sport / music / neighborhood / object / phenomenon)
        card("n1-overtime", "Overtime", "c", "sport — the game went long because nobody wanted to leave"),
        card("n1-murmuration", "Murmuration", "c", "phenomenon — starlings moving as one, like a community"),
        card("n1-stoop", "Stoop", "c", "neighborhood — where the whole block gathers"),
        card("n1-bside", "Bside", "c", "music — the deeper cut the real fans love"),
        card("n1-trampoline", "Trampoline", "c", "object — bounce, launch, play"),
        card("n1-grandstand", "Grandstand", "c", "sport — the crowd watching creators do their thing"),
    ],
    2: [
        # team a — the brief as feeling (type words, an app appears, play it instantly)
        card("n2-conjure", "Conjure", "a", "type the words, the app appears like conjured"),
        card("n2-genie", "Genie", "a", "rub the lamp — the wish becomes playable"),
        card("n2-manifest", "Manifest", "a", "think it and it manifests, live in the feed"),
        card("n2-whipup", "Whipup", "a", "whip up a real app in seconds"),
        card("n2-promptly", "Promptly", "a", "built from a prompt, and promptly"),
        card("n2-dreambuilt", "Dreambuilt", "a", "built from a daydream, playable by nightfall"),
        card("n2-vibeship", "Vibeship", "a", "ship the vibe — compound vehicle for the Vibes product"),
        card("n2-thinklive", "Thinklive", "a", "think it and it's already live"),
        # team b — metaphor team (workshop / studio / making worlds)
        card("n2-forge", "Forge", "b", "where raw ideas get hammered into shape"),
        card("n2-greenhouse", "Greenhouse", "b", "ideas grow fast in the warm light"),
        card("n2-treehouse", "Treehouse", "b", "built by hand, everyone climbs up"),
        card("n2-jamroom", "Jamroom", "b", "musicians riff — builders riff here"),
        card("n2-kiln", "Kiln", "b", "raw clay in, finished piece out"),
        card("n2-workbench", "Workbench", "b", "the bench where things get made"),
        # team c — wrong team (music / sport / phenomenon / object / print / neighborhood)
        card("n2-soundcheck", "Soundcheck", "c", "music — the test before the show goes live"),
        card("n2-underdog", "Underdog", "c", "sport — the one nobody saw coming"),
        card("n2-tide", "Tide", "c", "phenomenon — the whole ocean moving one way"),
        card("n2-snowglobe", "Snowglobe", "c", "object — a whole world you can shake and watch"),
        card("n2-zine", "Zine", "c", "print — made by hand, passed around, loved hard"),
        card("n2-alley", "Alley", "c", "neighborhood — where the interesting stuff actually happens"),
    ],
}


def main():
    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    batch = BATCHES.get(rnd)
    if not batch:
        print(f"no batch defined for round {rnd}")
        sys.exit(1)
    items = api("GET", f"/v1/edge-config/{EC_ID}/items")
    if isinstance(items, dict):
        items = items.get("items", [])
    current = {}
    for it in items:
        if it.get("key") == "name_rounds":
            current = it.get("value") or {}
            break
    current.setdefault("rounds", {})
    current["rounds"][str(rnd)] = {
        "n": rnd, "method": "three-team",
        "cards": batch,
    }
    current["current"] = max(current.get("current", 0), rnd)
    api("PATCH", f"/v1/edge-config/{EC_ID}/items",
        {"items": [{"operation": "upsert", "key": "name_rounds", "value": current}]})
    print(f"seeded name round {rnd}: {len(batch)} cards (current={current['current']})")


if __name__ == "__main__":
    main()
