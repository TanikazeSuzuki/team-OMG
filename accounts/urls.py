from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import AccountDeleteView, PreferenceView, ProfileView, SignupView

app_name = "accounts"

urlpatterns = [
    path("signup/", login_not_required(SignupView.as_view()), name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("preferences/", PreferenceView.as_view(), name="preferences"),
    path("delete/", AccountDeleteView.as_view(), name="delete"),
]
