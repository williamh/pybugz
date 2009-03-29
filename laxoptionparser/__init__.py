#!/usr/bin/env python

import locale

from optparse import BadOptionError, OptionParser

#
# LaxOptionParser will silently ignore options that it does not
# recognise, as opposed to OptionParser which will throw an
# exception.
#

class LaxOptionParser(OptionParser):
    def _match_long_opt(self, opt):
        try:
            return OptionParser._match_long_opt(self, opt)
        except BadOptionError, e:
            raise KeyError

    def _process_short_opts(self, rargs, values):
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1                      # we have consumed a character

            if not option:
                raise KeyError
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(rargs) < nargs:
                    if nargs == 1:
                        self.error("%s option requires an argument" % opt)
                    else:
                        self.error("%s option requires %d arguments"
                                   % (opt, nargs))
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:                       # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break

    def _process_args(self, largs, rargs, values):
        while rargs:
            arg = rargs[0]
            if arg == '--':
                del rargs[0]
                return
            elif arg[0:2] == '--':
                try:
                    self._process_long_opt(rargs, values)
                except KeyError, e:
                    if '=' in arg:
                        rargs.pop(0)
                    largs.append(arg) # popped from rarg in _process_long_opt
            elif arg[:1] == '-' and len(arg) > 1:
                try:
                    self._process_short_opts(rargs, values)
                except KeyError, e:
                    largs.append(arg) # popped from rarg in _process_short_opt
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return
