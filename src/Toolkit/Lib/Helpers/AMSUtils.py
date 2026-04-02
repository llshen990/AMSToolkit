import os

class AMSUtils(object):
    def __init__(self):
        pass

    @staticmethod
    def check_tcp_port(host, port, timeout=30):
        import socket
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            if result == 0:
                return True
            else:
                return False
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass