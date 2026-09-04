from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, Tag
from search.spreadsheet_test_data import (
    build_description,
    load_event_specs,
    parse_age_range,
)


ORGANIZER_EMAIL = "sheet-test-organizer@example.invalid"


class Command(BaseCommand):
    help = "共有スプレッドシートの30件のイベントを開発DBへ冪等に投入する"

    def handle(self, *args, **options):
        organizer = self._get_organizer()
        created_count = 0
        updated_count = 0

        for spec in load_event_specs():
            event, created = Event.objects.get_or_create(
                organizer=organizer,
                title=spec.title,
                defaults=self._event_values(spec),
            )
            if not created:
                for field, value in self._event_values(spec).items():
                    setattr(event, field, value)
                event.full_clean()
                event.save()

            tags = [Tag.objects.get_or_create(name=name)[0] for name in spec.tags]
            event.tags.set(tags)

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"スプレッドシートのイベント30件を投入しました"
                f"（新規{created_count}件・更新{updated_count}件）。"
            )
        )

    def _get_organizer(self):
        User = get_user_model()
        defaults = {
            "name": "スプレッドシートテスト主催者",
            "role": User.Role.ORGANIZER,
            "is_active": True,
        }
        organizer, created = User.objects.get_or_create(
            email=ORGANIZER_EMAIL,
            defaults=defaults,
        )
        if created:
            organizer.set_unusable_password()
            organizer.save(update_fields=["password"])
        return organizer

    @staticmethod
    def _event_values(spec):
        min_age, max_age = parse_age_range(spec.target_text)
        start_datetime = timezone.make_aware(
            datetime.combine(spec.start_date, time.min)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(spec.end_date, time(23, 59, 59))
        )
        return {
            "description": build_description(spec),
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "location": spec.location,
            "official_url": spec.url,
            "min_age": min_age,
            "max_age": max_age,
            "status": Event.Status.PUBLISH,
        }
