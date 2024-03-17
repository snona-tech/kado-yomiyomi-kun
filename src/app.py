from datetime import datetime
import io
import logging
import os

import pandas as pd
import requests
from dotenv import load_dotenv
from slack_bolt import Ack, App, Say
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
import utils

load_dotenv()

CHANNEL_ID = ""
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_APP_LEVEL_TOKEN = os.environ.get("SLACK_APP_LEVEL_TOKEN")

SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(level=logging.DEBUG)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    process_before_response=True,
)

receiver = SlackRequestHandler(app)


@app.command("/kado")
def handle_some_command(ack: Ack, body: dict, payload: dict, client: WebClient):
    ack()

    global CHANNEL_ID
    CHANNEL_ID = payload["channel_id"]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "kado-modal",
            "title": {"type": "plain_text", "text": "集計情報の入力"},
            "submit": {"type": "plain_text", "text": "集計"},
            "close": {"type": "plain_text", "text": "閉じる"},
            "blocks": utils.build_view_blocks(),
        },
    )


@app.view("kado-modal")
def handle_view_events(ack: Ack, body: dict, view: dict, say: Say):
    inputs = view["state"]["values"]
    start_date = datetime.strptime(
        inputs["start-date"]["start-date"]["selected_date"], "%Y-%m-%d"
    ).date()
    end_date = datetime.strptime(
        inputs["end-date"]["end-date"]["selected_date"], "%Y-%m-%d"
    ).date()

    csv_data = requests.get(
        url=inputs["jobcan-csv"]["jobcan-csv"]["files"][0]["url_private_download"],
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
    ).content

    pd_data = pd.read_csv(io.BytesIO(csv_data))
    result, errors = utils.has_csv_format_error(pd_data, start_date, end_date)

    if result:
        ack(response_action="errors", errors=errors)
        return

    filtered_df = pd_data[pd.notna(pd_data["出勤時刻"])].copy()
    filtered_df["労働時間"] = pd.to_timedelta(filtered_df["労働時間"] + ":00")

    non_project_work_hours = float(
        inputs["non-project-work-hours"]["non-project-work-hours"]["value"]
    )
    scheduled_holidays = float(
        inputs["scheduled-holidays"]["scheduled-holidays"]["value"]
    )

    total_work_hours, average_work_hours = utils.calc_work_hours(
        filtered_df, non_project_work_hours
    )
    remaining_work_days = utils.calc_remaining_work_days(
        scheduled_holidays,
        datetime.combine(end_date, datetime.min.time()),
    )
    real_work_days = len(filtered_df)
    estimated_hours = utils.calc_estimated_hours(
        total_work_hours, average_work_hours, remaining_work_days
    )

    user = body["user"]["id"]
    say(
        channel=CHANNEL_ID,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user}> さんの集計結果です！",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*集計期間*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{str(start_date)} ～ {str(end_date)}",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*今月の案件稼働時間（{str(utils.NOW_DATETIME.date())} 時点）*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{total_work_hours} 時間",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*今月の推定稼働時間*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{estimated_hours} 時間",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*平均稼働時間*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{average_work_hours} 時間/日",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*実稼働日数（残稼働予定日数）*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{real_work_days}（{remaining_work_days}）日",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*案件外時間*",
                    },
                    {
                        "type": "plain_text",
                        "text": f"{non_project_work_hours} 時間",
                    },
                ],
            },
        ],
    )

    ack()


def lambda_handler(event, context):
    return receiver.handle(event, context)


app.view("kado-modal")(ack=lambda ack: ack(), lazy=[handle_view_events])

if __name__ == "__main__":
    if SLACK_APP_LEVEL_TOKEN:
        SocketModeHandler(app, SLACK_APP_LEVEL_TOKEN).start()
