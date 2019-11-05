import os
import errno
import fcntl
import magic

from argparse import ArgumentParser
from itertools import chain
from datetime import date
from time import sleep

class PublishError(Exception):
    pass

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

    def publish(self, content_path):
        mime = magic.from_file(content_path, mime=1).split('/')
        path = None

        if mime[0] == 'text':
            id = self._next_id()
            path = self._pathtofile(f'{id}.txt')
        elif mime[0] == 'image':
            id = self._next_id()
            path = self._pathtofile(f'{id}.{mime[1]}')
        else:
            raise PublishError('content type needs to be "text" or "image"')

        if os.system(f'cp {content_path} {path}') != 0:
            raise PublishError('copy failed')

    def _getdate(self):
        if not self._date:
            self._date = {}
            d = date.today()
            self._date['y'] = d.year
            self._date['m'] = d.month
            self._date['d'] = d.day
        return self._date

    def _next_id(self):
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
    # define CLI arguments
    parser = ArgumentParser(description='Publish new Github History.')
    parser.add_argument('content', metavar='content', type=str, nargs=1,
            help='The path to the content to publish.')

    # parse the arguments (content)
    args = parser.parse_args()
    content = args.content[0]

    # publish content
    p = Publisher()
    p.publish(content)

if __name__ == '__main__':
    main()
