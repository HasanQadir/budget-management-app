"""budget_manager URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

def _get_api_urls() -> list:
    """Get API URL patterns."""
    return [
        # Add API URL patterns here
    ]


def _get_urlpatterns() -> list:
    """Get the URL patterns for the project."""
    return [
        path('admin/', admin.site.urls),
        path('api/', include((_get_api_urls(), 'api'), namespace='api')),
    ]


urlpatterns: list = _get_urlpatterns()

# Add static and media URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
