class QueryLogItem(object):
    def __init__(self, key, value, query_type, last_execution):
        self.key = key
        self.last_execution = last_execution
        self.query_type = query_type
        self.value = value
