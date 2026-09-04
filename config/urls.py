"""Root URL configuration for the Team-D project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("events/", include("events.urls")),
    path("interactions/", include("interactions.urls")),
    path("search/", include("search.urls", namespace="search")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    # 空パスを含むcoreは最後に置き、events等の固有URLを先に解決する。
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
