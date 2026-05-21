import numpy as np

class Miscellaneous:
    @staticmethod
    def get_units(val, sigFigs = 6):
        if isinstance(val, float) or isinstance(val, int):
            if val <= 0.0:
                return val

            thinspace = u"\u2009"
            def clip_val(value):
                return f'{value:.{sigFigs}g}'

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

    @staticmethod
    def get_metric_multiplier(vals):
        if isinstance(vals, np.ndarray):
            pass
        elif isinstance(vals, (list,tuple)):
            vals = np.array(isinstance(vals, np.ndarray))
        else:
            vals = np.array([vals])
        
        vals = np.abs(vals)
        vals = vals[vals>0]
        if vals.size == 0:
            return 1, ''    #It's just zero - can't get units here...
        norm_fac = np.round(np.log10(vals).mean()) / 3
        if norm_fac > 0:
            norm_fac = int(norm_fac)*3
        else:
            norm_fac = int(np.floor(norm_fac)*3)
        
        if norm_fac == -9:
            norm_prefix = 'n'
        elif norm_fac == -6:
            norm_prefix = 'μ'
        elif norm_fac == -3:
            norm_prefix = 'm'
        elif norm_fac == 3:
            norm_prefix = 'k'
        elif norm_fac == 6:
            norm_prefix = 'M'
        elif norm_fac == 9:
            norm_prefix = 'G'
        elif norm_fac == 12:
            norm_prefix = 'T'
        else:
            norm_prefix = ''
        

        return 10**norm_fac, norm_prefix
