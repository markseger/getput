This is the getput benchmarking tool suite.

Dependencies:

python-swiftclient

Installation:

git clone https://github.com/markseger/getput.git
<BR>cd getput
<BR>sudo python setup.py install

Documentation:

/usr/share/doc/gptools/getting-started.txt
<BR>/usr/share/doc/gptools/Introduction.pdf

Notes:

Version 2 of the swift client fixes the problem with longer PUT latencies
for small objects BUT you need to make sure you have the latest version
of python-requests which is not currently in the apt-get repository as of
this writing.  Running getput with that version results in slower 1K PUTs
than 2K PUTs.  I've found installing requests-2.2.1 from the tarball fixes
the problem.

Keystone v3: Export the following variables to your env

```
OS_REGION_NAME=region
OS_AUTH_URL=url
OS_USERNAME=user
OS_USER_DOMAIN_NAME=domain
OS_PROJECT_NAME=project
OS_PROJECT_DOMAIN_NAME=domain
OS_PASSWORD=pwd
```
