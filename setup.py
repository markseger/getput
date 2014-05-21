#!/usr/bin/python

from distutils.core import setup

setup(name='gptools',
      version='0.1.0',
      description='getput tools',
      author='Mark Seger',
      author_email='mark.seger@hp.com',
      url='https://github.com/markseger/getput',

      data_files=[('/usr/bin',['getput','gpmulti','gpsuite']),
                  ('/etc/gpsuite.d', ['gpsuite.conf']),
                  ('/usr/share/doc/gptools',['getting-started.txt','RELEASE-gptools']),
                  ('/usr/share/man/man1',['getput.1', 'gpmulti.1', 'gpsuite.1'])]
     )
