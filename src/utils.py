from datetime import date, datetime

import jpholiday
import pandas as pd
import workdays

NOW_DATETIME = datetime.now()


def default_date_range():
    yyyy = NOW_DATETIME.year
    base_period = [
        {
            "start_date": datetime(
                yyyy if month != 1 else yyyy - 1, month - 1 if month != 1 else month, 21
            ).date(),
            "end_date": datetime(yyyy, month, 20).date(),
        }
        for month in range(1, 13)
    ]

    period = [
        period
        for period in base_period
        if period["start_date"] <= NOW_DATETIME.date() <= period["end_date"]
    ]

    return period[0]["start_date"], period[0]["end_date"]


def build_view_blocks():
    start_date, end_date = default_date_range()

    return [
        {
            "type": "input",
            "block_id": "start-date",
            "element": {
                "type": "datepicker",
                "action_id": "start-date",
                "initial_date": str(start_date),
            },
            "label": {"type": "plain_text", "text": "集計開始日"},
        },
        {
            "type": "input",
            "block_id": "end-date",
            "element": {
                "type": "datepicker",
                "action_id": "end-date",
                "initial_date": str(end_date),
            },
            "label": {"type": "plain_text", "text": "集計終了日"},
        },
        {
            "type": "input",
            "block_id": "non-project-work-hours",
            "element": {
                "type": "number_input",
                "action_id": "non-project-work-hours",
                "is_decimal_allowed": True,
                "initial_value": "0",
                "min_value": "0",
            },
            "label": {
                "type": "plain_text",
                "text": "案件外稼働時間（例：1時間15分 ⇒ 1.25）",
            },
        },
        {
            "type": "input",
            "block_id": "scheduled-holidays",
            "element": {
                "type": "number_input",
                "action_id": "scheduled-holidays",
                "is_decimal_allowed": True,
                "initial_value": "0",
                "min_value": "0",
            },
            "label": {
                "type": "plain_text",
                "text": "未取得の予定休暇日数（例：PM 半休 ⇒ 0.5）",
            },
        },
        {
            "type": "input",
            "block_id": "jobcan-csv",
            "element": {
                "type": "file_input",
                "action_id": "jobcan-csv",
                "filetypes": ["csv"],
                "max_files": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "ジョブカン出力 CSV ファイル",
            },
        },
    ]


def has_csv_format_error(csv_data: pd.DataFrame, start_date: date, end_date: date):
    head_date = datetime.strptime(csv_data.at[0, "日付"], "%Y/%m/%d").date()
    tail_date = datetime.strptime(
        csv_data.at[csv_data.shape[0] - 1, "日付"], "%Y/%m/%d"
    ).date()

    errors = {}
    if start_date < head_date or tail_date < end_date:
        errors["jobcan-csv"] = (
            f"CSV ファイルに集計期間が含まれていません。\nジョブカンの出力設定を見直してください。"
        )

    return 0 < len(errors), errors


def calc_work_hours(filtered_data_frame: pd.DataFrame, non_project_work_hours: float):
    total_work_td: pd.Timedelta = filtered_data_frame["労働時間"].sum()
    total = round(
        total_work_td.total_seconds() / 3600 - non_project_work_hours,
        2,
    )

    average = round(total / len(filtered_data_frame), 2)

    return total, average


def calc_estimated_hours(total: float, average: float, remaining_work_days: int):
    hours = round(total + average * remaining_work_days, 2)
    return hours


def calc_remaining_work_days(scheduled_holidays: float, end_date: datetime):
    base_datetime = NOW_DATETIME if NOW_DATETIME < end_date else end_date

    holidays = []
    for holiday in jpholiday.between(base_datetime, end_date):
        holidays.append(datetime(holiday[0].year, holiday[0].month, holiday[0].day))

    remaining_work_days = (
        workdays.networkdays(base_datetime, end_date, holidays) - scheduled_holidays
    )

    return remaining_work_days
