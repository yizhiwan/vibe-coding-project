This will be main root directory. There will be multiple different projects in this repository.

Project list:
  1. [alphabet-adventure](alphabet-adventure) - HTML Web based games for kids to learn alphabet with interactive ways
  2. [telegram-career-coach](telegram-career-coach) - Serverless Telegram bot on Google Cloud Functions that checks portfolio uptime, rewrites resume bullets, and runs a 10-question mock interview with STAR feedback
  3. TBC

## Running the projects

**alphabet-adventure** - open `alphabet-adventure/index.html` in a browser, or run a live-reloading dev server on port 3000:

```bash
cd alphabet-adventure && npm install && npm run dev
```

**telegram-career-coach** - export your bot token and a webhook secret, then deploy (requires the `gcloud` CLI):

```bash
export TELEGRAM_BOT_TOKEN=<token from @BotFather> WEBHOOK_SECRET=<letters, digits, _ or ->
bash telegram-career-coach/deploy.sh
```

After deploying, register the function URL with Telegram:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -d "url=<FUNCTION_URL>" -d "secret_token=$WEBHOOK_SECRET"
```

Never commit the token or secret — they are read from environment variables only.
