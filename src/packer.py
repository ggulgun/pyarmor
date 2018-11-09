#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#############################################################
#                                                           #
#      Copyright @ 2018 -  Dashingsoft corp.                #
#      All rights reserved.                                 #
#                                                           #
#      pyarmor                                              #
#                                                           #
#      Version: 4.3.2 -                                     #
#                                                           #
#############################################################
#
#
#  @File: packer.py
#
#  @Author: Jondy Zhao(jondy.zhao@gmail.com)
#
#  @Create Date: 2018/11/08
#
#  @Description:
#
#   Pack obfuscated Python scripts with any of third party
#   tools: py2exe, py2app, cx_Freeze, PyInstaller
#

'''After the py2exe or cx_Freeze setup script works, this tool let you
to obfuscate all the python source scripts and package them. The basic
usage:

    python packer.py --type py2exe /path/to/src/entry.py

It will replace all the original python scripts with obfuscated ones
in the output path of py2exe or cx_Freeze.

'''

import logging
import os
import shutil
import subprocess
import sys
import time

from distutils.util import get_platform
from py_compile import compile as compile_file
from zipfile import PyZipFile

try:
    import argparse
except ImportError:
    # argparse is new in version 2.7
    import polyfills.argparse as argparse

try:
    from pyarmor import main as call_armor
except ImportError:
    from pyarmor.pyarmor import main as call_armor

def update_library(libzip, dist):
    # It's simple ,but there is a problem that old .pyc
    # can not be overwited
    # with PyZipFile(libzip, 'a') as f:
    #     f.writepy(dist)

    filelist = []
    for root, dirs, files in os.walk(dist):
        filelist.extend([os.path.join(root, s) for s in files])

    with PyZipFile(libzip, 'r') as f:
        namelist = f.namelist()
        f.extractall(dist)

    for s in filelist:
        compile_file(s, s + 'c')

    with PyZipFile(libzip, 'w') as f:
        for name in namelist:
            f.write(os.path.join(dist, name), name)

def armorcommand(func):
    def wrap(*args, **kwargs):
        path = os.getcwd()
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        try:
            return func(*args, **kwargs)
        finally:
            os.chdir(path)
    return wrap

@armorcommand
def _packer(src, entry, setup, packcmd, dist, libname):
    dest = os.path.dirname(setup)
    script = os.path.basename(setup)

    output = os.path.join(dest, dist)
    project = os.path.join('projects', 'build-for-packer')

    options = 'init', '--type', 'app', '--src', src, '--entry', entry, project
    call_armor(options)

    filters = ('global-include *.py', 'prune build, prune dist',
               'exclude %s %s pytransform.py' % (entry, script))
    options = ('config', '--runtime-path', '',  '--disable-restrict-mode', '1',
               '--manifest', ','.join(filters), project)
    call_armor(options)

    os.chdir(project)

    options = 'build', '--no-runtime', '--output', 'dist'
    call_armor(options)

    shutil.copy(os.path.join('..', '..', 'pytransform.py'), src)
    shutil.move(os.path.join(src, entry), '%s.bak' % entry)
    shutil.move(os.path.join('dist', entry), src)

    p = subprocess.Popen([sys.executable, script, packcmd], cwd=dest)
    p.wait()
    shutil.move('%s.bak' % entry, os.path.join(src, entry))
    os.remove(os.path.join(src, 'pytransform.py'))

    update_library(os.path.join(output, libname), 'dist')

    options = 'build', '--only-runtime', '--output', 'runtimes'
    call_armor(options)

    for s in os.listdir('runtimes'):
        if s == 'pytransform.py':
            continue
        shutil.copy(os.path.join('runtimes', s), output)

    os.chdir('..')
    shutil.rmtree(os.path.basename(project))

def packer(args):
    bintype = 'freeze' if args.type.lower().endswith('freeze') else 'py2exe'

    if args.path is None:
        src = os.path.abspath(os.path.dirname(args.entry[0]))
        entry = os.path.basename(args.entry[0])
    else:
        src = os.path.abspath(args.path)
        entry = os.path.relpath(args.entry[0], args.path)
    setup = os.path.join(src, 'setup.py') if args.setup is None \
        else os.path.abspath(args.setup)

    dist = os.path.join(
        'build', 'exe.%s-%s' % (get_platform(), sys.version[0:3])
    ) if bintype == 'freeze' else 'dist'
    packcmd = 'py2exe' if bintype == 'py2exe' else 'build'
    libname = 'library.zip' if bintype == 'py2exe' else \
        'python%s%s.zip' % sys.version_info[:2]

    _packer(src, entry, setup, packcmd, dist, libname)

def main(args):
    parser = argparse.ArgumentParser(
        prog='packer.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Pack obfuscated scripts',
        epilog=__doc__,
    )
    parser.add_argument('-v', '--version', action='version', version='v0.1')

    parser.add_argument('-t', '--type', default='py2exe',
                        choices=('py2exe', 'py2app', 'cx_Freeze', 'PyInstaller'))
    parser.add_argument('-p', '--path', help='Source path of Python scripts')
    parser.add_argument('-s', '--setup', help='Setup script')
    parser.add_argument('entry', metavar='Script', nargs=1, help='Entry script')

    packer(parser.parse_args(args))

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)-8s %(message)s',
    )
    main(sys.argv[1:])