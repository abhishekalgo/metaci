from django.contrib.auth.models import AnonymousUser
from django.core.management.base import BaseCommand

from metaci.build.models import Build
from metaci.build.models import Rebuild


class Command(BaseCommand):
    # NOTE: This should only be run at heroku postdeploy stage
    help = 'Rebuild all builds/rebuilds with status "running"'

    def handle(self, *args, **options):
        for rebuild in Rebuild.objects.filter(status='running'):
            rebuild.status = 'error'
            rebuild.error_message = 'System restarted while build was running'
            rebuild.save()
        for build in Build.objects.filter(status='running'):
            build.status = 'error'
            build.error_message = 'System restarted while build was running'
            build.save()
