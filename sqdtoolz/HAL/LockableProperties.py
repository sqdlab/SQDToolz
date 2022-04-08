class LockableProperties:
    def __init__(self):
        self._locked_props = []

    def __setattr__(self, prop, value):
        if not hasattr(self, '_locked_props'):
            super().__setattr__(prop, value)
        elif not prop in self._locked_props:
            super().__setattr__(prop, value)
    
    def _property_lock(self, prop):
        if not hasattr(self, '_locked_props'):
            self._locked_props = []
        self._locked_props += [prop]
    def _property_unlock(self, prop):
        try:
            while True:
                self._locked_props.remove(prop)
        except ValueError:
            pass
    def _property_lock_clearall(self):
        self._locked_props.clear()