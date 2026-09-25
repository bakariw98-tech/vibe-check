#!/usr/bin/env python3
"""Seed / append a Vibe Check name round in Edge Config.

Usage:
  python3 seed_names.py <round_number> [--hold]
  python3 seed_names.py --set-current <N>

Flags:
  --hold           seed BATCHES[N] but leave name_rounds.current untouched,
                   so the new round stages silently while the user is mid-round
  --set-current N  set name_rounds.current=N after validating round N is
                   already seeded (no seeding performed)

With neither flag, behaves as before: seed the batch and advance current
to at least the seeded round.

Round 1 is the hand-built three-team seed:
  team a — the real brief, asked as "what does the experience feel like?"
  team b — metaphor team: adjacent worlds (arcade, playground, stage, fair)
  team c — wrong team: unrelated categories (sport, music, neighborhood,
           physical object, natural phenomenon), briefed on the product after
Round 2: 20 cards, same method (making/workshop/studio metaphors for team b).
Round 3: 60 cards, same method — the first endless-refill batch. Names are
  kept EASY: simple, natural, easy to say/spell/remember, no tortured
  spellings; a few strange ones protected, wildcards kept.
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
    3: [
        # team a — the brief as feeling (type words, a real app appears in
        # seconds, try it instantly in the feed, creators own the room).
        # Rule: EASY — say it once, spell it once, remember it forever.
        card("n3-saygo", "Saygo", "a", "say it, go play it"),
        card("n3-typelive", "Typelive", "a", "type it and it's already live"),
        card("n3-wordplay", "Wordplay", "a", "words you can play"),
        card("n3-aloud", "Aloud", "a", "say it aloud, it's real"),
        card("n3-instant", "Instant", "a", "the whole feeling in one word"),
        card("n3-blink", "Blink", "a", "built in a blink"),
        card("n3-poof", "Poof", "a", "it just appears, like magic"),
        card("n3-tada", "Tada", "a", "the reveal moment, every single time"),
        card("n3-typecast", "Typecast", "a", "typed, then broadcast to the feed"),
        card("n3-adlib", "Adlib", "a", "made up on the spot, instantly playable"),
        card("n3-improv", "Improv", "a", "unscripted creation, live"),
        card("n3-freestyle", "Freestyle", "a", "straight from words to app, no script"),
        card("n3-oncue", "Oncue", "a", "appears right on cue"),
        card("n3-showtime", "Showtime", "a", "every build is a premiere"),
        card("n3-firsttry", "Firsttry", "a", "first to try what someone dreamed up"),
        card("n3-playable", "Playable", "a", "everything here opens and plays"),
        card("n3-tryout", "Tryout", "a", "every post is a tryout you can join"),
        card("n3-dreamplay", "Dreamplay", "a", "daydreams you can play by tonight"),
        card("n3-thinkmade", "Thinkmade", "a", "think it, it's made"),
        card("n3-sayit", "Sayit", "a", "just say it, it's already built"),
        card("n3-happen", "Happen", "a", "make it happen, watch it happen"),
        card("n3-riff", "Riff", "a", "builders riffing live in the feed"),
        card("n3-freshmade", "Freshmade", "a", "made fresh, seconds ago"),
        card("n3-keystroke", "Keystroke", "a", "one keystroke from idea to app"),
        # team b — metaphor team, blind to the product (making / workshop /
        # studio / play worlds). No n1/n2 metaphor words reused.
        card("n3-studio", "Studio", "b", "the studio where things get made"),
        card("n3-foundry", "Foundry", "b", "raw ideas cast into shape"),
        card("n3-bakery", "Bakery", "b", "fresh apps, still warm from the oven"),
        card("n3-kitchen", "Kitchen", "b", "where the magic gets cooked"),
        card("n3-sandbox", "Sandbox", "b", "build and play in the sand"),
        card("n3-toybox", "Toybox", "b", "a box full of things to try"),
        card("n3-playhouse", "Playhouse", "b", "a whole house built for play"),
        card("n3-circus", "Circus", "b", "every act is playable"),
        card("n3-carnival", "Carnival", "b", "wander, try every booth"),
        card("n3-garage", "Garage", "b", "built in the garage, like all great things"),
        card("n3-shed", "Shed", "b", "the shed out back where things get made"),
        card("n3-lab", "Lab", "b", "the experiment you can play"),
        card("n3-mill", "Mill", "b", "ideas ground into apps daily"),
        card("n3-press", "Press", "b", "hot off the press"),
        card("n3-mint", "Mint", "b", "fresh-minted, straight from someone's head"),
        card("n3-sketch", "Sketch", "b", "every app starts as a sketch"),
        card("n3-loom", "Loom", "b", "weave words into something playable"),
        card("n3-darkroom", "Darkroom", "b", "ideas develop in the dark"),
        card("n3-greenroom", "Greenroom", "b", "hang with creators before the show"),
        card("n3-matinee", "Matinee", "b", "the afternoon show, every day"),
        # team c — wrong team: genuinely unrelated categories (sport, music
        # movement, neighborhood, physical object, magazine/print, natural
        # phenomenon). No n1/n2 words reused.
        card("n3-dugout", "Dugout", "c", "sport — where the whole team gathers"),
        card("n3-tailgate", "Tailgate", "c", "sport — the party before the game"),
        card("n3-chorus", "Chorus", "c", "music — everyone sings it together"),
        card("n3-mixtape", "Mixtape", "c", "music — passed hand to hand"),
        card("n3-slowdance", "Slowdance", "c", "music movement — the part everyone remembers"),
        card("n3-blockparty", "Blockparty", "c", "neighborhood — the whole street shows up"),
        card("n3-cornerstore", "Cornerstore", "c", "neighborhood — everybody knows your name"),
        card("n3-culdesac", "Culdesac", "c", "neighborhood — the quiet street where things happen"),
        card("n3-porch", "Porch", "c", "neighborhood — where the block gathers at dusk"),
        card("n3-fireescape", "Fireescape", "c", "object — the city's front porch"),
        card("n3-lunchbox", "Lunchbox", "c", "object — packed with something good"),
        card("n3-thermos", "Thermos", "c", "object — keeps the good stuff warm"),
        card("n3-postcard", "Postcard", "c", "print — wish you were here"),
        card("n3-billboard", "Billboard", "c", "print — big, loud, unmissable"),
        card("n3-aurora", "Aurora", "c", "phenomenon — the sky doing something impossible"),
        card("n3-monsoon", "Monsoon", "c", "phenomenon — when it rains, it pours"),
    ],
}


def get_name_rounds():
    """Fetch the current name_rounds Edge Config item (or {})."""
    items = api("GET", f"/v1/edge-config/{EC_ID}/items")
    if isinstance(items, dict):
        items = items.get("items", [])
    for it in items:
        if it.get("key") == "name_rounds":
            return it.get("value") or {}
    return {}


def put_name_rounds(value):
    api("PATCH", f"/v1/edge-config/{EC_ID}/items",
        {"items": [{"operation": "upsert", "key": "name_rounds", "value": value}]})


def set_current(n):
    current = get_name_rounds()
    rounds = current.get("rounds", {})
    if str(n) not in rounds:
        print(f"round {n} is not seeded; current not changed")
        sys.exit(1)
    current["current"] = n
    put_name_rounds(current)
    print(f"set name_rounds.current={n} (round has {len(rounds[str(n)]['cards'])} cards)")


def main():
    args = sys.argv[1:]
    hold = "--hold" in args
    set_n = None
    rest = []
    skip_next = False
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a == "--set-current":
            set_n = int(args[i + 1])
            skip_next = True
        elif a.startswith("--set-current="):
            set_n = int(a.split("=", 1)[1])
        elif a == "--hold":
            continue
        else:
            rest.append(a)
    if set_n is not None:
        set_current(set_n)
        return
    rnd = int(rest[0]) if rest else 1
    batch = BATCHES.get(rnd)
    if not batch:
        print(f"no batch defined for round {rnd}")
        sys.exit(1)
    current = get_name_rounds()
    current.setdefault("rounds", {})
    current["rounds"][str(rnd)] = {
        "n": rnd, "method": "three-team",
        "cards": batch,
    }
    if not hold:
        current["current"] = max(current.get("current", 0), rnd)
    put_name_rounds(current)
    print(f"seeded name round {rnd}: {len(batch)} cards (current={current.get('current')})"
          + (" [held — current untouched]" if hold else ""))


if __name__ == "__main__":
    main()
