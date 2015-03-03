#!/usr/bin/python

'''A tool for modifying ini-format files from the contents of environment
variables.'''

import os
import sys
import argparse
from iniparse import ConfigParser
import re
import tempfile
import logging
import errno

LOG = logging.getLogger('iniconfigurator')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--replace', '-r',
                   action='store_true')
    p.add_argument('--keyprefix', '-k')

    g = p.add_argument_group('Logging options')
    g.add_argument('--verbose', '-v',
                   action='store_const',
                   const='INFO',
                   dest='loglevel')
    g.add_argument('--debug', '-d',
                   action='store_const',
                   const='DEBUG',
                   dest='loglevel')
    p.add_argument('target')

    p.set_defaults(loglevel='WARN')

    return p.parse_args()


def apply(cfg, environ, prefix):
    '''Applying configuraiton changes described by `prefix`-prefixed
    keys in `environ` to `cfg`.'''

    for k, v in environ.items():
        if k.startswith(prefix):
            LOG.debug('considering: %s', k)
            _, section, option = k.split('__')
            if not cfg.has_section(section) and section != 'DEFAULT':
                cfg.add_section(section)
            if not cfg.has_option(section, option):
                oldv = '<unset>'
            else:
                oldv = cfg.get(section, option)

            cfg.set(section, option, v)
            LOG.info('set %s/%s = %s [was: %s]',
                     section,
                     option,
                     v,
                     oldv)
        elif k.startswith('delete__%s' % prefix):
            LOG.debug('considering: %s', k)
            try:
                action, _, section, option = k.split('__')
            except ValueError:
                action, _, section, = k.split('__')
                option = None

            if option is not None:
                if cfg.has_option(section, option):
                    cfg.remove_option(section, option)
                    LOG.info('delete option %s/%s',
                             section,
                             option)
            else:
                if cfg.has_section(section):
                    cfg.remove_section(section)
                    LOG.info('delete section %s',
                             section)



def read_config(src):
    cfg = ConfigParser()

    try:
        with open(src) as fp:
            LOG.info('reading configuration from %s', src)
            cfg.readfp(fp)
    except IOError as err:
        if err.errno != errno.ENOENT:
            raise

    return cfg


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)

    if not args.keyprefix:
        args.keyprefix = os.path.basename(args.target)
        args.keyprefix = re.sub('[^\w]', '_', args.keyprefix)

    cfg = read_config(args.target)
    apply(cfg, os.environ, args.keyprefix)

    if args.replace:
        LOG.warn('replacing %s', args.target)
        with tempfile.NamedTemporaryFile(dir=os.path.dirname(args.target),
                                         prefix='iniconfigXXXXXX') as fd:
            cfg.write(fd)
            try:
                os.unlink(args.target)
            except OSError as err:
                if err.errno != errno.ENOENT:
                    raise
            os.link(fd.name, args.target)
    else:
        cfg.write(sys.stdout)


if __name__ == '__main__':
    main()
