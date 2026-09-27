// Copilot endpoint for the static archive site. The browser does retrieval with Pagefind and sends
// the question plus the retrieved passages; this Worker asks Workers AI for a JSON answer with
// verbatim quotations, which the browser then checks against the passages before showing it.
// Nothing is stored or logged.

const SYSTEM_PROMPT =
  'You answer questions about Columbia MAFN course materials using only the numbered passages provided. ' +
  'Return JSON. Each claim must be one sentence supported by a single passage. "source" is that passage number, ' +
  'and "quote" is copied word for word from that passage (at least five words) to prove the claim. Use at most five claims. ' +
  'If the passages do not answer the question, set "insufficient" to true and return no claims. Never use outside knowledge.';

const ANSWER_SCHEMA = {
  type: 'object',
  properties: {
    insufficient: { type: 'boolean' },
    claims: {
      type: 'array',
      maxItems: 5,
      items: {
        type: 'object',
        properties: { text: { type: 'string' }, source: { type: 'integer' }, quote: { type: 'string' } },
        required: ['text', 'source', 'quote'],
      },
    },
  },
  required: ['insufficient', 'claims'],
};

const LIMITS = { question: 600, passages: 8, title: 200, locator: 120, text: 2000 };

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function reply(status, body, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...(origin ? corsHeaders(origin) : {}) },
  });
}

function validate(payload) {
  if (!payload || typeof payload !== 'object') throw new Error('Send a JSON object');
  const question = typeof payload.question === 'string' ? payload.question.trim() : '';
  if (!question || question.length > LIMITS.question) throw new Error(`The question must be 1–${LIMITS.question} characters`);
  const passages = payload.passages;
  if (!Array.isArray(passages) || passages.length < 1 || passages.length > LIMITS.passages) {
    throw new Error(`Send 1–${LIMITS.passages} passages`);
  }
  return {
    question,
    passages: passages.map((p) => {
      if (!p || typeof p.text !== 'string' || typeof p.title !== 'string') throw new Error('Each passage needs a title and text');
      return {
        title: p.title.slice(0, LIMITS.title),
        locator: String(p.locator || '').slice(0, LIMITS.locator),
        text: p.text.slice(0, LIMITS.text),
      };
    }),
  };
}

// Workers AI chat models return either { response } or an OpenAI-style { choices }.
function answerText(result) {
  if (typeof result?.response === 'string') return result.response;
  if (result?.response && typeof result.response === 'object') return JSON.stringify(result.response);
  const message = result?.choices?.[0]?.message?.content;
  if (typeof message === 'string') return message;
  if (message && typeof message === 'object') return JSON.stringify(message);
  throw new Error('The model returned no answer');
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const allowed = env.ALLOWED_ORIGINS.split(',').map((o) => o.trim());
    const trusted = allowed.includes(origin) ? origin : null;
    const { pathname } = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return trusted ? new Response(null, { status: 204, headers: corsHeaders(trusted) }) : new Response(null, { status: 403 });
    }
    if (pathname === '/health' && request.method === 'GET') return reply(200, { status: 'ok', model: env.MODEL }, trusted);
    if (pathname !== '/answer' || request.method !== 'POST') return reply(404, { error: 'Not found' }, trusted);
    if (!trusted) return reply(403, { error: 'This endpoint only serves the archive site' }, null);

    const visitor = request.headers.get('CF-Connecting-IP') || 'unknown';
    const { success } = await env.PER_VISITOR.limit({ key: visitor });
    if (!success) return reply(429, { error: 'Too many questions in a minute. Wait a moment and ask again.' }, trusted);

    let input;
    try {
      if (Number(request.headers.get('Content-Length') || 0) > 32000) throw new Error('Request too large');
      input = validate(await request.json());
    } catch (error) {
      return reply(400, { error: error.message }, trusted);
    }

    const context = input.passages.map((p, i) => `[${i + 1}] ${p.title} (${p.locator})\n${p.text}`).join('\n\n');
    const started = Date.now();
    try {
      const result = await env.AI.run(env.MODEL, {
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `Passages:\n\n${context}\n\nQuestion: ${input.question} /no_think` },
        ],
        max_tokens: 900,
        temperature: 0,
        response_format: { type: 'json_schema', json_schema: ANSWER_SCHEMA },
      });
      return reply(200, { content: answerText(result), model: env.MODEL, elapsed_ms: Date.now() - started }, trusted);
    } catch (error) {
      const message = String(error?.message || error);
      // The free plan stops at its daily allowance rather than billing; tell the site so it can offer the in-browser model.
      if (/neuron|quota|limit|4006/i.test(message)) {
        return reply(503, { error: 'The hosted Copilot has used today’s free allowance.', quota: true }, trusted);
      }
      return reply(502, { error: 'The hosted model could not answer right now.' }, trusted);
    }
  },
};
