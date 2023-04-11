import fcntl, json, os
from tinydb.storages import JSONStorage


class transaction_isolated_storage(JSONStorage):

    def __init__(self, filename):
        self.filename = filename

    def read(self):
        if not os.path.exists(self.filename) or os.stat(self.filename).st_size == 0:
            return None

        with open(self.filename) as handle:
            fcntl.flock(handle, fcntl.LOCK_SH)

            return(json.load(handle) )

    def write(self, data):
        with open(self.filename, 'w+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)

            json.dump(data, handle)

    def close(self):
        pass

