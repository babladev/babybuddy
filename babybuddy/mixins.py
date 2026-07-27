# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import (
    AccessMixin,
    LoginRequiredMixin as LoginRequiredMixInBase,
    PermissionRequiredMixin as PermissionRequiredMixinBase,
)
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name="dispatch")
class LoginRequiredMixin(LoginRequiredMixInBase):
    pass


@method_decorator(never_cache, name="dispatch")
class PermissionRequiredMixin(PermissionRequiredMixinBase):
    login_url = "/login"


class CancelUrlMixin:
    """
    Provides a "cancel_url" for form templates, so a form can be abandoned
    without resorting to the browser's back button.

    Defaults to wherever a successful submission would have gone, which for
    these views is the list the entry belongs to. Set "cancel_url" on the view
    to send it somewhere else.
    """

    cancel_url = None

    def get_cancel_url(self):
        if self.cancel_url:
            return str(self.cancel_url)

        # success_url is read directly rather than through get_success_url,
        # which on a create view formats the URL against the object that does
        # not exist yet.
        success_url = getattr(self, "success_url", None)
        if success_url:
            return str(success_url)

        try:
            return self.get_success_url()
        except (AttributeError, ImproperlyConfigured):
            # A view with no fixed destination has nowhere obvious to return
            # to, so the template omits the button.
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_cancel_url()
        return context


@method_decorator(never_cache, name="dispatch")
class StaffOnlyMixin(AccessMixin):
    """
    Verify the current user is staff.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
