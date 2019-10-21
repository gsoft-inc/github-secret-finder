import json
import re


class BlacklistMatcher(object):
    def __init__(self, blacklist_file):
        self._blacklist = self._load_file(blacklist_file)

    @staticmethod
    def _load_file(blacklist_file):
        blacklist = []

        if blacklist_file:
            with open(blacklist_file, "r") as f:
                for i in json.load(f):
                    blacklist.append(BlacklistItem(i))

        return blacklist

    def is_blacklisted(self, code, file, secret):
        for i in self._blacklist:
            if i.matches(code, file, secret):
                return True
        return False


class BlacklistItem(object):
    def __init__(self, json_item):
        self.code_regex = None
        self.file_regex = None
        self.secret_regex = None

        if "code" in json_item:
            self.code_regex = re.compile(json_item["code"])

        if "file" in json_item:
            self.file_regex = re.compile(json_item["file"])

        if "secret" in json_item:
            self.secret_regex = re.compile(json_item["secret"])

    def matches(self, code, file, secret):
        code_matches = (not self.code_regex) or self.code_regex.search(code)
        file_matches = (not self.file_regex) or self.file_regex.search(file)
        secret_matches = (not self.secret_regex) or self.secret_regex.search(secret)
        return code_matches and file_matches and secret_matches


