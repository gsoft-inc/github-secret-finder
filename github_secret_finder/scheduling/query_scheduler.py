import operator
from sqlitedict import SqliteDict
from .query_log_item import QueryLogItem
from datetime import datetime


class QueryScheduler(object):
    def __init__(self, user_query, email_query, name_query, result_handler, db_file):
        self.result_handler = result_handler
        self.db_file = db_file
        self.name_query = name_query
        self.email_query = email_query
        self.user_query = user_query

    def execute(self, users, emails, names):
        user_query_type = "user"
        email_query_type = "email"
        name_query_type = "name"

        query_map = {user_query_type: self.user_query, email_query_type: self.email_query, name_query_type: self.name_query}
        operations = {}

        with SqliteDict(self.db_file, tablename="query_log", autocommit=True) as db:
            for k, i in db.iteritems():
                operations[k] = i

            for query_type, items in [(user_query_type, users), (email_query_type, emails), (name_query_type, names)]:
                for i in items:
                    operation_key = query_type + "_" + i
                    if operation_key not in operations:
                        operations[operation_key] = QueryLogItem(operation_key, i, query_type, datetime.min)

            for operation in (sorted(operations.values(), key=operator.attrgetter('last_execution'))):
                operation.last_execution = datetime.utcnow()
                for result in query_map[operation.query_type](operation.value):
                    self.result_handler(result)

                db[operation.key] = operation
