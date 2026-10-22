# Telegram Career Coach

A Telegram bot that helps software engineers prepare for senior / FAANG interview loops. It runs as a single Google Cloud Function with no database and no AI API keys — all feedback is rule-based and instant.

**What it does**

- **Portfolio uptime check** — confirms your portfolio site is up, fast, and served over HTTPS.
- **Resume bullet optimiser** — rewrites a raw achievement into a strong, metric-driven resume bullet and scores it.
- **Mock interview** — 10 behavioural and architecture questions, each graded on STAR structure, metrics, technical depth, ownership and delivery.

## Commands

| Command | What it does |
| --- | --- |
| `/start` | Welcome message and command list |
| `/help` | Command list |
| `/check_portfolio <url>` | Checks the site's status, response time, HTTPS and redirects |
| `/optimize_bullet <text>` | Rewrites the achievement as a resume bullet. Send `/optimize_bullet` alone and the bot waits for your next message |
| `/mock_interview` | Starts a 10-question mock interview |
| `/skip` | Skips the current interview question |
| `/end_interview` | Stops the interview and shows your summary (`/end` and `/stop` also work) |

### `/check_portfolio`

```
/check_portfolio https://example.com
```

```
🌐 Portfolio uptime check

✅ UP
Final URL: https://example.com
HTTP status: 200 OK
Total response time: 56 ms
HTTPS: yes
```

The bot also warns about slow responses (over 2.5 s), sites without HTTPS, pages that return 401/403 (recruiters can't see them), broken links, TLS certificate failures and redirect loops. If you leave out the URL, it uses `PORTFOLIO_URL` when that is set.

### `/optimize_bullet`

```
/optimize_bullet I was responsible for building a Kafka pipeline for payment events which resulted in a 35% drop in reconciliation errors for 2M users
```

```
Rewritten:
• Built a Kafka pipeline for payment events, resulting in a 35% drop in reconciliation errors for 2M users

Impact-first variant:
• Delivered a 35% drop in reconciliation errors for 2M users by building a Kafka pipeline for payment events

Impact score: 80/100 → 100/100
✅ Opens with a strong past-tense action verb
✅ Contains a hard metric
...
```

How the rewrite works:

1. Strips bullet symbols, "I"/"We", and filler words ("successfully", "very", "in order to").
2. Replaces weak openers ("responsible for", "worked on", "helped") with a strong past-tense verb.
3. Normalises the outcome clause ("which resulted in" → "resulting in", "and reduced" → "reducing").
4. Adds an impact-first variant when the outcome contains a number.
5. Scores the before and after versions against a checklist: strong verb, hard metric, named technology, outcome, scope, length (12–35 words), no vague words like "significantly".

If the bullet has no number, the bot asks targeted questions to help you find one (e.g. "Latency before → after?" for performance work).

### `/mock_interview`

The bot asks 10 questions, one at a time. Reply to each with a single message, written the way you'd say it — about 250–400 words. Answers under 15 words are sent back for a fuller answer rather than graded.

| # | Category |
| --- | --- |
| 1 | Situational — Incident Response |
| 2 | Architecture — Distributed System Design |
| 3 | Architecture — Scaling |
| 4 | Architecture — Zero-Downtime Migration |
| 5 | Cross-functional — Conflict Resolution |
| 6 | Leadership — Influence Without Authority |
| 7 | Situational — Ambiguity and Deadlines |
| 8 | Leadership — Raising the Engineering Bar |
| 9 | Situational — Owning a Wrong Decision |
| 10 | Architecture — Cost and Performance Optimisation |

Each answer is scored 1–5 on five dimensions:

| Dimension | Weight | What it checks |
| --- | --- | --- |
| STAR structure | 30% | Signals of Situation, Task, Action and Result |
| Metric validation | 25% | Percentages, durations, money, scale, before → after; penalises vague claims |
| Technical depth | 25% | Domain terms for that question plus general engineering vocabulary |
| Ownership | 10% | Ratio of "I" to "we" |
| Delivery | 10% | Length (200–450 words scores highest) |

You get a weighted overall score and a verdict (Strong Hire, Hire, Lean Hire, Lean No Hire, No Hire), coaching for weak areas, and a checklist of what a hire-level answer includes. After the last question (or `/end_interview`) you get a summary with per-question scores, dimension averages and up to two areas to practise.

The grading is keyword- and pattern-based, so treat it as a structure check rather than a judgement of your story's quality.

## Deploying

### Prerequisites

- A Telegram bot token from [@BotFather](https://t.me/BotFather) (`/newbot`).
- A Google Cloud project with billing enabled, and the [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and logged in.

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>
gcloud services enable cloudfunctions.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### 1. Set the token and a webhook secret

The secret may only contain letters, digits, `_` and `-`. A random hex string works:

```bash
export TELEGRAM_BOT_TOKEN=<token from BotFather>
export WEBHOOK_SECRET=$(openssl rand -hex 32)
```

Optional: `export REGION=europe-west1` to deploy somewhere other than `us-central1`.

### 2. Deploy the function

```bash
bash telegram-career-coach/deploy.sh
```

### 3. Point Telegram at the function

Get the function's URL:

```bash
gcloud functions describe telegram-career-coach --gen2 --region=${REGION:-us-central1} --format="value(serviceConfig.uri)"
```

Register it as the webhook, passing the same secret:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -d "url=<FUNCTION_URL>" -d "secret_token=$WEBHOOK_SECRET"
```

Check it took effect (look for `"url"` and no `last_error_message`):

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

### 4. (Optional) Show commands in Telegram's menu

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setMyCommands" -H "Content-Type: application/json" -d '{"commands":[{"command":"start","description":"Welcome and command list"},{"command":"check_portfolio","description":"Check your portfolio site is up"},{"command":"optimize_bullet","description":"Rewrite a resume bullet"},{"command":"mock_interview","description":"Start a 10-question mock interview"},{"command":"skip","description":"Skip the current question"},{"command":"end_interview","description":"End the interview and see your summary"},{"command":"help","description":"Command list"}]}'
```

Open your bot in Telegram and send `/start`.

### Updating

Edit the code and run `deploy.sh` again. The webhook URL stays the same.

## Running locally

```bash
cd telegram-career-coach
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=<token> WEBHOOK_SECRET=local-test
functions-framework --target=telegram_webhook --port=8080
```

Send a fake update from another terminal. Replace `<YOUR_CHAT_ID>` with your Telegram chat ID; the reply is delivered to that chat through the real bot:

```bash
curl -X POST localhost:8080 -H "Content-Type: application/json" -H "X-Telegram-Bot-Api-Secret-Token: local-test" -d '{"update_id":1,"message":{"message_id":1,"chat":{"id":<YOUR_CHAT_ID>},"text":"/help"}}'
```

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `WEBHOOK_SECRET` | Yes | Must match the `secret_token` given to `setWebhook`; requests without it are rejected with 403 |
| `PORTFOLIO_URL` | No | Default URL for `/check_portfolio` with no argument |

## Limitations

- **Sessions live in memory.** The function is deployed with `--max-instances=1` so every message reaches the same instance. When Cloud Functions shuts down an idle instance, any interview in progress is lost and the bot asks you to start again. Inactive sessions are also cleared after 2 hours.
- **Grading is rule-based**, not AI. It detects structure, numbers and vocabulary; it can't tell whether a story is true or compelling.
- **Text only.** Voice messages, photos and files are not processed.

## Security

- Never commit `TELEGRAM_BOT_TOKEN` or `WEBHOOK_SECRET`. Both are read from environment variables only.
- Every request must carry the webhook secret header; the check is constant-time.
- `/check_portfolio` refuses private, loopback and link-local addresses, and checks every redirect, so the bot can't be used to reach internal networks.
- The bot token is redacted from error logs.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | Webhook entry point (`telegram_webhook`), command handlers, bullet optimiser, interview questions and grading |
| `requirements.txt` | Pinned Python dependencies |
| `deploy.sh` | One-line `gcloud functions deploy` command |
