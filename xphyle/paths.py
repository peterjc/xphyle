# -*- coding: utf-8 -*-
"""Convenience functions for working with file paths.
"""
import errno
import os
import re
import shutil
import stat
import sys
import tempfile

ACCESS = dict(
    r=(os.R_OK, stat.S_IREAD),
    w=(os.W_OK, stat.S_IWRITE),
    a=(os.W_OK, stat.S_IWRITE),
    x=(os.X_OK, stat.S_IEXEC))
"""Dictionary mapping mode characters to access method constants"""
STDIN = STDOUT = '-'
"""Placeholder for ``sys.stdin`` or ``sys.stdout`` (depending on access mode)"""
STDERR = '_'
"""Placeholder for ``sys.stderr``"""

def get_access(mode : 'str') -> 'int':
    """Returns the access mode constant associated with given mode string.
    
    Args:
        mode: A mode string
    
    Returns:
        The access mode constant
    
    Raises:
        ValueError, if ``mode`` does not contain a valid mode character.
    
    Examples:
        a = get_access('rb') # -> os.R_OK
    """
    for a, i in ACCESS.items():
        if a in mode:
            return i[0]
    raise ValueError("{} does not contain a valid access mode".format(mode))

def set_access(path, mode):
    """Sets file access from a mode string.
    
    Args:
        path: The file to chmod
        mode: Mode string consisting of one or more of 'r', 'w', 'x'
    
    Returns:
        The integer equivalent of the specified mode string
    """
    mode_flag = 0
    for char in mode:
        if char not in ACCESS:
            raise ValueError("Invalid mode character {}".format(char))
        mode_flag |= ACCESS[char][1]
    os.chmod(path, mode_flag)
    return mode_flag

def check_access(path : 'str', access : 'int'):
    """Check that ``path`` is accessible.
    """
    if isinstance(access, str):
        access = get_access(access)
    if path in (STDOUT, STDERR):
        if path == STDOUT and access not in (os.R_OK, os.W_OK):
            raise IOError(errno.EACCES, "STDOUT access must be r or w", path)
        elif path == STDERR and access != os.W_OK:
            raise IOError(errno.EACCES, "STDERR access must be w", path)
    elif not os.access(path, access):
        raise IOError(errno.EACCES, "{} not accessable".format(path), path)

def abspath(path : 'str') -> 'str':
    """Returns the fully resolved path associated with ``path``.
    
    Args:
        path: Relative or absolute path
    
    Returns:
        Fully resolved path
    
    Examples:
        abspath('foo') # -> /path/to/curdir/foo
        abspath('~/foo') # -> /home/curuser/foo
    """
    if path in (STDOUT, STDERR):
        return path
    return os.path.abspath(os.path.expanduser(path))

def split_path(path : 'str', keep_seps : 'bool' = True,
               resolve : 'bool' = True) -> 'tuple':
    """Splits a path into a (parent_dir, name, *ext) tuple.
    
    Args:
        path: The path
        keep_seps: Whether the extension separators should be kept as part
            of the file extensions
        resolve: Whether to resolve the path before splitting
    
    Returns:
        A tuple of length >= 2, in which the first element is the parent
        directory, the second element is the file name, and the remaining
        elements are file extensions.
    
    Examples:
        split_path('myfile.foo.txt', False)
        -> ('/current/dir', 'myfile', 'foo', 'txt')
        split_path('/usr/local/foobar.gz', True)
        -> ('/usr/local', 'foobar', '.gz')
    """
    if resolve:
        path = abspath(path)
    parent = os.path.dirname(path)
    file_parts = tuple(os.path.basename(path).split(os.extsep))
    if len(file_parts) == 1:
        seps = ()
    else:
        seps = file_parts[1:]
        if keep_seps:
            seps = tuple('{}{}'.format(os.extsep, ext) for ext in file_parts[1:])
    return (parent, file_parts[0]) + seps

def filename(path : 'str') -> 'str':
    """Returns just the filename part of ``path``. Equivalent to
    ``split_path(path)[1]``.
    """
    return split_path(path)[1]

def resolve_path(path : 'str', parent : 'str' = None) -> 'str':
    """Resolves the absolute path of the specified file and ensures that the
    file/directory exists.
    
    Args:
        path: Path to resolve
        parent: The directory containing ``path`` if ``path`` is relative
    
    Returns:
        The absolute path
    
    Raises:
        IOError: if the path does not exist or is invalid
    """
    if path in (STDOUT, STDERR):
        return path
    if parent:
        path = os.path.join(abspath(parent), path)
    else:
        path = abspath(path)
    if not os.path.exists(path):
        raise IOError(errno.ENOENT, "{} does not exist".format(path), path)
    return path

def check_path(path : 'str', ptype : 'str' = None, access=None) -> 'str':
    """Resolves the path (using ``resolve_path``) and checks that the path is
    of the specified type and allows the specified access.
    
    Args:
        path: The path to check
        ptype: 'f' for file or 'd' for directory.
        access: One of the access values from :module:`os`
    
    Returns:
        The fully resolved path
    
    Raises:
        IOError if the path does not exist, is not of the specified type,
        or doesn't allow the specified access.
    """
    path = resolve_path(path)
    if ptype is not None:
        if ptype == 'f' and not (
                path in (STDOUT, STDERR) or os.path.isfile(path)):
            raise IOError(errno.EISDIR, "{} not a file".format(path), path)
        elif ptype == 'd' and not os.path.isdir(path):
            raise IOError(errno.ENOTDIR, "{} not a directory".format(path),
                          path)
    if access is not None:
        check_access(path, access)
    return path

def check_readable_file(path : 'str') -> 'str':
    """Check that ``path`` exists and is readable.
    
    Args:
        path: The path to check
    
    Returns:
        The fully resolved path of ``path``
    """
    return check_path(path, 'f', 'r')

def check_writeable_file(path : 'str', mkdirs : 'bool' = True) -> 'str':
    """If ``path`` exists, check that it is writeable, otherwise check that
    its parent directory exists and is writeable.
    
    Args:
        path: The path to check
        mkdirs: Whether to create any missing directories (True)
    
    Returns:
        The fully resolved path
    """
    if os.path.exists(path):
        return check_path(path, 'f', 'w')
    else:
        path = abspath(path)
        dirpath = os.path.dirname(path)
        if os.path.exists(dirpath):
            check_path(dirpath, 'd', 'w')
        else:
            os.makedirs(dirpath)
        return path

### "Safe" versions of the check methods, meaning they return None
### instead of throwing exceptions

def safe_check_path(path : 'str', *args, **kwargs) -> 'str':
    try:
        return check_path(path, *args, **kwargs)
    except IOError:
        return None

def safe_check_readable_file(path : 'str') -> 'str':
    try:
        return check_readable_file(path)
    except IOError:
        return None

def safe_check_writeable_file(path : 'str') -> 'str':
    try:
        return check_writeable_file(path)
    except IOError:
        return None

def find(root : 'str', pattern, types : 'str' = 'f',
         recursive : 'bool' = True) -> 'list':
    """Find all paths under ``root`` that match ``pattern``.
    
    Args:
        root: Directory at which to start search
        pattern: File name pattern to match (string or re object)
        types: Types to return -- files ("f"), directories ("d") or both ("fd")
        recursive: Whether to search directories recursively
    
    Returns:
        List of matching paths
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    found = []
    for root, dirs, files in os.walk(root):
        if types != "f":
            for d in filter(lambda x: pattern.match(x), dirs):
                found.append(os.path.join(root, d))
        if types != "d":
            for f in filter(lambda x: pattern.match(x), files):
                found.append(os.path.join(root, f))
    return found

executable_cache = {}
"""Cache of full paths to executables"""

def get_executable_path(executable : 'str') -> 'str':
    """Get the full path of ``executable``.
    
    Args:
        executable: A executable name
    
    Returns:
        The full path of ``executable``, or None if the path cannot be found.
    """
    exe_name = os.path.basename(executable)
    if exe_name in executable_cache:
        return executable_cache[exe_name]
    
    def check_executable(fpath):
        try:
            return check_path(fpath, 'f', 'x')
        except:
            return None
    
    exe_file = check_executable(executable)
    if not exe_file:
        for path in os.get_exec_path():
            exe_file = check_executable(os.path.join(path.strip('"'), executable))
            if exe_file:
                break
    
    executable_cache[exe_name] = exe_file
    return exe_file

# tempfiles

class TempPathDescriptor(object):
    """Describes a temporary file or directory within a TempDir.
    
    Args:
        name: The file/direcotry name
        subdir: A TempPathDescriptor
    """
    def __init__(self, name=None, subdir=None, mode=None,
                 suffix='', prefix='', contents='', path_type='f'):
        if contents and path_type != 'f':
            raise ValueError("'contents' only valid for files")
        self.path_type = path_type
        self.subdir = subdir
        self.name = name
        self.prefix = prefix
        self.suffix = suffix
        if not mode and self.subdir:
            self.mode = subdir.mode
        else:
            self.mode = mode
        self.contents = contents
        self.root = None
        self._abspath = None
        self._relpath = None
    
    @property
    def exists(self):
        return self._abspath is not None and os.path.exists(self._abspath)
    
    @property
    def absolute_path(self):
        if self._abspath is None:
            self._init_path()
        return self._abspath
    
    @property
    def relative_path(self):
        if self._relpath is None:
            self._init_path()
        return self._relpath
    
    def _init_path(self):
        if self.root is None:
            raise Exception("Cannot determine absolute path without 'root'")
        if self.subdir:
            self._relpath = os.path.join(self.subdir.relative_path, self.name)
        else:
            self._relpath = self.name
        self._abspath = os.path.join(self.root.path, self._relpath)
        
    def set_root(self, tempdir):
        self.root = tempdir
        if self.mode is None:
            self.mode = tempdir.mode
    
    def set_access(self, mode=None):
        if mode:
            self.mode = mode
        if self.path is None or self.mode is None:
            raise Exception("Both 'path' and 'mode' must be set before setting "
                            "access permissions")
        set_access(self.absolute_path, self.mode)
    
    def create(self):
        if self.path_type in ('d', 'dir'):
            os.mkdir(self.absolute_path)
        else:
            if self.path_type == 'fifo':
                os.mkfifo(self.absolute_path)
            
            if self.contents or self.path_type != 'fifo':
                with open(self.absolute_path, 'wt') as fh:
                    fh.write(self.contents or '')

class TempDir(object):
    """Context manager that creates a temporary directory and cleans it up
    upon exit.
    
    Args:
        mode: Access mode to set on temp directory. All subdirectories and
            files will inherit this mode unless explicity set to be different.
        paths: Iterable of TempPathDescriptors.
        kwargs: Additional arguments passed to tempfile.mkdtemp
    
    By default all subdirectories and files inherit the mode of the temporary
    directory. If TempPathDescriptors are specified, the files are created
    before permissions are set, enabling creation of a read-only temporary file
    system.
    """
    def __init__(self, mode='rwx', path_descriptors=None, **kwargs):
        self.path = abspath(tempfile.mkdtemp(**kwargs))
        self.mode = mode
        self.paths = {}
        if paths:
            self.make_paths(*paths)
        set_access(self.path, mode)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
    
    def __getitem__(self, path):
        return self.paths[path]
    
    def __contains__(self, path):
        return path in self.paths
        
    def close(self):
        """Delete the temporary directory and all files/subdirectories within.
        """
        shutil.rmtree(self.path)
    
    def make_path(self, desc=None, apply_permissions=True, **kwargs):
        if not desc:
            desc = TempPathDescriptor(**kwargs)
        
        parent = desc.subdir.path if desc.subdir else self.path
        if desc.name:
            path = os.path.join(parent, desc.name)
        elif desc.path_type in ('d', 'dir'):
            path = tempfile.mkdtemp(
                prefix=desc.prefix, suffix=desc.suffix, dir=parent)[1]
            desc.name = os.path.basename(path)
        else:
            path = tempfile.mkstemp(
                prefix=desc.prefix, suffix=desc.suffix, dir=parent)[1]
            desc.name = os.path.basename(path)
        
        desc.set_root(self)
        desc.create()
        if apply_permissions:
            desc.set_access()
        
        self.paths[desc.absolute_path] = desc
        self.paths[desc.relative_path] = desc
        
        return desc.absolute_path
    
    def make_paths(self, *path_descriptors):
        # Create files/directories without permissions
        paths = [
            self.make_path(desc, apply_permissions=False)
            for desc in path_descriptors]
        # Now apply permissions after all paths are created
        for desc in path_descriptors:
            desc.set_access()
        return paths
    
    def make_empty_files(self, n, **kwargs):
        return list(self.make_path(FileDescriptor(**kwargs) for i in range(n)))
