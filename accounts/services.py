from django.db import transaction

from .models import User, UserPreference


class AccountService:
    @staticmethod
    @transaction.atomic
    def create_account(*, email, password, name, role=User.Role.PARTICIPANT):
        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            role=role,
        )
        UserPreference.objects.get_or_create(user=user)
        return user

    @staticmethod
    @transaction.atomic
    def delete_account(user):
        user.delete()
