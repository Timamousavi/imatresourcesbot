# IMAT Study Resources Bot — GitHub + Vercel

Webhook-based Telegram bot for IMAT books, notes and past papers, powered by a Google Sheet catalog and Google Drive links.

## Security first

If a Telegram token was ever posted publicly, revoke it in `@BotFather` and create a new one. Never place the real token in GitHub or any project file.

## Google Sheet

Import `resources_template.csv` into Google Sheets. Upload each resource to Google Drive, set it to **Anyone with the link — Viewer**, and paste its link into `drive_url`. Set `active` to `yes`.

Publish the Sheet or make it publicly readable, then use:

```text
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
```

## GitHub

Create a repository and upload all files from this folder. Do not upload a `.env` file.

## Vercel

1. In Vercel, choose **Add New → Project** and import the GitHub repository.
2. Keep the framework preset as **Other**.
3. Add these Environment Variables for Production, Preview and Development:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_SHEET_CSV_URL`
   - `TELEGRAM_WEBHOOK_SECRET`
4. Deploy and copy the production URL, such as `https://your-project.vercel.app`.

## Register the Telegram webhook

Open this URL once in a browser, replacing all placeholders:

```text
https://api.telegram.org/botYOUR_NEW_TOKEN/setWebhook?url=https://YOUR_PROJECT.vercel.app/api/webhook&secret_token=YOUR_WEBHOOK_SECRET
```

Telegram should return `{"ok":true,"result":true}`. Never share or screenshot this registration URL because it contains the token.

Verify without exposing the token publicly by opening this privately:

```text
https://api.telegram.org/botYOUR_NEW_TOKEN/getWebhookInfo
```

Then open `@IMATStudyResourcesBot` and send `/start`.

## Environment variables

Generate a webhook secret locally with Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

After changing Vercel environment variables, redeploy the project.
