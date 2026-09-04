from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_next_url(request, default=""):
    """POST優先・次いでGETから 'next' を取得し、検証して返す。無効なら default。"""
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return default
