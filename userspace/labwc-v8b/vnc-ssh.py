"""Expose one local RFB connection over pinned SSH stdio, never over LAN."""
import argparse
from pathlib import Path
import socket
import subprocess
import threading


def relay(peer, command):
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          bufsize=0) as ssh:
        def to_phone():
            try:
                while data := peer.recv(65536):
                    view = memoryview(data)
                    while view:
                        written = ssh.stdin.write(view)
                        if not written:
                            return
                        view = view[written:]
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                ssh.stdin.close()

        sender = threading.Thread(target=to_phone, daemon=True)
        sender.start()
        try:
            while data := ssh.stdout.read(65536):
                peer.sendall(data)
        finally:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            if ssh.poll() is None:
                ssh.terminate()
            sender.join(timeout=2)
    return ssh.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--known-hosts", required=True, type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--gnome-rdp", action="store_true", help="Use the isolated GNOME RDP stream")
    args = parser.parse_args()
    if args.port is None:
        args.port = 13389 if args.gnome_rdp else 5905
    if not args.identity.is_file() or not args.known_hosts.is_file():
        parser.error("A local SSH identity and COM-verified known_hosts are required")
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port between 1024 and 65535")
    cmd = [
        "ssh.exe", "-T", "-b", "192.168.77.1", "-i", str(args.identity.resolve()),
        "-oBatchMode=yes", "-oIdentitiesOnly=yes", "-oStrictHostKeyChecking=yes",
        "-oUserKnownHostsFile=" + str(args.known_hosts.resolve()),
        "-oKexAlgorithms=curve25519-sha256", "-oConnectTimeout=5",
        "-oServerAliveInterval=5", "-oServerAliveCountMax=2", "root@192.168.77.2",
        "/bin/sh /tmp/lemon-gnome50/rdp-stream.sh" if args.gnome_rdp
        else "/bin/sh /tmp/lemon-labwc-v8b/runtime/session.sh stream",
    ]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port))
        listener.listen(1)
        if args.gnome_rdp:
            print(f"Connect Remote Desktop to 127.0.0.1:{args.port}. One local connection.", flush=True)
        else:
            print(f"Connect the VNC viewer to 127.0.0.1::{args.port}. One local connection.", flush=True)
        peer, _ = listener.accept()
        # Do not leave a listening socket after accepting the intended connection.
        listener.close()
        with peer:
            return relay(peer, cmd)


if __name__ == "__main__":
    raise SystemExit(main())
