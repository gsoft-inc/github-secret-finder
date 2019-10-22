from typing import Iterable
import requests
from findings import FindingsDatabase
from findings.finding import Finding
from .stoppable_thread import StoppableThread
import itertools


class SlackFindingSender(object):
    min_time_between_messages = 10 * 60

    def __init__(self, slack_webhook, db_file):
        self._db_file = db_file
        self._slack_webhook = slack_webhook

    def __enter__(self):
        if not hasattr(self, '_findings_db') or self._findings_db is None:
            self._findings_db = FindingsDatabase(self._db_file)

        if not hasattr(self, '_thread') or self._thread is None:
            self._thread = StoppableThread(self._send_new_findings, self.min_time_between_messages)
            self._thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread.stop()
        self._findings_db.close()

    def _send_new_findings(self):
        findings = list(self._findings_db.get_findings(lambda f: not f.notification_sent))
        if len(findings) == 0:
            return

        self._send_slack_message("New Github secrets found.", self._findings_to_message(findings))

        for f in findings:
            f.notification_sent = True
            self._findings_db.update(f)

    def _send_slack_message(self, message, attachment=None):
        payload = {"text": message}
        if attachment is not None:
            payload["attachments"] = [{"text": attachment}]
        requests.post(self._slack_webhook, json=payload)

    @staticmethod
    def _findings_to_message(findings: Iterable[Finding]):
        message = ""

        for findings_by_commit in [list(f) for c, f in itertools.groupby(findings, lambda f: f.commit.id)]:
            commit = findings_by_commit[0].commit
            message += "\n%s" % commit.html_url
            commit_secrets = [f.secret for f in findings_by_commit]

            for file, secrets in [(f, list(s)) for f, s in itertools.groupby(commit_secrets, lambda s: s.file_name)]:
                message += "\n*%s*" % file
                for secret in secrets:
                    value = secret.value
                    if len(value) > 100:
                        value = value[:100] + "..."
                    message += "\n> • %s" % value

            message += "\n"
        return message

