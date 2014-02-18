#!/usr/bin/python -u

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Use of this script is subject to HP Terms of Use at
# http://www8.hp.com/us/en/privacy/terms-of-use.html.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# debug
#    1 - print some basic stuff
#    2 - print commands
#    4 - print details of getput results a line at a time
#    8 - show individual  latencies
#   16 - show trimmed test output
#   32 - show all getput results before processing any
#   64 - trace execution to /tmp for gpmulti
#  128 - tell getput to trace execution to /tmp
#  256 - show pretest command

import os
import re
import sys
import glob
import time
import subprocess
from optparse import OptionParser, OptionGroup
from multiprocessing import Process, Queue

global lock
global results_fname
global lat_dist


def logexec(text):

    if debug & 64:
        logfile = '/tmp/gpmulti-exec-%s.log' % (time.strftime('%Y%m%d'))
        log = open(logfile, 'a')
        log.write('%s %s\n' % (time.strftime('%H:%M:%S', time.gmtime()), text))
        log.close()


def error(text):
    print text
    sys.exit()


def main(argv):

    global debug, options, procset, sizeset

    debug = 0
    procset = [1]

    parser = OptionParser(add_help_option=False)
    group0 = OptionGroup(parser, 'these are the basic switches')
    group0.add_option('--creds',    dest='creds',
                      help='credentials file')
    group0.add_option('--csv',    dest='csv',
                      help='report output in csv format',
                      action='store_true')
    group0.add_option('--nodes',    dest='nodes',
                      help='file containing list of nodes to run on')
    group0.add_option('--numnodes', dest='numnodes',
                      help="use this number of nodes in '--file'")
    group0.add_option('--sshkey',   dest='sshkey',
                      help='ssh key file to be used with ssh -i')
    group0.add_option('--sync',     dest='sync',
                      help='sync time, secs from NOW', default='5')
    group0.add_option('--username', dest='username',
                      help='use this for the ssh login name', default='')
    group0.add_option('-h', '--help', dest='help',
                      help='show this help message and exit',
                      action='store_true')
    group0.add_option('-v', '--version',  dest='version',
                      help='print version and exit', action='store_true')
    parser.add_option_group(group0)

    group1 = OptionGroup(parser, 'these are required for getput')
    group1.add_option('-c', '--cname',    dest='cname',
                      help='container name')
    group1.add_option('-o', '--oname',    dest='oname',
                      help='object name prefix')
    group1.add_option('-n', '--nobjects', dest='numobjs',
                      help='max number of objects', default=0)
    group1.add_option('-s', '--size',     dest='sizeset',
                      help='object size, [def=32k]')
    group1.add_option('-t', '--tests',    dest='tests',
                      help='tests to run [gpd]')
    parser.add_option_group(group1)

    group2 = OptionGroup(parser, 'these are optionsal for getput')
    group2.add_option('--nocompress', dest='nocompress',
                      help="disable ssl compression",
                      action='store_true', default=False)
    group2.add_option('--cont-nodelete', dest='cont_nodelete',
                      help="do not delete container after a delete test",
                      action='store_true',
                      default=False)
    group2.add_option('--ctype',     dest='ctype',
                      help="container type: shared|bynode|byproc, def=shared")
    group2.add_option('--latexc',    dest='latexc',
                      help="stop when max latency matches exception")
    group2.add_option('--ldist',    dest='ldist',
                      help="report latency distributions at this granularity")
    group2.add_option('--logops',   dest='logops',
                      help="pass this to getput as --logops value")
    group2.add_option('--nohead',   dest='nohead',
                      help="don't print any headers", action='store_true')
    group2.add_option('--objopts',  dest='objopts', default='',
                      help='object options [acfu]')
    group2.add_option('--preauthtoken', dest='preauthtoken',
                      help="tell getput to use a pre-defined preauthtoken",
                      default='')
    group2.add_option('--pretest',  dest='pretest',
                      help="run this script before each test")
    group2.add_option('--procs',    dest='procset',
                      help="number of processes to run")
    group2.add_option('--proxies',  dest='proxies', default='',
                      help='bypass load balancer and connect directly')
    group2.add_option('--quiet',    dest='quiet', default=False,
                      help='suppress api errors & sync time warnings',
                      action='store_true')
    group2.add_option('--runtime',  dest='runtime',
                      help="runtime in secs")
    group2.add_option('--utc',      dest='utc', action='store_true',
                      help="append -utc to container name")
    group2.add_option('--warnexit', dest='warnexit',
                      help='exit on warnings', action='store_true')
    parser.add_option_group(group2)

    group3 = OptionGroup(parser, 'development and testing')
    group3.add_option('-d', '--debug',    dest='debug',
                      help='debugging mask')
    group3.add_option('-f', '--flavor',   dest='flavor',
                      help="append '-FLAVOR' onto getput command name",
                      default='')
    parser.add_option_group(group3)

    try:
        (options, args) = parser.parse_args()
    except:
        print 'invalid command'
        sys.exit()

    if options.help:
        parser.print_help()
        sys.exit()

    if options.version:
        print 'gpmulti V%s\n\n%s' % (version, copyright)
        sys.exit()

    if options.debug:
        try:
            debug = int(options.debug)
        except ValueError:
            error('-d must be an integer')

    if not options.creds:
        error('--creds required')

    if options.nodes:
        if not os.path.exists(options.nodes):
            error("nodes file '%s' doesn't exist" % options.nodes)

    if options.sshkey:
        if not os.path.exists(options.sshkey):
            error("ssh key file doesn't exist")

    if options.tests:
        if not (re.match('[,pgdPGD]+\Z', options.tests)):
            error("valid tests are any comma separated values of: gpd")
    else:
        error('define test list with -t or --tests')

    if not options.cname:
        error('specify container name with -c or --cname')

    # test can contain some of its own switches so just look at basename
    if options.pretest and not os.path.exists(options.pretest.split()[0]):
        error("pretest '%s' does not exist" % options.pretest)

    #    T e s t    D e p e n d e n t    S w i t c h e s

    if re.match('[gpd]', options.tests):
        if not options.oname:
            error('get, put and delete tests require object name')

    if options.sizeset:
        if re.search(',', options.sizeset):
            if not re.match('p', options.tests):
                error('multiple obj sizes require PUT test')
        sizeset = []
        for size in options.sizeset.split(','):
            match = re.match('(\d+)([kmg]?\Z)', size, re.I)
            if (match):
                sizeset.append(size)
            else:
                error('object size must be a number OR number + k/m/g')
    elif re.search('p', options.tests):
        error('put test requires object size')

    if options.procset:
        procset = []
        for proc in options.procset.split(','):
            try:
                procset.append(int(proc))
            except ValueError:
                error('--procs must be an integer')

    if options.ldist:
        if not re.match('\d+$', options.ldist):
            error('--ldist must be an integer')
        if options.ldist > '3':
            error("--ldist > 3 not supported")

    if options.ctype:
        if not re.match('shared|bynode|byproc', options.ctype):
            error("invalid ctype, expecting: 'shared|bynode|byproc'")

    if options.numnodes:
        if not re.match('\d+$', options.numnodes) \
                and not re.match('\d+:\d+$', options.numnodes):
            error('--numnodes must be an integer')

    if options.numobjs:
        if not re.match('\d+$', options.numobjs):
            error("-n must be an integer")

    if options.sync:
        if not re.match('\d+$', options.sync):
            error('sync time must be an integer')

    if options.runtime:
        if not re.match('\d+$', options.runtime):
            error('--runtime must be an integer')

    if args:
        print "Extra command argument(s):", args
        sys.exit()

    if not options.runtime and not options.numobjs:
        error('specify at least one of -n/--runtime')


def cvtFromKMG(str):
    """
    converts a string containing K, M or G to its equivilent number
    """

    # remember, we already verify sizeset[]
    match = re.match('(\d+)([kmg]?\Z)', str, re.I)
    size = int(match.group(1))
    type = match.group(2).lower()
    if type == '':
        objsize = size
    if type == 'k':
        objsize = size * 1024
    elif type == 'm':
        objsize = size * 1024 * 1024
    elif type == 'g':
        objsize = size * 1024 * 1024 * 1024
    return(objsize)


def trim(str):

    temp = re.search('=(.*)', str).group(1)
    temp = re.sub('MB/s', '', temp)
    return(temp)


def build_command(timenow, test, size_index, procs, utc, putcount):

    command = ''
    getput_name = './getput'
    if options.flavor != '':
        getput_name += "-%s" % options.flavor

    # if --utc puts then generate a container name of the form:
    # cname-utc. then since we're doing puts with a utc stamp in the
    # container name we need to use THAT modifier on subsequent tests,
    # including subsequent PUTs
    cname = options.cname
    utcsw = ''
    if options.utc:
        if test == 'p' and putcount == 1:
            cname = options.cname
            utcsw = ' --utc'
        else:
            cname = '%s-%s' % (options.cname, utc)
            utcsw = ''

    osize = cvtFromKMG(sizeset[size_index])

    # note, we're managing removal of containers after delete tests
    synctime = timenow + int(options.sync)
    command = '%s -c%s -o%s' % (getput_name, cname, options.oname)
    command += ' -s%s -t%s --procs %d %s' % (osize, test, procs, utcsw)
    command += ' --cont-nodelete --sync %d --nohead' % synctime

    if test == 'p':
        command += ' --putsperproc'
        runtime = int(options.runtime)
    else:
        # give get/del plenty of time to complete
        runtime = int(options.runtime) * 2

    if debug & 128:
        command += " --debug 128"

    if options.creds != '':
        command += " --creds %s" % options.creds

    if options.ctype:
        command += " --ctype %s" % options.ctype

    if options.preauthtoken != '':
        command += " --preauthtoken %s" % options.preauthtoken

    if options.logops:
        command += " --logops %s" % options.logops

    if options.latexc:
        command += " --latexc %s" % options.latexc

    if options.ldist:
        command += " --ldist %s" % options.ldist

    if options.nocompress:
        command += " --nocompress"

    if options.objopts:
        command += " --objopts %s" % options.objopts

    if options.proxies:
        command += " --proxies %s" % options.proxies

    if options.quiet:
        command += " --quiet"

    if options.runtime:
        command += " --runtime %d" % runtime

    if options.warnexit:
        command += " --warnexit"

    return(command)


def execute(queue, command):

    match = re.search('-t(\S).*rank (\d+)', command)
    test = match.group(1)
    rank = match.group(2)

    errlog = '/tmp/gpmulti-%s-%s-%d.err' % (test, rank, time.time())
    command += ' 2>%s' % errlog
    try:
        results = subprocess.check_output(command, shell=True)
        os.remove(errlog)
    except subprocess.CalledProcessError as err:
        print "getput error, see %s for details" % errlog
        queue.put("unexpected getput error, see %s for details" % errlog)
        return

    # VERY unexepected!!!
    try:
        if results == '':
            print "NO RESULTS!!!"
            queue.put("error: no results")
            return
    except UnboundLocalError:
        print "NO RESULTS exception!!!"
        queue.put("error: no results exception")
        return

    if debug & 32:
        print "Results", results

    trimmed = ''
    for line in results.split('\n'):
        # note that if random tests, the get/put/del will be followed by R
        if re.search('error|warning|debug| getR* | putR* | delR* |PutsPerProc',
                     line, re.IGNORECASE):
            trimmed += "%s\n" % line
        elif debug & 16:
            print line

    queue.put(trimmed)


def print_header():

    hdr = "%-5s  %4s  %4s  %-5s  %-8s  %-8s  %8s  %5s  %7s %4s %7s %7s  %10s" \
        % ('#Test', 'Clts', 'Proc', 'OSize', 'Start', 'End', 'MB/Sec', 'Ops',
         'Ops/Sec', 'Errs', 'Latency', 'Median', 'LatRange')

    if options.ldist:
        ldist = int(options.ldist)
        ldist10 = 10 ** ldist
        for i in (0, 1, 2, 3, 4, 5, 10, 20, 30, 40, 50):
            f10 = "%.*f" % (ldist, float(i) / ldist10)
            hdr = "%s %5s" % (hdr, f10)
    hdr += "    %4s %s %s " % ('%CPU', 'Comp', 'TimeStamp')

    # in csv mode, just replace all whitspace with commas
    if options.csv:
        hdr = re.sub('\s+', ',', hdr)
        hdr = re.sub(',$', '', hdr)
    print hdr


def print_results(queue, putcount):

    lmin = 9999
    lmax = 0
    mbps = ops = iops = latency = median = items = errs = percent = 0

    lat_dist = []
    for i in range(11):
        lat_dist.append(0)

    puts_per_proc = []
    for i in remote_nodes:
        puts_per_proc.append(0)

    # split line and skip errors (I think)
    # if nothing left when done, THEN it's a serious problem
    status = 1
    for node in remote_nodes:
        results = queue.get()

        for line in results.split('\n'):
            if line == '':
                continue

            if debug & 4:
                print 'Line:', line

            # this will need to evolve, but for now treat any error messages
            # EXCEPT 'apierror' as serious and don't expect any output
            if re.search('error|warning|debug', results, re.IGNORECASE):
                if re.search('apierror', line):
                    print line
                    continue
                elif re.search('warning|debug', line, re.IGNORECASE):
                    print line
                    warnexit = options.warnexit
                    if re.search('warning', line, re.IGNORECASE) and warnexit:
                        status = -1
                    continue
                elif re.search('error', line, re.IGNORECASE):
                    print "*** Remote Execution Error on node %s ***" % node
                    print results
                    sys.exit()

            fields = line.split()
            if re.match('P', line):
                puts_per_proc[rank] = line.split()[1]
                continue

            # used as index for puts_pre_proc
            rank = int(fields[0])

            items += 1
            test = fields[1]
            osize = fields[4]
            stime = fields[5]
            etime = fields[6]

            mbps += float(fields[7])
            ops += float(fields[8])
            iops += float(fields[9])
            errs += int(fields[10])
            latency += float(fields[11])
            median += float(fields[12])

            # min/max latency
            n, x = fields[13].split('-')
            if float(n) < lmin:
                lmin = float(n)
            if float(x) > lmax:
                lmax = float(x)
            if debug & 8:
                print "min: %s max: %s" % (min, max)

            ldist_offset = 0
            if options.ldist:
                ldist_offset = 11
                for i in range(11):
                    lat_dist[i] = lat_dist[i] + int(fields[i + 14])

            percent = percent + float(fields[ldist_offset + 14])
            compress = fields[ldist_offset + 15]

            # only the first put test returns a utc at the end since the
            # other tests are run w/o --utc.  if not running with --utc
            # we don't even care!
            if options.utc:
                if test == 'put' and putcount == 1:
                    utcstamp = fields[ldist_offset + 16]
                else:
                    utcstamp = utc
            else:
                utcstamp = ''
    try:
        out = "%-5s  %4d  %4d  %5s" % \
            (test, numnodes, numnodes * procs, osize)
        out += "  %8s  %8s  %8.2f %6d %8.2f %4d %7.3f %7.3f %5.2f-%05.2f" % \
            (stime, etime, mbps, ops, iops, errs, latency / items,
             median / numnodes, lmin, lmax)
        if options.ldist:
            for i in range(11):
                out += " %5d" % lat_dist[i]
        out += "   %5.2f %4s %s" % (percent / items, compress, utcstamp)

        if options.csv:
            out = re.sub('\s+', ',', out)
            out = re.sub(',$', '', out)
        print out
    except UnboundLocalError, err:
        print "Error printing output:", err
        utcstamp = int(time.time())

    return((status, puts_per_proc, utcstamp))


def delcont(cname):

    errlog = '/tmp/swiftdel-%s.err' % cname
    command = 'swift delete %s 2>>%s' % (cname, errlog)

    # sometimes this can fail so wait a bit for eventual consistency to kick in
    time.sleep(10)
    for i in range(3):
        try:
            logexec('deleting container: %s' % command)
            results = subprocess.check_output(command, shell=True)
            os.remove(errlog)
            break
        except subprocess.CalledProcessError as err:
            print "Swift errors, retrying... see %s for details" % errlog
            time.sleep(10)
    logexec('container deleted')

if __name__ == "__main__":

    version = '0.0.7'
    copyright = 'Copyright 2013 Hewlett-Packard Development Company, L.P.'

    main(sys.argv[1:])

if debug & 8:
    resname = '/tmp/gpmulti-%d.log' % os.getpid()
    if debug & 1:
        print "Writing results to: %s" % resname

#    E x e c u t e    R e m o t e    C o m m a n d    o n    E a c h    N o d e

# build list of remote nodes
count_nodes = 0
remote_nodes = []
if not re.search(':', options.numnodes):
    skip = 0
    numnodes = int(options.numnodes)
else:
    skip, numnodes = options.numnodes.split(':')
    skip = int(skip)
    numnodes = int(numnodes)

if options.nodes:
    try:
        f = open(options.nodes, 'r')
    except:
        error("couldn't read '%s'" % file)
    for name in f:
        if re.match('#', name):
            continue
        count_nodes += 1
        if count_nodes <= skip:
            continue
        remote_nodes.append(name[:-1])
        if count_nodes == numnodes + skip:
            break
    f.close()
else:
    remote_nodes.append('localhost')

queue = Queue()

ssh_command = 'ssh -o StrictHostKeyChecking=no -o BatchMode=yes'
ssh_command += ' -o ServerAliveInterval=60'
if options.sshkey:
    ssh_command += ' -i %s' % options.sshkey
if options.username:
    ssh_command += ' -l %s' % options.username

for procs in procset:

    if not options.nohead:
        print_header()

    ppp = ''    # defined by 'put' test
    for size_index in range(len(sizeset)):
        size = sizeset[size_index]
        osize = cvtFromKMG(size)

        utc = ''
        putcount = 0
        for test in options.tests.split(','):

            if options.pretest:
                errlog = '/tmp/gpmulti-pretest-%s-%d.err' % (test, time.time())
                command = '%s %s 2>%s' % (options.pretest, test, errlog)
                if debug & 256:
                    print "Command:", command
                try:
                    logexec('started pretest: %s' % options.pretest)
                    results = subprocess.check_output(command, shell=True)
                    if results != '':
                        print results,
                    logexec('pretest finished')
                    os.remove(errlog)
                except subprocess.CalledProcessError as err:
                    queue.put("gpmulti error, see %s for details" % errlog)
                    error("gpmulti pretest error, see %s for details" % errlog)

            # count puts because if multiples we want to reuse the container!
            putcount += 1

            # make sure remote command sync times offset from same base time
            # BUT only after we drop caches
            root_command = \
                build_command(int(time.time()), test, size_index, procs,
                              utc, putcount)
            logexec('Command: %s' % root_command)

            jobs = []
            for rank in range(len(remote_nodes)):

                # if there's a 'p' test, use -n OR 99999 noting IT will return
                # the number of objects actually written. On the other hand if
                # there is no PUT test we need -n or 99999 anyways
                if test == 'p' or not re.search('p', options.tests):
                    if options.numobjs:
                        nobjects = options.numobjs
                    else:
                        nobjects = 999999
                else:
                    nobjects = ppp[rank]

                remote_command = "%s %s %s --nobjects %s" % \
                    (ssh_command, remote_nodes[rank], root_command, nobjects)
                remote_command += " --rank %d" % rank
                if debug & 2:
                    print "Command:", remote_command
                proc = Process(target=execute, args=(queue, remote_command))
                jobs.append(proc)
                proc.start()
                logexec('Started PID: %s' % proc.pid)

            for job in jobs:
                logexec('joined pid: %s' % job.pid)
                job.join()
            logexec('subprocesses completed')

            # only the put has a legitimate ppp list AND we want to reuse
            # its timestamp for non-p tests, noting -1 set if --warnexit
            # specified and we had one
            status, temp_ppp, timestamp = print_results(queue, putcount)
            logexec('results printed')
            if status == -1:
                logexec('abnormal exit!!!')
                sys.exit()

            if test == 'p':
                ppp = temp_ppp
                utc = timestamp
            if not status:
                print "couldn't report results"
                print "Test: %s  Procs: %s  Size: %s" % (test, procs, osize)

            # stolen from getput, noting we always use --utc
            if test == 'd' and not options.cont_nodelete:
                cname = options.cname
                if options.utc:
                    cname = '%s-%s' % (cname, utc)
                if options.ctype == 'bynode':
                    cname += "-%s" % options.rank
                if debug & 1:
                    print 'deleting container(s): %s' % cname

                if options.ctype != 'byproc':
                    delcont(cname)
                else:
                    for proc in range(procs):
                        name = '%s-%s-%d' % (cname, options.rank, proc)
                        delcont(name)

logexec('exiting cleanly')
