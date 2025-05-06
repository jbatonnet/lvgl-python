# Detect current platform
_is_micropython = None
_is_windows = None
_is_linux = None

_target_library = None

try:
    import micropython

    _is_micropython = True
    _is_windows = False
    _is_linux = True

    _target_library = 'lvgl-arm-linux-uclibc.so'
except:
    _is_micropython = False

    try:
        import cffi
        import platform

        architecture = platform.architecture()
        _is_windows = architecture[1] == 'WindowsPE'
        _is_linux = platform.system() == 'Linux'

        if _is_windows:
            if architecture[0] == '32bit':
                _target_library = 'lvgl-x86-windows.dll'
            elif architecture[0] == '64bit':
                _target_library = 'lvgl-x64-windows.dll'
        elif _is_linux:
            _target_library = 'lvgl-arm-linux-uclibc.so'
    except:
        pass

if _is_micropython is None or _target_library is None:
    raise Exception('Current platform is not supported')

class helpers:
    def is_windows():
        return not _is_micropython and _is_windows == True
    def is_linux():
        return _is_micropython or _is_linux == True
    def is_cpython():
        return not _is_micropython
    def is_micropython():
        return _is_micropython

# Find the library
if _is_micropython:
    import uos as os
else:
    import os
    
def exists(path):
    try:
        os.stat(path)
        return True
    except:
        return False

_library_path = f'{os.getcwd()}/{_target_library}'
if not exists(_library_path):
    _library_path = f'{os.path.dirname(os.path.realpath(__file__))}/{_target_library}'
if not exists(_library_path):
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', '').split(':')
    for path in ld_library_path:
        ld_library_path = f'{path}/{_target_library}'
        if exists(ld_library_path):
            break
if not exists(_library_path):
    raise Exception(f'Unable to find library {_target_library}')
