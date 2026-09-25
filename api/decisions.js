// GET /api/decisions — canonical swipe log (written by the agent loop from the live MQTT feed).
module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method !== "GET") return res.status(405).end();
  try {
    const r = await fetch(
      `https://edge-config.vercel.com/${process.env.EDGE_CONFIG_ID}/item/decisions`,
      { headers: { Authorization: "Bearer " + process.env.EDGE_CONFIG_TOKEN } }
    );
    const data = r.ok ? await r.json() : {};
    return res.status(200).json({ decisions: data || {} });
  } catch (e) {
    return res.status(200).json({ decisions: {} });
  }
};
