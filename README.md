This is the getput benchmarking tool suite.

Dependencies:

python-swiftclient

Installation:

git clone https://github.com/markseger/getput.git
cd getput
sudo python setup.py install

Documentation:

/usr/share/doc/gptools/getting-started.txt
/usr/share/doc/gptools/Introduction.pdf

Notes:

Version 2 of the swift client fixes the problem with longer PUT latencies
for small objects BUT you need to make sure you have the latest version
of python-requests which is not currently in the apt-get repository as of
this writing.  Running getput with that version results in slower 1K PUTs
than 2K PUTs.  I've found installing requests-2.2.1 from the tarball fixes
the problem.
