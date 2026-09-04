from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import NotificationService

# Create your views here.


@login_required
def notification_list(request):
    notifications = NotificationService.get_notifications(user=request.user)
    unread_count = NotificationService.unread_count(user=request.user)
    context = {"notifications": notifications, "unread_count": unread_count}
    return render(request, "notifications/notification_list.html", context)


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    try:
        NotificationService.mark_as_read(notification=notification, user=request.user)
    except PermissionError:
        pass
    return redirect("notifications:notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    NotificationService.mark_all_as_read(user=request.user)
    return redirect("notifications:notification_list")
