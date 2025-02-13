"""
Django management command to force-send the daily/weekly digest emails
"""
import sys
import datetime
import pytz
import logging
import logging.config
from django.conf import settings

# This is specifically placed at the top
# to act as a logic configuration override for the rest of the
# code
# Have all logging go to stdout with management commands
# this must be up at the top otherwise the
# configuration does not appear to take affect
if not getattr(settings, 'TEST_MODE', False):
    logging.config.dictConfig({
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO'
        }
    })

from django.core.management.base import BaseCommand, CommandError

from edx_notifications import const
from edx_notifications.digests import send_notifications_digest, send_notifications_namespace_digest

from optparse import make_option, OptionParser


log = logging.getLogger(__file__)


class Command(BaseCommand):
    """
    Django management command to force-send the daily/weekly digest emails
    """

    help = 'Command to force-send the daily/weekly digest emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daily',
            action='store_true',
            dest='send_daily_digest',
            default=False,
            help='Force send daily digest email.'
        ),

        parser.add_argument(
            '--weekly',
            action='store_true',
            dest='send_weekly_digest',
            default=False,
            help='Force send weekly digest email.'
        ),

        parser.add_argument(
            '--ns',
            dest='namespace',
            default='All',
            help='Specify the namespace. Default = All.'
        ),

    def _send_digest(self, subject, preference_name, day_delta, namespace):
        """
        Sends a digest
        """
        if const.NOTIFICATION_DIGEST_SEND_TIMEFILTERED:
            from_timestamp = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=day_delta)
        else:
            from_timestamp = None

        to_timestamp = datetime.datetime.now(pytz.UTC)
        from_email = const.NOTIFICATION_EMAIL_FROM_ADDRESS

        if namespace == "All":
            digests_sent = send_notifications_digest(from_timestamp, to_timestamp, preference_name, subject, from_email)
        else:
            digests_sent = send_notifications_namespace_digest(
                namespace, from_timestamp, to_timestamp, preference_name, subject, from_email
            )
        return digests_sent

    def send_daily_digest(self, namespace='All'):
        """
        Sends the daily digest.
        """

        return self._send_digest(
            const.NOTIFICATION_DAILY_DIGEST_SUBJECT,
            const.NOTIFICATION_DAILY_DIGEST_PREFERENCE_NAME,
            1,
            namespace
        )

    def send_weekly_digest(self, namespace='All'):
        """
        Sends the weekly digest.
        """

        return self._send_digest(
            const.NOTIFICATION_WEEKLY_DIGEST_SUBJECT,
            const.NOTIFICATION_WEEKLY_DIGEST_PREFERENCE_NAME,
            7,
            namespace
        )

    def handle(self, *args, **options):
        """
        Management command entry point, simply call into the send_notifications_digest or the
        send_notifications_namespace_digest depending on the passed the parameters.
        The expected command line arguments are:
         --daily: Sends the daily digest.
         --weekly: Sends the weekly digest.
         --ns=NAMESPACE : Sends the notifications for the particular NAMESPACE.
        """

        if not settings.FEATURES.get('ENABLE_NOTIFICATIONS', False):
            print('ENABLE_NOTIFICATIONS not set to "true". Stopping...')
            return

        usage = "usage: %prog [--daily] [--weekly] [--ns=NAMESPACE]"
        parser = OptionParser(usage=usage)

        log.info("Running management command ...")

        if options['send_daily_digest']:
            log.info("Sending the daily digest with namespace=%s...", options['namespace'])
            daily_digests_sent = self.send_daily_digest(options['namespace'])
            log.info("Successfully sent %s digests...", daily_digests_sent)

        if options['send_weekly_digest']:
            log.info("Sending the weekly digest with namespace=%s...", options['namespace'])
            weekly_digests_sent = self.send_weekly_digest(options['namespace'])
            log.info("Successfully sent %s digests...", weekly_digests_sent)

        if not options['send_weekly_digest'] and not options['send_daily_digest']:
            parser.print_help()
            raise CommandError("Neither Daily, nor Weekly digest specified.")

        log.info("Completed.")
