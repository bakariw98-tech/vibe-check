# ✓ vibe check

An endless swipe lab for finding your brand's look — logos **and** names.
You swipe. An agent watches live on the other end and generates the next
round from your taste. It never ends until you say so.

## How it works

1. **Swipe** through a deck of logo concepts (or names) — keep what passes
   the vibe check, pass on the rest. Undo anytime.
2. Every swipe is relayed in real time to the agent on the other end.
3. The agent reads your cumulative taste — what you keep, what you pass —
   and generates a fresh mixed round: variations on your keeps plus wild
   cards so the algorithm never overfits.
4. New rounds keep coming until you call it done.

## The live loop

- The deck (`public/index.html`) reports each decision to `POST /api/mcp`
  (`record_decision`), which relays it via a lightweight email ping.
- `poller/poller.py` drains those pings from Gmail, mirrors every decision
  into Vercel Edge Config (the canonical store), and trashes the pings so
  the inbox stays clean.
- The agent side reads canonical state through the MCP tools
  (`get_lab_state`, `get_cards`, `get_taste_profile`), generates the next
  round, and redeploys — new cards appear in the deck.

No build step, no dependencies. Static frontend + two serverless functions.

## Project layout

```
public/
  index.html        # the swipe deck (mobile-first)
  data/rounds.json  # rounds, cards, image metadata
  logos/r2/         # round 2 logo renders
api/
  mcp.js            # JSON-RPC agent interface (swipe in, state/taste out)
  decisions.js      # canonical decision log
poller/
  poller.py         # gmail -> edge-config live mirror
```

## Deploy

```bash
~/workspace/skills/vercel/bin/deploy.py   # deploys this directory to Vercel
```

Environment variables: `EDGE_CONFIG_ID`, `EDGE_CONFIG_TOKEN`,
`FORMSUBMIT_EMAIL`.
