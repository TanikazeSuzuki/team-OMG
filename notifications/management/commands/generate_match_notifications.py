from django.core.management.base import BaseCommand

from notifications.services import EventMatchNotifier
from search.queries import published_events


class Command(BaseCommand):
    help = "公開イベントと保存検索を照合し、条件一致通知を生成します。"

    def handle(self, *args, **options):
        created_count = 0

        for event in published_events().prefetch_related("tags"):
            created_count += len(EventMatchNotifier.notify_for_event(event))

        self.stdout.write(
            self.style.SUCCESS(f"条件一致通知を{created_count}件作成しました。")
        )
