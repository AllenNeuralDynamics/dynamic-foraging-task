from pyOSC3.OSC3 import OSCStreamingClient
from rigcontrol import RigClient

ip = "127.0.0.1"
request_port = 4002
client = OSCStreamingClient()  # Create client 
client.connect((ip, request_port))

channel = RigClient(client)

channel.receive2()


