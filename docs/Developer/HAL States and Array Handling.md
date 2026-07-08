# HAL States and Array Handling

Idea:
- The HAL has `_get_current_config()` and `_set_current_config(...)` to handle the querying/setting of the states.
- Most parameters serialise fine into JSON.
- However, numpy arrays and other object types can be tricky. Idea is to use their in-built pickled serialisation...

The handling of will be automatic. This is fine as:
- Message passing through internal *SQDToolz* objects will still work fine with actual numpy arrays
- The JSON serialisation/deserialisation will be the only place where it'll fail; hence, the encoding/decoding is done there

The proposed format is:
```json
"weights": {
    "__type__": "numpy.ndarray",
    "encoding": "npy+zlib+base64",
    "data": "eJzt3V..."
}
```
That is, it is a clean as no attribute of any *SQDToolz* object should have double underscore anyway. Basically, it if it has a `__type__`, it is some serialised/compressed type. The information is there to help guide the decoder; nonetheless, currently the "encoding" entry is fixed in value and reserved for future changes etc.

It displays fine in VSCode (i.e. one line for the 'data' attribute), but Notepad on Win10 seems to still wrap the text even with *Word Wrap* turned off... Note that the encoding should only use `A-Z`, `a-z`, `0-9`, `+`, `/` and `=` (i.e. simple ASCII).
