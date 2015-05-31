# -*- coding: utf-8 -*-

def main():
    from .app import Botch

    app = Botch()
    return app.run()

if __name__ == "__main__":
    import sys

    retval = main()
    sys.exit(retval)
