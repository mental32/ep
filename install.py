import sys

assert sys.version_info[:2] >= (3, 6), 'fatal: requires python3.6+'

import argparse
import subprocess
import importlib

PYTHON_PATH = sys.executable
DEPENDENCIES = [
    {
        'name': 'discord', 
        'src': 'https://github.com/Rapptz/discord.py@rewrite#egg=discord.py[voice]',
        'git': True,
        'check': lambda m: (m.__version__, m.__author__) == ('1.0.0a', 'Rapptz')
    },
    {
        'name': 'flask',
    },
    {
        'name': 'rapidjson',
        'src': 'python-radidjson'
    }
]


def install_dependency(name, git=False, src=None, check=None):
    check = check or (lambda key: True)

    def dependency_check(name, pred, exception=ImportError):
        try:
            module = importlib.import_module(name)
            if not pred(module):
                raise ImportError
            version = module.__version__
        finally:
            try:
                del module
                del sys.modules[name]
            except NameError:
                pass

        return version

    try:
        version = dependency_check(name, check)
    except ImportError:
        status = subprocess.check_call(f'{PYTHON_PATH} -m pip install -U{" git+" if git else " "}{name if src is None else src}')
        dependency_check(name, check, exception=RuntimeError(f'fatal: Could not install dependency: {name}[{src}]'))
        return status, None
    else:
        return -1, version

def main():
    for dep in DEPENDENCIES:
        print(f'Installing {dep["name"]}...', end='')
        sts, _v = install_dependency(**dep)
        if sts == -1:
            print(f'Already installed: {dep["name"]}({_v})')
        else:
            print(f'Installed {dep["name"]}')

if __name__ == '__main__':
    main()
