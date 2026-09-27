# Archive Copilot Worker

This Cloudflare Worker answers Copilot questions for the [hosted archive site](https://nl2992.github.io/columbia-mafn-coursework/), so visitors don't download a model.

1. The browser retrieves passages with Pagefind.
2. It sends the question and up to 8 passages to `POST /answer`.
3. The Worker asks Workers AI (`@cf/qwen/qwen3-30b-a3b-fp8`) for a JSON answer with verbatim quotations.
4. The browser keeps only claims whose quotation appears in the cited passage.

## Safeguards

- **Origins:** only the origins in `ALLOWED_ORIGINS` are served. Others get `403`.
- **Fixed prompt and size limits:** the system prompt is fixed, questions are capped at 600 characters and passages at 2,000 characters, so the endpoint can't be used as a general-purpose chatbot.
- **Rate limit:** each IP address can ask 6 questions a minute.
- **No storage:** questions and passages are never stored or logged, and Workers observability is off.
- **No bill on the free plan:** the free plan includes 10,000 neurons a day, about 300 questions. After that, Workers AI refuses requests until the next day. The site then suggests switching to an in-browser model.

## Deploy

```bash
cd copilot-worker
npx wrangler login
npx wrangler deploy
```

After deploying, put the Worker URL in [`site/config.json`](../site/config.json) as `copilot_endpoint` and push. If that value is empty, the site offers only the in-browser models.
