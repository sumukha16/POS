import uuid

from django.contrib.auth import logout
from django.shortcuts import redirect


SERVER_INSTANCE_ID = uuid.uuid4().hex


class POSServerSessionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Only apply this to the POS area.
        if request.path.startswith("/pos/"):

            # Every POS route can read or change operational and financial
            # data.  Keep the access rule here so a newly added POS view is
            # protected by default rather than relying on each view author to
            # remember a decorator.
            if not request.user.is_authenticated:
                return redirect("admin_panel:login")

            stored_server_id = request.session.get(
                "pos_server_instance_id"
            )

            # Existing session from a previous
            # server instance.
            if (
                request.user.is_authenticated
                and stored_server_id != SERVER_INSTANCE_ID
            ):

                logout(request)

                request.session.flush()

                return redirect(
                    "admin_panel:login"
                )

            # Store the current server instance
            # in the user's session.
            if request.user.is_authenticated:

                request.session[
                    "pos_server_instance_id"
                ] = SERVER_INSTANCE_ID

        return self.get_response(request)
