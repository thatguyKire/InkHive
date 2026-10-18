"""Create the demo accounts, or wipe and re-create them.

    python manage.py seed_demo           # create them if they are missing
    python manage.py seed_demo --reset   # delete everything they made and start over
"""
from django.core.management.base import BaseCommand

from modules.demo.accounts import ensure_demo_data, reset_demo_data


class Command(BaseCommand):
    help = "Create the shared demo accounts and sample class (--reset to start over)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all demo data first.")

    def handle(self, *args, reset=False, **options):
        if reset:
            reset_demo_data()
            self.stdout.write("Demo data reset.")
        else:
            ensure_demo_data()
            self.stdout.write("Demo accounts are ready.")
