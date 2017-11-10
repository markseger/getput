#!/usr/bin/python

from distutils.core import setup

setup(name='gptools',
      version='0.3.0',
      description='getput tools',
      author='Mark Seger',
      author_email='mseger@suse.com',
      url='https://github.com/markseger/getput',

      data_files=[('/usr/bin',['getput','gpmulti','gpsuite','gpsum','gpwhere']),
                  ('/etc/gpsuite.d', ['gpsuite.conf']),
                  ('/usr/share/doc/gptools',['getting-started.txt','RELEASE-gptools','Introduction.pdf']),
                  ('/usr/share/man/man1',['getput.1', 'gpmulti.1', 'gpsuite.1', 'gpsum.1', 'gpwhere.1'])]
     
