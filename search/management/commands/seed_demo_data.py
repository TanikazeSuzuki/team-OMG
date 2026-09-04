from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, Tag
from notifications.models import Notification
from search.models import SavedSearch

User = get_user_model()

# ブラウザでの手動確認用テストユーザー。パスワードは開発用の分かりやすいものにしている。
DEMO_USERS = [
    {
        "key": "participant",
        "email": "demo-participant@example.com",
        "name": "デモ参加者",
        "role": User.Role.PARTICIPANT,
        "password": "testpass123",
    },
    {
        "key": "organizer",
        "email": "demo-organizer@example.com",
        "name": "デモ主催者",
        "role": User.Role.ORGANIZER,
        "password": "testpass123",
    },
]

DEMO_TAG_NAMES = ["子供向け", "屋外", "屋内", "無料", "夜間開催"]


class Command(BaseCommand):
    #検索画面(/search/)をブラウザで手動確認するためのデモデータを投入する。
    #再実行してもデータが増殖しないよう、get_or_create等で冪等に作成する。
    help = "検索画面(/search/)の手動確認用に、テストユーザー・Tag・Event・SavedSearchを投入する"

    def handle(self, *args, **options):
        users = self._create_users()
        tags = self._create_tags()
        events = self._create_events(users, tags)
        saved_searches = self._create_saved_searches(users, tags)
        self._create_notifications(users, events, saved_searches)

        self.stdout.write(self.style.SUCCESS("デモデータの投入が完了しました。"))
        self.stdout.write("テストユーザー:")
        for demo_user in DEMO_USERS:
            self.stdout.write(
                f"  - email={demo_user['email']} / password={demo_user['password']}"
            )

    def _create_users(self):
        users = {}
        for demo_user in DEMO_USERS:
            user, _created = User.objects.get_or_create(
                email=demo_user["email"],
                defaults={
                    "name": demo_user["name"],
                    "role": demo_user["role"],
                    "is_active": True,
                },
            )
            user.name = demo_user["name"]
            user.role = demo_user["role"]
            user.is_active = True
            user.set_password(demo_user["password"])
            user.save()
            users[demo_user["key"]] = user
        return users

    def _create_tags(self):
        tags = {}
        for name in DEMO_TAG_NAMES:
            tag, _created = Tag.objects.get_or_create(name=name)
            tags[name] = tag
        return tags

    def _create_events(self, users, tags):
        organizer = users["organizer"]
        now = timezone.now()

        # (title, status, start, end, location, min_age, max_age, tag_names)
        event_specs = [
            (
                "【デモ】親子で楽しむ屋外ピクニック",
                Event.Status.PUBLISH,
                now - timedelta(days=10),
                now - timedelta(days=10) + timedelta(hours=3),
                "東京都渋谷区",
                3, 10,
                ["子供向け", "屋外"],
            ),
            (
                "【デモ】無料屋内ワークショップ",
                Event.Status.PUBLISH,
                now + timedelta(days=5),
                now + timedelta(days=5) + timedelta(hours=2),
                "大阪府大阪市",
                None, None,
                ["屋内", "無料"],
            ),
            (
                "【デモ】無料屋外マルシェ",
                Event.Status.PUBLISH,
                now + timedelta(days=14),
                now + timedelta(days=14) + timedelta(hours=4),
                "東京都新宿区",
                None, None,
                ["屋外", "無料"],
            ),
            (
                "【デモ】大人向け屋内セミナー",
                Event.Status.PUBLISH,
                now - timedelta(days=3),
                now - timedelta(days=3) + timedelta(hours=2),
                "福岡県福岡市",
                18, None,
                ["屋内"],
            ),
            (
                "【デモ】未就学児向け室内遊び場",
                Event.Status.PUBLISH,
                now + timedelta(days=7),
                now + timedelta(days=7) + timedelta(hours=3),
                "東京都渋谷区",
                None, 6,
                ["子供向け", "屋内"],
            ),
            (
                "【デモ】夜間屋外イルミネーション",
                Event.Status.PUBLISH,
                now + timedelta(days=20),
                now + timedelta(days=20) + timedelta(hours=3),
                "北海道札幌市",
                None, None,
                ["夜間開催", "屋外"],
            ),
            (
                "【デモ】中止になった子供向けイベント",
                Event.Status.CANCEL,
                now + timedelta(days=8),
                now + timedelta(days=8) + timedelta(hours=2),
                "東京都渋谷区",
                None, None,
                ["子供向け"],
            ),
            (
                "【デモ】下書き中の屋外イベント",
                Event.Status.DRAFT,
                now + timedelta(days=30),
                now + timedelta(days=30) + timedelta(hours=2),
                "神奈川県横浜市",
                None, None,
                ["屋外"],
            ),
        ]

        events = {}
        for title, status, start, end, location, min_age, max_age, tag_names in event_specs:
            event, _created = Event.objects.get_or_create(
                organizer=organizer,
                title=title,
                defaults={
                    "start_datetime": start,
                    "end_datetime": end,
                    "location": location,
                    "min_age": min_age,
                    "max_age": max_age,
                    "status": status,
                },
            )
            event.tags.set([tags[name] for name in tag_names])
            events[title] = event
        return events

    def _create_saved_searches(self, users, tags):
        owner = users["participant"]

        # keyでnotify_for_eventの通知シードから参照できるよう名前を付けている
        saved_search_specs = {
            "tokyo_kids": {
                "keyword": "",
                "location": "東京",
                "period_from": None,
                "period_to": None,
                "notify_enabled": True,
                "tag_names": ["子供向け"],
            },
            "night_event": {
                "keyword": "",
                "location": "",
                "period_from": None,
                "period_to": None,
                "notify_enabled": False,
                "tag_names": ["夜間開催"],
            },
        }

        saved_searches = {}
        for key, spec in saved_search_specs.items():
            saved_search, _created = SavedSearch.objects.get_or_create(
                owner=owner,
                source=SavedSearch.Source.MANUAL,
                keyword=spec["keyword"],
                location=spec["location"],
                defaults={
                    "period_from": spec["period_from"],
                    "period_to": spec["period_to"],
                    "notify_enabled": spec["notify_enabled"],
                },
            )
            saved_search.period_from = spec["period_from"]
            saved_search.period_to = spec["period_to"]
            saved_search.age_min = None
            saved_search.age_max = None
            saved_search.notify_enabled = spec["notify_enabled"]
            saved_search.save()
            saved_search.tags.set([tags[name] for name in spec["tag_names"]])
            saved_searches[key] = saved_search
        return saved_searches

    def _create_notifications(self, users, events, saved_searches):
        #testuser宛に、未読・既読を混在させた通知を投入する(通知一覧画面の手動確認用)。
        #Notificationの(user, event, saved_search)一意制約に沿ってget_or_createするため、
        #再実行しても増殖しない。is_readはdefaultsにしか含めないため、手動で既読化した
        #状態を再実行が巻き戻すこともない。
        testuser = users["participant"]

        notification_specs = [
            {
                "event": events["【デモ】親子で楽しむ屋外ピクニック"],
                "saved_search": saved_searches["tokyo_kids"],
                "message": "「東京・子供向け」の保存検索に一致するイベントが見つかりました。",
                "is_read": False,
            },
            {
                "event": events["【デモ】未就学児向け室内遊び場"],
                "saved_search": saved_searches["tokyo_kids"],
                "message": "「東京・子供向け」の保存検索に一致するイベントが見つかりました。",
                "is_read": True,
            },
            {
                "event": events["【デモ】夜間屋外イルミネーション"],
                "saved_search": saved_searches["night_event"],
                "message": "「夜間開催」の保存検索に一致するイベントが見つかりました。",
                "is_read": False,
            },
        ]

        for spec in notification_specs:
            Notification.objects.get_or_create(
                user=testuser,
                event=spec["event"],
                saved_search=spec["saved_search"],
                defaults={
                    "message": spec["message"],
                    "notification_type": Notification.NotificationType.MATCH,
                    "is_read": spec["is_read"],
                },
            )
