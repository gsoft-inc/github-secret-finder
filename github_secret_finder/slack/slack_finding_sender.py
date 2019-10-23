from typing import Iterable
import requests
from findings import FindingsDatabase
from findings.finding import Finding
from .stoppable_thread import StoppableThread
import itertools


class SlackFindingSender(object):
    min_time_between_messages = 20 * 60
    max_ish_message_length = 6000

    def __init__(self, slack_webhook, db_file):
        self._db_file = db_file
        self._slack_webhook = slack_webhook

    def __enter__(self):
        if not hasattr(self, '_findings_db') or self._findings_db is None:
            self._findings_db = FindingsDatabase(self._db_file)

        if not hasattr(self, '_thread') or self._thread is None:
            self._thread = StoppableThread(self._send_new_findings, self._on_stop, self.min_time_between_messages)
            self._thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._thread.stop()

    def _on_stop(self):
        self._findings_db.close()

    def _send_new_findings(self):
        findings = list(self._findings_db.get_findings(lambda f: not f.notification_sent))
        if len(findings) == 0:
            return

        for message in self._findings_to_messages(findings):
            self._send_slack_message("New Github secrets found.", message)

        for f in findings:
            f.notification_sent = True
            self._findings_db.update(f)

    def _send_slack_message(self, message, attachment=None):
        payload = {"text": message}
        if attachment is not None:
            payload["attachments"] = [{"text": attachment}]
        requests.post(self._slack_webhook, json=payload)

    def _findings_to_messages(self, findings: Iterable[Finding]):
        message = ""
        secret_formatter = " _*"

        for findings_by_commit in [list(f) for c, f in itertools.groupby(findings, lambda f: f.commit.id)]:
            commit = findings_by_commit[0].commit
            commit_header = "%s\n" % commit.html_url
            commit_header_added = False

            commit_secrets = [f.secret for f in findings_by_commit]
            for file, secrets in [(f, list(s)) for f, s in itertools.groupby(commit_secrets, lambda s: s.file_name)]:
                file_header = "*%s*\n" % file
                file_header_added = False

                for secret in secrets:
                    line = secret.line.replace(secret.value, secret_formatter + secret.value + secret_formatter[::-1])
                    if len(line) > 100:
                        secret_index = line.find(secret.value)
                        if secret_index > 50:
                            line = "..." + line[secret_index - 50:]
                        if len(line) > 100:
                            line = line[:100] + "..."

                        if secret.value not in line:
                            line += secret_formatter[::-1]  # The secret was truncated.

                    if not commit_header_added:
                        message += commit_header
                        commit_header_added = True

                    if not file_header_added:
                        message += file_header
                        file_header_added = True

                    message += "> • %s: %s\n" % (secret.secret_type, line)
                    if len(message) > self.max_ish_message_length:
                        yield message
                        message = ""
                        commit_header_added = False
                        file_header_added = False

        yield message

