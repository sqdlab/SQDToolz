class Miscellaneous:
    @staticmethod
    def get_units(val, sigFigs = -1):
        if isinstance(val, float) or isinstance(val, int):
            if val <= 0.0:
                return val

            thinspace = u"\u2009"
            def clip_val(value):
                return f'{value:.6g}'

            if val < 1e-6:
                return f'{clip_val(val*1e9)}{thinspace}n'
            if val < 1e-3:
                return f'{clip_val(val*1e6)}{thinspace}μ'
            if val < 1:
                return f'{clip_val(val*1e3)}{thinspace}m'
            if val < 1000:
                return val
            if val < 1e6:
                return f'{clip_val(val*1e-3)}{thinspace}k'
            if val < 1e9:
                return f'{clip_val(val*1e-6)}{thinspace}M'

            return f'{clip_val(val*1e-9)}{thinspace}G'
        else:
            return val
