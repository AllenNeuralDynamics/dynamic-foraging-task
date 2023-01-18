import sys
import time

#sys.path.append('E:\BonsaiBehavior-master\BonsaiBehavior-master\DynamicForaging_v4')
import rigcontrol
from datetime import datetime
from pyOSC3.OSC3 import OSCStreamingClient


def default_handler(address, *args):
    print(f"DEFAULT {address}: {args}")

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

rig.Left_Bait(0)
rig.Right_Bait(0)
rig.ITI(1.0)
rig.DelayTime(1.0)
rig.ResponseTime(2.0)
rig.start(1)

a=rig.receive()
b=rig.receive()
e=rig2.receive()
f=rig2.receive()
print(a)

if a[1]=='ErrorRight':
    print(1)
client.close()
client2.close()

