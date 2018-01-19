#!/usr/bin/env python3

import sys
import os

os.chdir(os.path.dirname(os.path.realpath(__file__)))

import builtins
import smashladder.slqt as slqt
import time


def main():
    if 'debug' in sys.argv:
        builtins.debug_smashladder = True
    else:
        builtins.debug_smashladder = False

    sys.exit(slqt.app.exec_())


if __name__ == '__main__':
    main()
