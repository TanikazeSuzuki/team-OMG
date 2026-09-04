from django.contrib.auth.mixins import UserPassesTestMixin


class OrganizerRequiredMixin(UserPassesTestMixin):
    """主催者または管理者だけにビューを許可する。"""

    permission_denied_message = "この操作には主催者権限が必要です。"

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_organizer
