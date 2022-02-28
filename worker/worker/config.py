from datetime import timedelta

from celery.schedules import crontab

from common.settings import settings

broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/0"
imports = ["worker.tasks"]

# careful: maps task names set in @task decorator
task_routes = {
    "scraping.*": {"queue": "scraping"},
    "files.*": {"queue": "files"},
    "process.*": {"queue": "process"},
}

# task_annotations = {'files.download_message_attachments': {'rate_limit': '3/m'}}

# Send task-related events so that tasks can be monitored using tools like flower.
worker_send_task_events = True

# scheduled tasks
beat_schedule = {
    "scrape-chats": {
        "task": "scraping.init_scrapers",
        "schedule": timedelta(minutes=settings.scrape_chats_interval_minutes),
    },
    "scrape-chat-members": {
        "task": "scraping.scrape_chat_members",
        "schedule": crontab(hour=3, minute=0),  # execute daily
    },
}

if settings.save_attachment_types and settings.keep_attachment_files_days > 0:
    beat_schedule["purge-attachment-files"] = {
        "task": "files.purge_message_attachments",
        "schedule": crontab(hour=4, minute=0),  # execute daily
    }
