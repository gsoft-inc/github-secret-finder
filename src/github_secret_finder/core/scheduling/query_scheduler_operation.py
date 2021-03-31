class QuerySchedulerOperation(object):
    def __init__(self, key, value, query_type, last_started, last_completed):
        self.key = key
        self.last_started = last_started
        self.last_completed = last_completed
        self.query_type = query_type
        self.value = value
