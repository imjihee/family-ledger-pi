import socket
import unittest
from unittest.mock import patch
import telegram_http
class TelegramHttpTests(unittest.TestCase):
 def test_ipv4_first_and_restore(self):
  original=socket.getaddrinfo; values=[(socket.AF_INET6,socket.SOCK_STREAM,6,"",("::1",443,0,0)),(socket.AF_INET,socket.SOCK_STREAM,6,"",("127.0.0.1",443))]
  with patch("telegram_http.socket.getaddrinfo",return_value=values):
   with telegram_http.ipv4_first(): self.assertEqual(socket.getaddrinfo("example",443)[0][0],socket.AF_INET)
  self.assertIs(socket.getaddrinfo,original)
