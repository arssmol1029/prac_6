import unittest
import fun_2
import fun_3
import time
import multiprocessing
import socket


class TestSqrootsServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = multiprocessing.Process(target=fun_2.main)
        cls.server.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()

    def setUp(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(("localhost", 1337))

    def tearDown(self):
        self.client.close()

    def test_sqroots_server(self):
        self.client.sendall("{}\n")
        self.assertEqual(self.client.recv(128), b"\n")
