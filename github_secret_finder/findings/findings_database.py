import uuid
from typing import Iterable
from sqlitedict import SqliteDict
from findings.finding import Finding


class FindingsDatabase(object):
    def __init__(self, db_file):
        self._findings_db = SqliteDict(db_file, tablename="findings", autocommit=True)

    def close(self):
        self._findings_db.close()

    def get_findings(self, finding_filter) -> Iterable[Finding]:
        for result in self._findings_db.itervalues():
            if finding_filter(result):
                yield result

    def add(self, finding):
        self._findings_db[str(uuid.uuid4())] = finding

