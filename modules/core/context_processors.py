from django.conf import settings


def site(request):
    """App name and contact address, available in every template.

    Named brand_name because Django's login/logout views already set site_name
    (to the host name), which would win over a context processor.
    """
    return {"brand_name": settings.SITE_NAME, "contact_email": settings.CONTACT_EMAIL}
