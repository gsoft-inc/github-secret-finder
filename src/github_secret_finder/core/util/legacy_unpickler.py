import io
import pickle


class LegacyUnpickler(pickle.Unpickler):
    missing_core_modules = ["scheduling", "github", "findings", "analysis"]

    def find_class(self, module, name):
        # The namespace of these modules was changed.
        if any(t for t in self.missing_core_modules if module.startswith(t + ".")):
            module = "core." + module

        return super(LegacyUnpickler, self).find_class(module, name)


def legacy_decode(obj):
    return LegacyUnpickler(io.BytesIO(obj)).load()
