
class DataProcessor:
    def __init__(self, proc_name, lab):
        self._name = proc_name
        lab._register_PROC(self)

    def __new__(cls, *args, **kwargs):
        if len(args) == 0:
            proc_name = kwargs.get('proc_name', '')
        else:
            proc_name = args[0]
        assert isinstance(proc_name, str) and proc_name != '', "Parameter proc_name was not passed or does not exist as the first argument in the variable class initialisation?"
        if len(args) < 2:
            lab = kwargs.get('lab', None)
            if lab == None:
                lab = kwargs.get('Lab', None)
        else:
            lab = args[1]
        assert lab.__class__.__name__ == 'Laboratory' and lab != None, "Lab parameter was not passed or does not exist as the second argument in the variable class initialisation?"

        prev_exists = lab.PROC(proc_name, True)
        if prev_exists:
            assert isinstance(prev_exists, cls), f"A different processor type ({prev_exists.__class__.__name__}) already exists by this name."
            return prev_exists
        else:
            return super(cls.__class__, cls).__new__(cls)

    @property
    def Name(self):
        return self._name

    def push_data(self, arr):
        raise NotImplementedError()

    def get_all_data(self):
        raise NotImplementedError()

    def ready(self):
        raise NotImplementedError()

    def _get_current_config(self):
        raise NotImplementedError()

    def _set_current_config(self, dict_config, lab):
        raise NotImplementedError()
