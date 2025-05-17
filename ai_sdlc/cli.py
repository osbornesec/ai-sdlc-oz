#!/usr/bin/env python
import sys

def main() -> None:
    cmd, *args = sys.argv[1:] or ["--help"]
    if cmd == "init":
        from .commands.init import run_init
        run_init()
    elif cmd == "new":
        from .commands.new import run_new
        run_new(args)
    elif cmd == "next":
        from .commands.next import run_next
        run_next()
    elif cmd == "done":
        from .commands.done import run_done
        run_done()
    else:
        print("Usage: aisdlc [init|new|next|done]")
