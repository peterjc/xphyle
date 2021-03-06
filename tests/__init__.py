from contextlib import contextmanager
from io import BytesIO, TextIOWrapper
import random
from unittest.mock import patch
import urllib.request

def random_text(n=1024):
    return ''.join(chr(random.randint(32, 126)) for i in range(n))

class MockStdout(object):
    def __init__(self, name, as_bytes):
        self.bytes_io = BytesIO()
        object.__setattr__(self.bytes_io, 'name', name)
        self.wrapper = TextIOWrapper(self.bytes_io)
        self.wrapper.mode = 'w'
        self.as_bytes = as_bytes
    
    def getvalue(self):
        val = self.bytes_io.getvalue()
        if not self.as_bytes:
            val = val.decode()
        return val

@contextmanager
def intercept_stdout(as_bytes=False):
    i = MockStdout('<stdout>', as_bytes)
    with patch('sys.stdout', i.wrapper):
        yield i

@contextmanager
def intercept_stderr(as_bytes=False):
    i = MockStdout('<stderr>', as_bytes)
    with patch('sys.stderr', i.wrapper):
        yield i

@contextmanager
def intercept_stdin(content, is_bytes=False):
    if not is_bytes:
        content = content.encode()
    i = BytesIO()
    object.__setattr__(i, 'name', '<stdin>')
    i.write(content)
    if not (is_bytes or content.endswith(b'\n')):
        i.write(b'\n')
    i.seek(0)
    i = TextIOWrapper(i)
    i.mode = 'r'
    with patch('sys.stdin', i):
        yield

def no_internet():
    """Test whether there's no internet connection available.
    """
    try:
        urllib.request.urlopen("https://github.com").info()
        return False
    except:
        return True
