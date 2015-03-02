#!/usr/bin/python

import os
import sys
import argparse
import iniparse
import re
import tempfile
import logging

LOG = logging.getLogger('iniconfigurator')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--replace', '-r',
                   action='store_true')
    p.add_argument('--ignore-failed-delete', '-i',
                   action='store_true')
    p.add_argument('--keyprefix', '-k')
    p.add_argument('--verbose', '-v',
                   action='store_const',
                   const='INFO',
                   dest='loglevel')
    p.add_argument('--debug', '-d',
                   action='store_const',
                   const='DEBUG',
                   dest='loglevel')
    p.add_argument('target')
    
    p.set_defaults(loglevel='WARN')

    return p.parse_args()


def apply(cfg, environ, prefix,
          ignore_failed_delete=False):
    for k, v in environ.items():
        if not k.startswith(prefix):
            continue

        try:
            _, section, option = k.split('__')
            try:
                oldv = cfg[section][option]
                if isinstance(oldv,iniparse.config.Undefined):
                    raise KeyError('%s/%s' % (section, option))
            except KeyError:
                oldv = '<unset>'

            cfg[section][option] = v
            LOG.info('set %s/%s = %s [was: %s]',
                     section,
                     option,
                     v,
                     oldv)
        except ValueError:
            _, section, option, action = k.split('__')
            if action == 'delete':
                try:
                    del cfg[section][option]
                    LOG.info('delete %s/%s',
                             section,
                             option)
                except KeyError:
                    if not ignore_failed_delete:
                        raise KeyError('%s/%s' % (
                            section,
                            option))
                    LOG.debug('delete %s/%s failed (ignored)',
                              section,
                              option)


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)

    if not args.keyprefix:
        args.keyprefix = os.path.basename(args.target)
        args.keyprefix = re.sub('[^\w]', '_', args.keyprefix)

    with open(args.target) as fp:
        cfg = iniparse.INIConfig(fp=fp)

    apply(cfg, os.environ, args.keyprefix,
          ignore_failed_delete=args.ignore_failed_delete)

    if args.replace:
        LOG.warn('replacing %s', args.target)
        with tempfile.NamedTemporaryFile(dir=os.path.dirname(args.target),
                                         prefix='iniconfigXXXXXX') as fd:
            fd.write(str(cfg))
            os.unlink(args.target)
            os.link(fd.name, args.target)
    else:
        sys.stdout.write(str(cfg))


if __name__ == '__main__':
    main()
