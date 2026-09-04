from .services import NotificationService


def unread_notifications(request):
    """共通ヘッダーへログイン利用者本人の未読件数を渡す。"""
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}

    return {
        "unread_notification_count": NotificationService.unread_count(
            user=request.user
        )
    }
