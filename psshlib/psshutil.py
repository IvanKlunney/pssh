# Copyright (c) 2009-2012, Andrew McNabb
# Copyright (c) 2003-2008, Brent N. Chun

import fcntl
import string
import sys
import re

HOST_FORMAT_FILE = 'Host format is [user@]host[:port] [user]'
HOST_FORMAT_STRING  = 'Host format is [user@]host[[start:stop]][:port] [user]'
HOST_PATTERN = r'(.*)\[(.+)\](.*)'

def read_host_files(paths, default_user=None, default_port=None):
    """Reads the given host files.

    Returns a list of (host, port, user) triples.
    """
    hosts = []
    if paths:
        for path in paths:
            hosts.extend(read_host_file(path, default_user=default_user))
    return hosts

def read_host_file(path, default_user=None, default_port=None):
    """Reads the given host file.

    Lines are of the form: host[:port] [login].
    Returns a list of (host, port, user) triples.
    """
    lines = []
    f = open(path)
    for line in f:
        lines.append(line.strip())
    f.close()

    hosts = []
    for line in lines:
        # Skip blank lines or lines starting with #
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        host, port, user = parse_host_entry(line, default_user, default_port)
        if host:
            hosts.append((host, port, user))
    return hosts

# TODO: deprecate the second host field and standardize on the
# [user@]host[:port] format.
def parse_host_entry(line, default_user, default_port):
    """Parses a single host entry.

    This may take either the of the form [user@]host[[start:stop]][:port] or
    host[[start:stop]][:port][ user].

    Returns a (host, port, user) triple.
    """
    fields = line.split()
    if len(fields) > 2:
        sys.stderr.write('Bad line: "%s". Format should be'
                ' [user@]host[[start:stop]][:port] [user]\n' % line)
        return None, None, None
    host_field = fields[0]
    host, port, user = parse_host(host_field, default_port=default_port)
    if len(fields) == 2:
        if user is None:
            user = fields[1]
        else:
            sys.stderr.write('User specified twice in line: "%s"\n' % line)
            return None, None, None
    if user is None:
        user = default_user
    return host, port, user

def parse_host_string(host_string, default_user=None, default_port=None):
    """Parses a whitespace-delimited string of "[user@]host[[start:stop]][:port]" entries.

    Returns a list of (host, port, user) triples.
    """
    hosts = []
    entries = host_string.split()

    for index_entry in entries:
        is_match = re.search(HOST_PATTERN, index_entry)
        if is_match:
            prefix, range_idx, suffix = is_match.groups()
            left, right = range_idx.split(':')
            if left and right:
                left_int     = int(left)
                right_int    = int(right)
                width	     = 0
                if left.find('0') == 0 or right.find('0') == 0:
                    width = max(len(left), len(right))
                if left_int >= right_int:
                    sys.stderr.write("Index range [%s:%s] is not valid\n" % (left, right))
                    return None, None, None
                elif len(right) - len(left) != 0 and width > 0:
                    sys.stderr.write("Leading zeros is non-deterministic\n")
                    return None, None, None
                while left_int <= right_int:
                    host_idx = left_int
                    if width and len(str(left_int)) <= len(str(right_int)):
                    	# Padding
                        current    = str(left_int)
                        host_idx   = current.zfill(len(current) + (width - len(current)))
                    hosts.append(parse_host("{}{}{}".format(prefix, host_idx, suffix), default_user, default_port))
                    left_int += 1

    for entry in entries:
        is_match = re.search(HOST_PATTERN, entry)
        if not is_match:
	       hosts.append(parse_host(entry, default_user, default_port))
    return hosts

def parse_host(host, default_user=None, default_port=None):
    """Parses host entries of the form "[user@]host[[start:stop]][:port]".

    Returns a (host, port, user) triple.
    """
    user = default_user
    port = default_port
    if '@' in host:
        user, host = host.split('@', 1)
    if ':' in host:
        host, port = host.rsplit(':', 1)
    return (host, port, user)

def set_cloexec(filelike):
    """Sets the underlying filedescriptor to automatically close on exec.

    If set_cloexec is called for all open files, then subprocess.Popen does
    not require the close_fds option.
    """
    fcntl.fcntl(filelike.fileno(), fcntl.FD_CLOEXEC, 1)
