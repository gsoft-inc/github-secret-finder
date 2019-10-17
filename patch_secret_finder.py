from detect_secrets.core.usage import PluginOptions
from detect_secrets.plugins.common import initialize
from unidiff import PatchSet, UnidiffParseError


class PatchSecretFinder(object):
    def __init__(self):
        active_plugins = {}
        for plugin in PluginOptions.all_plugins:
            related_args = {}
            for related_arg_tuple in plugin.related_args:
                flag_name, default_value = related_arg_tuple
                related_args[flag_name[2:].replace("-", "_")] = default_value

            active_plugins[plugin.classname] = related_args

        self._plugins = initialize.from_parser_builder(
            active_plugins,
            exclude_lines_regex=None,
            automaton=False,
            should_verify_secrets=True)

    def find_secrets(self, patch_text):
        try:
            patch = PatchSet.from_string(patch_text)
        except UnidiffParseError:
            raise StopIteration

        for p in self._plugins:
            for patch_file in patch:
                for chunk in patch_file:
                    for line in chunk.target_lines():
                        if line.is_added:
                            l = line.value.strip()
                            for k in p.analyze_string(l, line.target_line_no, patch_file.path):
                                yield l, k.json()
