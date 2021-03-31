from typing import Iterable

from sqlitedict import SqliteDict

from .finding import Finding


class FindingsDatabase(object):
    def __init__(self, db_file):
        self._findings_db = SqliteDict(db_file, tablename="findings", autocommit=True)

    def close(self):
        self._findings_db.close()

    def get_findings(self, finding_filter) -> Iterable[Finding]:
        for result in self._findings_db.itervalues():
            if finding_filter(result):
                yield result

    def create(self, commit, secret):
        finding = Finding(commit, secret)
        self._findings_db[finding.id] = finding
        return finding

    def update(self, finding):
        self._findings_db[finding.id] = finding


