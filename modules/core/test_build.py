"""The production static build (what Render's build.sh runs) must succeed.

WhiteNoise's manifest storage rewrites every url() in every stylesheet and
fails the whole deploy if one points at a missing file (it even reads url()
inside CSS comments), so run it here instead of finding out on Render.
"""
import shutil
import tempfile

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class StaticBuildTests(SimpleTestCase):
    def test_collectstatic_with_production_storage(self):
        root = tempfile.mkdtemp(prefix="inkhive-static-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        storages = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        }
        with override_settings(STATIC_ROOT=root, STORAGES=storages):
            call_command("collectstatic", interactive=False, verbosity=0)
