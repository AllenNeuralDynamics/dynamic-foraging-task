import rigcontrol
from pyOSC3.OSC3 import OSCStreamingClient, OSCMessage


ip = "127.0.0.1"
request_port = 4002
client = OSCStreamingClient()  # Create client
client.connect((ip, request_port))
rig = rigcontrol.RigClient(client)

ip = "127.0.0.1"
request_port = 4003
client2 = OSCStreamingClient()  # Create client
client2.connect((ip, request_port))
rig2 = rigcontrol.RigClient(client2)
print("Starting....")

rig.Right_Bait(0)
rig.ITI(1.0)
rig.DelayTime(1.0)
rig.ResponseTime(2.0)
rig.start(1)


rig.client.sendOSC(OSCMessage("/StartTest", "StartPlease"))

a = rig.receive()
b = rig.receive()
e = rig2.receive()
f = rig2.receive()

if a[1] == 0:
    rig.client.sendOSC(OSCMessage("/EndTest", "EndPlease"))

client.close()
client2.close()
