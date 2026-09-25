// POST /api/mcp — Vibe Check's agent interface (JSON-RPC 2.0, hand-rolled, zero deps).
//
// Tools:
//   get_lab_state    — current round, its cards, every swipe decision so far
//   get_cards        — cards for a round (key, name, image URL, family, traits)
//   get_taste_profile— keep/pass analysis across rounds
//   record_decision  — log one swipe; written straight into Edge Config
//   complete_round   — signal a finished round with its full log
//
// The live loop: the browser calls record_decision per swipe. This function
// writes the decision directly into Edge Config — the canonical store that
// get_lab_state serves — via the Vercel API (VERCEL_API_TOKEN, server-side
// only). No email relay, no poller, no third party.

const EC_ID = process.env.EDGE_CONFIG_ID;
const EC_TOKEN = process.env.EDGE_CONFIG_TOKEN;
const VERCEL_API_TOKEN = process.env.VERCEL_API_TOKEN;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id",
  "Access-Control-Max-Age": "86400",
};

const SERVER_INFO = { name: "vibe-check", version: "1.0.0" };
const PROTOCOL_VERSION = "2025-06-18";

// --- helpers ---------------------------------------------------------------

async function roundsData(host) {
  const r = await fetch(`https://${host}/data/rounds.json`);
  if (!r.ok) throw new Error("rounds.json unavailable");
  return r.json();
}

async function ecGet(key) {
  if (!EC_ID || !EC_TOKEN) return null;
  try {
    const r = await fetch(`https://edge-config.vercel.com/${EC_ID}/item/${key}`, {
      headers: { Authorization: "Bearer " + EC_TOKEN },
    });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

// Summary of name rounds + decisions for get_lab_state.
async function nameRoundSummary() {
  const nr = (await ecGet("name_rounds")) || { current: 0, rounds: {} };
  const ndec = (await ecGet("name_decisions")) || {};
  const out = {};
  for (const [n, rd] of Object.entries(nr.rounds || {})) {
    const cards = rd.cards || [];
    const dec = ndec["n" + n] || {};
    out["n" + n] = {
      card_count: cards.length,
      decided: Object.keys(dec).length,
      keeps: Object.entries(dec).filter(([, v]) => v.d === "keep").map(([k]) => k),
      passes: Object.entries(dec).filter(([, v]) => v.d === "pass").map(([k]) => k),
    };
  }
  return { current: nr.current || 0, rounds: out };
}

// --- Edge Config writes (via the Vercel API; server-side token, never exposed) ---

async function vcApi(method, path, body) {
  if (!VERCEL_API_TOKEN) throw new Error("VERCEL_API_TOKEN not configured");
  const res = await fetch("https://api.vercel.com" + path, {
    method,
    headers: {
      Authorization: "Bearer " + VERCEL_API_TOKEN,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error("vercel api " + res.status);
  return res.json();
}

async function ecItemRaw(key) {
  const items = await vcApi("GET", `/v1/edge-config/${EC_ID}/items`);
  const list = Array.isArray(items) ? items : items.items || [];
  const found = list.find((it) => it.key === key);
  return found ? found.value : undefined;
}

// Persist one swipe decision. Logo rounds use store "decisions" with bucket
// "2"; name rounds use store "name_decisions" with bucket "n1".
// decision null/"undo" deletes the key (undo support).
async function persistDecision(tag, key, decision) {
  const isName = tag[0] === "n";
  const store = isName ? "name_decisions" : "decisions";
  const bucket = isName ? tag : tag.slice(1);
  const current = (await ecItemRaw(store)) || {};
  const roundBucket = { ...(current[bucket] || {}) };
  if (decision === null || decision === "undo") delete roundBucket[key];
  else roundBucket[key] = { d: decision, ts: Date.now() };
  const next = { ...current, [bucket]: roundBucket };
  await vcApi("PATCH", `/v1/edge-config/${EC_ID}/items`, {
    items: [{ operation: "upsert", key: store, value: next }],
  });
  return { store, bucket };
}

// Record a completed-round event for the generation watcher.
async function recordRoundEvent(tag, keeps, total) {
  try {
    const events = (await ecItemRaw("round_events")) || {};
    events[tag] = { keeps, total, completed_at: Date.now() };
    await vcApi("PATCH", `/v1/edge-config/${EC_ID}/items`, {
      items: [{ operation: "upsert", key: "round_events", value: events }],
    });
  } catch (e) {
    console.error("round event write failed:", e.message);
  }
}

// --- tools -----------------------------------------------------------------

const TOOLS = [
  {
    name: "get_lab_state",
    description: "Current logo round and name round, their cards, and every swipe decision recorded so far across all rounds.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_cards",
    description: "List the logo cards for a round (key, name, image URL, family, traits).",
    inputSchema: {
      type: "object",
      properties: { round: { type: "integer", description: "Round number; defaults to current." } },
      additionalProperties: false,
    },
  },
  {
    name: "get_name_cards",
    description: "List the name cards for a name round (key, name, generating team, rationale).",
    inputSchema: {
      type: "object",
      properties: { round: { type: "integer", description: "Name round number; defaults to current." } },
      additionalProperties: false,
    },
  },
  {
    name: "get_taste_profile",
    description: "Keep/pass analysis: which logo traits (shape, finish, palette, family) and which name-generating teams the user keeps vs passes.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "record_decision",
    description: "Log one swipe: keep, pass, or null to clear (undo). Round is a logo-round number or an \"n<N>\" name round. Written directly to the canonical Edge Config store.",
    inputSchema: {
      type: "object",
      properties: {
        round: { type: ["integer", "string"] },
        key: { type: "string" },
        decision: { type: ["string", "null"], enum: ["keep", "pass", null] },
      },
      required: ["round", "key", "decision"],
      additionalProperties: false,
    },
  },
  {
    name: "complete_round",
    description: "Signal a finished round with its full decision log. Round is a logo-round number or an \"n<N>\" name round.",
    inputSchema: {
      type: "object",
      properties: {
        round: { type: ["integer", "string"] },
        keeps: { type: "integer" },
        total: { type: "integer" },
      },
      required: ["round", "keeps", "total"],
      additionalProperties: false,
    },
  },
];

function textResult(obj) {
  return { content: [{ type: "text", text: JSON.stringify(obj, null, 2) }] };
}

async function callTool(name, args, host) {
  const rounds = await roundsData(host);
  const current = rounds.current_round;

  switch (name) {
    case "get_lab_state": {
      const decisions = (await ecGet("decisions")) || {};
      const perRound = {};
      for (const [rn, rd] of Object.entries(rounds.rounds)) {
        const cards = rd.cards || [];
        const dec = decisions[rn] || {};
        perRound[rn] = {
          kind: rd.kind, note: rd.note,
          card_count: cards.length,
          decided: Object.keys(dec).length,
          keeps: Object.entries(dec).filter(([, v]) => v.d === "keep").map(([k]) => k),
          passes: Object.entries(dec).filter(([, v]) => v.d === "pass").map(([k]) => k),
        };
      }
      return textResult({ current_round: current, rounds: perRound,
        name_rounds: await nameRoundSummary() });
    }

    case "get_name_cards": {
      const nr = await ecGet("name_rounds");
      const n = String(args.round || (nr && nr.current) || 0);
      const rd = nr && nr.rounds && nr.rounds[n];
      if (!rd) throw new Error("no such name round: " + n);
      return textResult({ round: Number(n),
        cards: (rd.cards || []).map((c) => ({ key: c.key, name: c.name, team: c.team, note: c.note })) });
    }

    case "get_cards": {
      const rn = String(args.round || current);
      const rd = rounds.rounds[rn];
      if (!rd) throw new Error("no such round: " + rn);
      const cards = (rd.cards || []).map((c) => ({
        key: c.key, name: c.name, image: `https://${host}/${c.file}`,
        family: c.family, traits: c.traits,
      }));
      return textResult({ round: Number(rn), cards });
    }

    case "get_taste_profile": {
      const decisions = (await ecGet("decisions")) || {};
      const byTrait = {};
      const bump = (traits, kept) => {
        for (const [dim, val] of Object.entries(traits || {})) {
          const k = dim + ":" + val;
          byTrait[k] = byTrait[k] || { keep: 0, pass: 0 };
          byTrait[k][kept ? "keep" : "pass"] += 1;
        }
      };
      const r1traits = { shape: "mixed", finish: "3d-glossy", palette: "brand" };
      for (const k of rounds.rounds["1"].keeps || []) bump({ ...r1traits, card: k }, true);
      for (const [rn, rd] of Object.entries(rounds.rounds)) {
        if (!rd.cards) continue;
        const dec = decisions[rn] || {};
        for (const c of rd.cards) {
          const d = dec[c.key];
          if (!d || !d.d) continue;
          bump(c.traits, d.d === "keep");
          bump({ family: c.family }, d.d === "keep");
        }
      }
      const ranked = Object.entries(byTrait)
        .map(([trait, s]) => ({ trait, ...s, total: s.keep + s.pass,
          keep_rate: Math.round((s.keep / (s.keep + s.pass)) * 100) / 100 }))
        .sort((a, b) => b.total - a.total);
      // Name taste: keep/pass rates per generating team.
      const nr = await ecGet("name_rounds");
      const ndec = (await ecGet("name_decisions")) || {};
      const byTeam = {};
      if (nr && nr.rounds) {
        for (const [n, rd] of Object.entries(nr.rounds)) {
          const dec = ndec["n" + n] || {};
          for (const c of rd.cards || []) {
            const d = dec[c.key];
            if (!d || !d.d) continue;
            const t = "name-team:" + (c.team || "?");
            byTeam[t] = byTeam[t] || { keep: 0, pass: 0 };
            byTeam[t][d.d === "keep" ? "keep" : "pass"] += 1;
          }
        }
      }
      const nameTeams = Object.entries(byTeam)
        .map(([trait, s]) => ({ trait, ...s, total: s.keep + s.pass,
          keep_rate: Math.round((s.keep / (s.keep + s.pass)) * 100) / 100 }))
        .sort((a, b) => b.total - a.total);
      return textResult({ traits: ranked, name_teams: nameTeams });
    }

    case "record_decision": {
      const { round, key, decision } = args;
      if (!round || !key || !["keep", "pass", null].includes(decision))
        throw new Error("round, key, decision (keep|pass|null) required");
      const tag = typeof round === "number" ? "r" + round : String(round);
      const where = await persistDecision(tag, key, decision);
      return textResult({ ok: true, persisted: where.store + "/" + where.bucket });
    }

    case "complete_round": {
      const { round, keeps, total } = args;
      if (!round) throw new Error("round required");
      const tag = typeof round === "number" ? "r" + round : String(round);
      await recordRoundEvent(tag, keeps || 0, total || 0);
      return textResult({ ok: true });
    }

    default:
      return null;
  }
}

// --- transport ---------------------------------------------------------------

const hits = new Map();
const ipOf = (req) =>
  req.headers["x-forwarded-for"]?.split(",")[0]?.trim() || req.headers["x-real-ip"] || "unknown";

module.exports = async (req, res) => {
  for (const [k, v] of Object.entries(CORS)) res.setHeader(k, v);
  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method === "GET") {
    return res.status(200).json({
      name: SERVER_INFO.name, version: SERVER_INFO.version,
      protocolVersion: PROTOCOL_VERSION, transport: "streamable-http",
      endpoint: `https://${req.headers.host}/api/mcp`,
      tools: TOOLS.map((t) => t.name),
    });
  }
  if (req.method !== "POST") return res.status(405).end();

  const now = Date.now();
  const ip = ipOf(req);
  const row = hits.get(ip);
  if (!row || now > row.reset) hits.set(ip, { count: 1, reset: now + 60000 });
  else if (++row.count > 120)
    return res.status(200).json({ jsonrpc: "2.0", id: null,
      error: { code: -32000, message: "Rate limited — slow down and retry." } });

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = null; } }
  const ok = (id, result) => res.status(200).json({ jsonrpc: "2.0", id, result });
  const err = (id, code, message) => res.status(200).json({ jsonrpc: "2.0", id: id ?? null, error: { code, message } });

  if (!body || typeof body !== "object" || Array.isArray(body))
    return err(null, -32600, "Invalid request.");
  const { id, method, params } = body;
  try {
    switch (method) {
      case "initialize":
        return ok(id, { protocolVersion: PROTOCOL_VERSION,
          capabilities: { tools: { listChanged: false } }, serverInfo: SERVER_INFO,
          instructions: "Vibe Check: endless swipe decks for logos and names. Watch get_lab_state while the user swipes; generate the next round from get_taste_profile. Logo rounds go through rounds.json + redeploy; name rounds are written live to the name_rounds Edge Config item." });
      case "notifications/initialized":
      case "notifications/cancelled":
        return res.status(202).end();
      case "ping": return ok(id, {});
      case "tools/list": return ok(id, { tools: TOOLS });
      case "resources/list": return ok(id, { resources: [] });
      case "tools/call": {
        const out = await callTool(params?.name, params?.arguments || {}, req.headers.host);
        if (!out) return err(id, -32602, `Unknown tool: ${params?.name}`);
        return ok(id, out);
      }
      default:
        if (id === undefined || id === null) return res.status(202).end();
        return err(id, -32601, `Method not found: ${method}`);
    }
  } catch (e) {
    console.error("[mcp]", e);
    return ok(id, { content: [{ type: "text", text: "Tool failed: " + e.message }], isError: true });
  }
};
