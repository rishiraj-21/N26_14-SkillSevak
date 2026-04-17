from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


class LocalhostCsrfMiddleware(CsrfViewMiddleware):
    """
    In development (DEBUG=True), accept any Origin from 127.0.0.1 or localhost
    regardless of port. This handles cases where a browser extension, VS Code
    preview, or proxy rewrites the Origin port to a random value.

    In production (DEBUG=False) this behaves exactly like the standard
    CsrfViewMiddleware — no security is relaxed.
    """

    def _origin_verified(self, request):
        if settings.DEBUG:
            origin = request.META.get('HTTP_ORIGIN', '')
            if '127.0.0.1' in origin or 'localhost' in origin:
                return True
        return super()._origin_verified(request)
