class Secret(object):
    def __init__(self, secret_type, file_name, line_number, value, verified):
        self.secret_type = secret_type
        self.file_name = file_name
        self.line_number = line_number
        self.value = value
        self.verified = verified

    def __str__(self):
        return "(%s) %s:%s - %s" % (self.secret_type, self.file_name, self.line_number, self.value)