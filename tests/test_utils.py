import os.path
import socket
import unittest
from shutil import rmtree

from grpcalchemy.utils import (
    socket_bind_test,
    select_address_family,
    get_sockaddr,
    generate_proto_file,
)


class UtilsTestCase(unittest.TestCase):
    def test_socket_bind_test(self):
        unix_socket = "0.0.0.0:50051"
        for host in ["0.0.0.0", "::", f"unix://{unix_socket}"]:
            port = 50051
            address_family = select_address_family(host)
            server_address = get_sockaddr(host, port, address_family)
            with self.subTest(f"host: {host}"):
                with socket.socket(address_family, socket.SOCK_STREAM) as s:
                    s.bind(server_address)
                    with self.assertRaises(OSError):
                        socket_bind_test(host, port)
        if os.path.exists(unix_socket):
            os.remove(unix_socket)

    def test_generate_proto_file(self):
        dir_name = "protos"
        if os.path.exists(dir_name):
            rmtree(dir_name)
        generate_proto_file(dir_name)
        self.assertTrue(os.path.exists(dir_name))
        self.assertTrue(os.path.exists(os.path.join(dir_name, "__init__.py")))
        self.assertTrue(os.path.exists(os.path.join(dir_name, "README.md")))
        rmtree(dir_name)


if __name__ == "__main__":
    unittest.main()
