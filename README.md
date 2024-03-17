# 稼働ヨミヨミくん

ビルド

```bash
bash tools/src_build.sh
```

デプロイ

```bash
export $(cat src/.env | grep -v ^#)
```

```bash
sam deploy --parameter-overrides SlackBotToken=$SLACK_BOT_TOKEN SlackSigningSecret=$SLACK_SIGNING_SECRET
```