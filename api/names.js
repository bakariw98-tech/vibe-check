// GET /api/names — Vibe Check name rounds (live from Edge Config).
// Name cards are text, so new rounds land here instantly with no redeploy.
module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method !== "GET") return res.status(405).end();
  try {
    const r = await fetch(
      `https://edge-config.vercel.com/${process.env.EDGE_CONFIG_ID}/item/name_rounds`,
      { headers: { Authorization: "Bearer " + process.env.EDGE_CONFIG_TOKEN } }
    );
    const data = r.ok ? await r.json() : null;
    return res.status(200).json(data || { current: 0, rounds: {} });
  } catch (e) {
    return res.status(200).json({ current: 0, rounds: {} });
  }
};
