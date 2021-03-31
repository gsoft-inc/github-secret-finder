import operator
from datetime import datetime
from typing import Iterable

from sqlitedict import SqliteDict

from .query_scheduler_operation import QuerySchedulerOperation
from ..util.legacy_unpickler import legacy_decode


class QueryScheduler(object):
    USER_QUERY_TYPE = "user"
    EMAIL_QUERY_TYPE = "email"
    NAME_QUERY_TYPE = "name"
    ORGANIZATION_QUERY_TYPE = "organization"

    def __init__(self, user_query, email_query, name_query, organization_query, result_handler, db_file, cache_only):
        self.cache_only = cache_only
        self.result_handler = result_handler
        self.db_file = db_file
        self.name_query = name_query
        self.email_query = email_query
        self.user_query = user_query
        self.organization_query = organization_query

        self._operation_map = {
            QueryScheduler.USER_QUERY_TYPE: self.user_query,
            QueryScheduler.EMAIL_QUERY_TYPE: self.email_query,
            QueryScheduler.NAME_QUERY_TYPE: self.name_query,
            QueryScheduler.ORGANIZATION_QUERY_TYPE: self.organization_query
        }

    def execute(self, users, emails, names, organizations):
        with SqliteDict(self.db_file, tablename="query_log", autocommit=True, decode=legacy_decode) as db:
            operations = self._get_operations(db, users, emails, names, organizations)

            if self.cache_only:
                for operation in operations:
                    if operation.last_started == datetime.min:
                        continue
                    for result in self._operation_map[operation.query_type](operation.value):
                        self.result_handler(result)
            else:
                for operation in sorted(self._get_operations(db, users, emails, names, organizations), key=operator.attrgetter('last_completed')):

                    operation.last_started = datetime.utcnow()
                    db[operation.key] = operation

                    for result in self._operation_map[operation.query_type](operation.value):
                        self.result_handler(result)

                    operation.last_completed = datetime.utcnow()
                    db[operation.key] = operation

    @staticmethod
    def _get_operations(db, users, emails, names, organizations) -> Iterable[QuerySchedulerOperation]:
        operations = {}
        for query_type, items in [(QueryScheduler.USER_QUERY_TYPE, users),
                                  (QueryScheduler.EMAIL_QUERY_TYPE, emails),
                                  (QueryScheduler.NAME_QUERY_TYPE, names),
                                  (QueryScheduler.ORGANIZATION_QUERY_TYPE, organizations)]:
            for i in items:
                operation_key = query_type + "_" + i
                if operation_key not in db:
                    operations[operation_key] = QuerySchedulerOperation(operation_key, i, query_type, datetime.min, datetime.min)
                else:
                    operations[operation_key] = db[operation_key]

        return operations.values()
