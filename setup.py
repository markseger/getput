#!/usr/bin/python

from distutils.core import setup

setup(name='gptools',
      version='0.2.1',
      description='getput tools',
      author='Mark Seger',
      author_email='mark.seger@hpe.com',
      url='https://github.com/markseger/getput',

      data_files=[('/usr/bin',['getput','gpmulti','gpsuite']),
                  ('/etc/gpsuite.d', ['gpsuite.conf']),
                  ('/usr/share/doc/gptools',['Getting-Started.txt','RELEASE-gptools','Introduction.pdf']),
                  ('/usr/share/man/man1',['getput.1', 'gpmulti.1', 'gpsuite.1'])]
     )
