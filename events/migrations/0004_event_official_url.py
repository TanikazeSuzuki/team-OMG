import re

from django.db import migrations, models


OFFICIAL_URL_PATTERN = re.compile(r"(?:\r?\n)?公式URL:\s*(https?://\S+)")


def move_official_url_from_description(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    for event in Event.objects.all().iterator():
        match = OFFICIAL_URL_PATTERN.search(event.description or "")
        if not match:
            continue
        event.official_url = match.group(1)
        event.description = OFFICIAL_URL_PATTERN.sub("", event.description).rstrip()
        event.save(update_fields=["official_url", "description"])


def restore_official_url_to_description(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    for event in Event.objects.exclude(official_url="").iterator():
        description = (event.description or "").rstrip()
        event.description = f"{description}\n公式URL: {event.official_url}".lstrip()
        event.save(update_fields=["description"])


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0003_rename_explanation_event_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="official_url",
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(
            move_official_url_from_description,
            restore_official_url_to_description,
        ),
    ]
