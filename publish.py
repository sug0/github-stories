import io
import os
import errno
import fcntl

from datetime import date
from itertools import chain
from time import sleep

class LockedFile(object):
    def __init__(self, *args, **kwargs):
        self.file = open(*args, **kwargs)
        self._spinacquire()
        self.locked = True

    def __enter__(self):
        return self.file

    def __exit__(self, type, value, traceback):
        self._close()

    def _close(self):
        if self.locked:
            fd = self.file.fileno()
            fcntl.flock(fd, fcntl.LOCK_UN)
            self.locked = False
            self.file.close()

    def _spinacquire(self):
        fd = self.file.fileno()
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except IOError as e:
                if e.errno != errno.EAGAIN:
                    raise
                else:
                    time.sleep(0.1)

class Publisher(object):
    def __init__(self):
        self._date = None

    def _getdate(self):
        if not self._date:
            self._date = {}
            d = date.today()
            self._date['y'] = d.year
            self._date['m'] = d.month
            self._date['d'] = d.day
        return self._date

    def _nextpath(self):
        lockpath = self._pathtofile('publish.lock')
        now = -1
        try:
            with LockedFile(lockpath, 'r+') as f:
                now = 1 + int(f.readline())
                f.seek(0)
                f.write(f'{now}\n')
        except IOError:
            with LockedFile(lockpath, 'w') as f:
                f.write('1\n')
                now = 1
        return now

    def _pathtofile(self, f):
        def it(x):
            return [str(x)]
        def mkdir(path):
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise
        d = self._getdate()
        dirpath = os.sep.join(chain(it(d['y']), it(d['m']), it(d['d'])))
        mkdir(dirpath)
        return os.sep.join(chain(it(dirpath), it(f)))

def main():
    p = Publisher()
    print(p._nextpath())

if __name__ == '__main__':
    main()
