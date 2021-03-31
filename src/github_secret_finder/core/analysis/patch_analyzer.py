from detect_secrets.core.plugins.util import get_mapping_from_secret_type_to_class
from detect_secrets import SecretsCollection
from detect_secrets.settings import transient_settings
from unidiff import PatchSet

from .blacklist_matcher import BlacklistMatcher
from .Secret import Secret


class PatchAnalyzer(object):
    def __init__(self, blacklist_file):
        self._blacklist = BlacklistMatcher(blacklist_file)

    def find_secrets(self, diff):
        changes = None

        secrets_collection = SecretsCollection()
        with transient_settings({'plugins_used': [{'name': plugin_type.__name__} for plugin_type in get_mapping_from_secret_type_to_class().values()]}) as settings:
            settings.disable_filters(
                'detect_secrets.filters.common.is_invalid_file',
            )
            secrets_collection.scan_diff(diff)

        for file_name, secret in secrets_collection:
            if len(secret.secret_value) < 6:
                continue  # Ignore small secrets to reduce false positives.

            # Only parse the diff if at least one secret was found.
            if not changes:
                patch_set = PatchSet.from_string(diff)
                changes = {}
                for patch_file in patch_set:
                    lines = dict((line.target_line_no, line.value.strip()) for chunk in patch_file for line in chunk.target_lines() if line.is_added)
                    changes[patch_file.path] = lines

            line = changes[secret.filename][secret.line_number]
            if self._blacklist.is_blacklisted(line, file_name, secret.secret_value):
                continue

            # detect_secrets sometimes return a lowercase version of the secret. Find the real string.
            secret_index = line.lower().find(secret.secret_value.lower())
            secret_value = line[secret_index:secret_index + len(secret.secret_value)]

            yield Secret(secret.type, secret.filename, secret.line_number, secret_value, line, secret.is_verified)
