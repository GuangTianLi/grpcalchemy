import socket
import unittest

from grpcalchemy.utils import socket_bind_test, select_address_family, get_sockaddr


class UtilsTestCase(unittest.TestCase):
    def test_socket_bind_test(self):
        host = "0.0.0.0"
        port = 50051
        address_family = select_address_family(host)
        server_address = get_sockaddr(host, port, address_family)
        with socket.socket(address_family, socket.SOCK_STREAM) as s:
            s.bind(server_address)
            with self.assertRaises(OSError):
                socket_bind_test(host, port)


if __name__ == "__main__":
    unittest.main()
