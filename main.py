import builtins
import smashladder_qt
import sys
import time


def main():
    if 'debug' in sys.argv:
        builtins.debug_smashladder = True
    else:
        builtins.debug_smashladder = False

    sys.exit(smashladder_qt.app.exec_())


if __name__ == '__main__':
    main()
