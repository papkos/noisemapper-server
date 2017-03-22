from typing import Callable

from django.contrib.auth.models import User


class Permission(object):
    """
    :type name: str
    :type test: Callable[[User], bool]
    """
    def __init__(self, name: str, test: Callable[[User], bool]):
        self.name = name
        self.test = test

    def __call__(self, user: User) -> bool:
        return self.test(user)


def _is_staff_user(user: User) -> bool:
    return user.is_authenticated and user.is_staff

can_download = Permission('can_download', _is_staff_user)


