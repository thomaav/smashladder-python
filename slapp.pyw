#!/usr/bin/env python3

import builtins
import smashladder.slqt as slqt
import sys
import time


def main():
    if 'debug' in sys.argv:
        builtins.debug_smashladder = True
    else:
        builtins.debug_smashladder = False

    sys.exit(slqt.app.exec_())


if __name__ == '__main__':
    main()
