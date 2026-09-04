from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from search.models import SavedSearch

from .forms import AccountDeletionForm, ProfileForm, RegistrationForm, UserPreferenceForm
from .models import User, UserPreference
from .services import AccountService


class SignupView(FormView):
    template_name = "accounts/signup.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:profile")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "アカウントを作成しました。")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "プロフィールを更新しました。")
        return super().form_valid(form)


class PreferenceView(LoginRequiredMixin, UpdateView):
    model = UserPreference
    form_class = UserPreferenceForm
    template_name = "accounts/preferences.html"
    success_url = reverse_lazy("accounts:preferences")

    def get_object(self, queryset=None):
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notification_searches = list(
            SavedSearch.objects.filter(
                owner=self.request.user,
                source=SavedSearch.Source.MANUAL,
                notify_enabled=True,
            ).prefetch_related("tags")
        )
        for saved_search in notification_searches:
            query = []
            if saved_search.keyword:
                query.append(("keyword", saved_search.keyword))
            if saved_search.location:
                query.append(("location", saved_search.location))
            if saved_search.period_from:
                query.append(("period_from", saved_search.period_from.isoformat()))
            if saved_search.period_to:
                query.append(("period_to", saved_search.period_to.isoformat()))
            query.extend(("tag", tag.pk) for tag in saved_search.tags.all())
            query.append(("show_saved", "1"))
            saved_search.search_query = urlencode(query)
        context["notification_searches"] = notification_searches
        return context

    def form_valid(self, form):
        messages.success(self.request, "設定を更新しました。")
        return super().form_valid(form)


class AccountDeleteView(LoginRequiredMixin, FormView):
    template_name = "accounts/delete_confirm.html"
    form_class = AccountDeletionForm
    success_url = reverse_lazy("core:home")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        logout(self.request)
        AccountService.delete_account(user)
        messages.success(self.request, "アカウントを削除しました。")
        return super().form_valid(form)
