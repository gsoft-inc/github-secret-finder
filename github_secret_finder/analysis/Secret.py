class Secret(object):
    def __init__(self, secret_type, file_name, line_number, value, line, verified):
        self.line = line
        self.secret_type = secret_type
        self.file_name = file_name
        self.line_number = line_number
        self.value = value
        self.verified = verified

    def to_slack_string(self):
        line = self._escape_markdown(self.line)
        secret_value = self._escape_markdown(self.value)
        markdown_format = " _*"
        return self._to_string_internal(line, secret_value, markdown_format, markdown_format[::-1], 100)

    def to_terminal_string(self, max_width):
        return self._to_string_internal(self.line, self.value, '\033[1m', '\033[0m', max_width)

    @staticmethod
    def _to_string_internal(line, secret, format_start, format_end, max_width):
        line = line.replace(secret, format_start + secret + format_end)
        if len(line) > max_width:
            secret_index = line.find(secret)

            half_length = max_width // 2
            if secret_index > half_length:
                line = "..." + line[secret_index - half_length:]
            if len(line) > max_width:
                line = line[:max_width - 3] + "..."

            if secret not in line:
                line += format_end  # The secret was truncated.

        return line

    @staticmethod
    def _escape_markdown(line):
        alternative_characters = {"*": "⁎", "_": "⎯", "~": "∼", ">": "›", "<": "‹", "`": "ˋ"}
        for c, alt_c in alternative_characters.items():
            line = line.replace(c, alt_c)
        return line
