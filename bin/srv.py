#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio

@asyncio.coroutine
def main(app):
    from vexmpp.utils import resolveHostPort

    for client, port in ((True, 5222), (False, 5269)):
        print()
        srv_records = []
        result = yield from resolveHostPort(app.args.hostname, port,
                                            app.event_loop, use_cache=False,
                                            client_srv=client,
                                            srv_records=srv_records)
        print("SRV records:\n" if srv_records else "", end="")
        for rec in srv_records:
            print("   -\t{0.host}:{0.port} "
                  "priority={0.priority} weight={0.weight}"
                  .format(rec))
        print("XMPP {}: {}".format("client" if client else "server", result))

    return 0

if __name__ == "__main__":
    import sys
    import vexmpp.application

    app = vexmpp.application.Application(main)
    app.arg_parser.add_argument("hostname")
    sys.exit(app.run())
