#!/usr/bin/env python3

def main():
    from src.server import Server
    from src.handler import Handler

    scene_host = Server(8233, Handler)
    scene_host.run()

if __name__ == '__main__':
    main()