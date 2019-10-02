# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016-2019 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
__authors__ = ["V.A. Sole", "T. Vincent"]
__license__ = "MIT"
__date__ = "11/07/2018"


from glob import glob
import os
import sys
from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.build_ext import build_ext


# Plugins

class PluginBuildExt(build_ext):
    """Build command for DLLs that are not Python modules

    This is actually only useful for Windows
    """

    def get_export_symbols(self, ext):
        """Overridden to remove PyInit_* export"""
        return ext.export_symbols

    def get_ext_filename(self, ext_name):
        """Overridden to use .dll as file extension"""
        if sys.platform.startswith('win'):
            return os.path.join(*ext_name.split('.')) + '.dll'
        else:
            return super(PluginBuildExt, self).get_ext_filename(ext_name)


class HDF5PluginExtension(Extension):
    """Extension adding specific things to build a HDF5 plugin"""

    @staticmethod
    def __prepend(kwargs, key, extra_list):
        kwargs[key] = extra_list + kwargs.get(key, [])

    def __init__(self, name, **kwargs):
        if sys.platform.startswith('win'):
            self.__prepend(kwargs, 'sources', ['src/register_win32.c'])
            self.__prepend(kwargs, 'export_symbols', ['register_filter'])
            self.__prepend(kwargs, 'define_macros', [('H5_BUILT_AS_DYNAMIC_LIB', None)])
            self.__prepend(kwargs, 'libraries', ['hdf5'])
            hdf5_lib_dir = os.environ.get('HDF5_LIB_DIR', None)
            if hdf5_lib_dir:
                self.__prepend(kwargs, 'library_dirs', [hdf5_lib_dir])
        else:
            self.__prepend(kwargs, 'sources', ['src/hdf5_dl.c'])
            self.__prepend(kwargs, 'export_symbols', ['init_filter'])

        hdf5_inc_dir = os.environ.get('HDF5_INC_DIR', None)
        if hdf5_inc_dir:
            self.__prepend(kwargs, 'include_dirs', [hdf5_inc_dir])
        self.__prepend(kwargs, 'define_macros', [('H5_USE_18_API', None)])
        super(HDF5PluginExtension, self).__init__(name, **kwargs)


def prefix(directory, files):
    """Add a directory as prefix to a list of files.

    :param str directory: Directory to add as prefix
    :param List[str] files: List of relative file path
    :rtype: List[str]
    """
    return ['/'.join((directory, f)) for f in files]


# bitshuffle (+lz4) plugin
# Plugins from https://github.com/kiyo-masui/bitshuffle
# TODO compile flags + openmp
bithsuffle_dir = 'src/bitshuffle'

bithsuffle_plugin = HDF5PluginExtension(
    "hdf5plugin.plugins.libh5bshuf",
    sources=prefix(bithsuffle_dir,
        ["src/bshuf_h5plugin.c", "src/bshuf_h5filter.c",
         "src/bitshuffle.c", "src/bitshuffle_core.c",
         "src/iochain.c", "lz4/lz4.c"]),
    depends=prefix(bithsuffle_dir,
        ["src/bitshuffle.h", "src/bitshuffle_core.h",
         "src/iochain.h", 'src/bshuf_h5filter.h',
         "lz4/lz4.h"]),
    include_dirs=prefix(bithsuffle_dir, ['src/', 'lz4/']),
    )


# blosc plugin
# Plugin from https://github.com/Blosc/hdf5-blosc
# c-blosc from https://github.com/Blosc/c-blosc
# TODO compile flags avx2/sse2, snappy
hdf5_blosc_dir = 'src/hdf5-blosc/src/'
blosc_dir = 'src/c-blosc/'

# blosc sources
sources = [f for f in glob(blosc_dir + 'blosc/*.c')
           if 'avx2' not in f and 'sse2' not in f]
depends = [f for f in glob(blosc_dir + 'blosc/*.h')
        if 'avx2' not in f and 'sse2' not in f]
include_dirs = [blosc_dir, blosc_dir + 'blosc']
define_macros = []

# compression libs
# lz4
lz4_sources = glob(blosc_dir + 'internal-complibs/lz4*/*.c')
lz4_depends = glob(blosc_dir + 'internal-complibs/lz4*/*.h')
lz4_include_dirs = glob(blosc_dir + 'internal-complibs/lz4*')

sources += lz4_sources
depends += lz4_depends
include_dirs += lz4_include_dirs
define_macros.append(('HAVE_LZ4', 1))

# snappy
# TODO

#zlib
sources += glob(blosc_dir + 'internal-complibs/zlib*/*.c')
depends += glob(blosc_dir + 'internal-complibs/zlib*/*.h')
include_dirs += glob(blosc_dir + 'internal-complibs/zlib*')
define_macros.append(('HAVE_ZLIB', 1))

# zstd
sources += glob(blosc_dir +'internal-complibs/zstd*/*/*.c')
depends += glob(blosc_dir +'internal-complibs/zstd*/*/*.h')
include_dirs += glob(blosc_dir + 'internal-complibs/zstd*')
include_dirs += glob(blosc_dir + 'internal-complibs/zstd*/common')
define_macros.append(('HAVE_ZSTD', 1))


blosc_plugin = HDF5PluginExtension(
    "hdf5plugin.plugins.libh5blosc",
    sources=sources + \
        prefix(hdf5_blosc_dir,['blosc_filter.c', 'blosc_plugin.c']),
    depends=depends + \
        prefix(hdf5_blosc_dir, ['blosc_filter.h', 'blosc_plugin.h']),
    include_dirs=include_dirs + [hdf5_blosc_dir],
    define_macros=define_macros,
    )


# lz4 plugin
# Source from https://github.com/nexusformat/HDF5-External-Filter-Plugins
lz4_dir = 'src/HDF5-External-Filter-Plugins/LZ4/src/'

lz4_plugin = HDF5PluginExtension(
    "hdf5plugin.plugins.libh5lz4",
    sources=['src/HDF5-External-Filter-Plugins/LZ4/src/H5Zlz4.c'] + \
            lz4_sources,
    depends=lz4_depends,
    include_dirs=lz4_include_dirs,
    libraries=['Ws2_32'] if sys.platform == 'win32' else [],
    )


extensions=[lz4_plugin,
            bithsuffle_plugin,
            blosc_plugin,
            ]

# setup

# ########## #
# version.py #
# ########## #

def get_version():
    """Returns current version number from version.py file"""
    dirname = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, dirname)
    import version
    sys.path = sys.path[1:]
    return version.strictversion


class build_py(_build_py):
    """
    Enhanced build_py which copies version.py to <PROJECT>._version.py
    """
    def find_package_modules(self, package, package_dir):
        modules = _build_py.find_package_modules(self, package, package_dir)
        if package == PROJECT:
            modules.append((PROJECT, '_version', 'version.py'))
        return modules


PROJECT = 'hdf5plugin'
author = "ESRF - Data Analysis Unit"
description = "HDF5 Plugins for windows,MacOS and linux"
f = open("README.rst")
long_description=f.read()
f.close()
classifiers = ["Development Status :: 4 - Beta",
               "Environment :: Console",
               "Environment :: MacOS X",
               "Environment :: Win32 (MS Windows)",
               "Intended Audience :: Education",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: MIT License",
               "Natural Language :: English",
               "Operating System :: POSIX :: Linux",
               "Operating System :: MacOS",
               "Operating System :: Microsoft :: Windows",
               "Programming Language :: Python :: 2.7",
               "Programming Language :: Python :: 3.4",
               "Programming Language :: Python :: 3.5",
               "Programming Language :: Python :: 3.6",
               "Programming Language :: Python :: 3.7",
               "Topic :: Software Development :: Libraries :: Python Modules",
               ]
cmdclass = dict(build_ext=PluginBuildExt,
                build_py=build_py)


if __name__ == "__main__":
    setup(name=PROJECT,
          version=get_version(),
          author=author,
          classifiers=classifiers,
          description=description,
          long_description=long_description,
          packages=[PROJECT],
          ext_modules=extensions,
          install_requires=['h5py'],
          setup_requires=['setuptools'],
          cmdclass=cmdclass,
          )

