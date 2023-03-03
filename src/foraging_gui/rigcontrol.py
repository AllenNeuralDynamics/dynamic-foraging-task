import queue
from enum import Enum
from pyOSC3.OSC3 import OSCMessage

class RigClient:
    def __init__(self, client):
        self.client = client
        self.client.addMsgHandler("default", self.msg_handler)
        self.msgs = queue.Queue(maxsize=0)

    def msg_handler(self, address, *args):
        msg = OSCMessage(address, args)
        self.msgs.put(msg)
        print(msg)

    def send(self, address="", *args):
        message = OSCMessage(address, *args)
        return self.client.sendOSC(message)

    def receive(self):
        return self.msgs.get(block=True)
        #return self.msgs.get(block=False)
        #return self.msgs.get(block=True, timeout=None)
    
    def receive2(self):
        return self.msgs.get(block=False)
    
    def Left_Bait(self, value):
        self.send("/Left_Bait", value)
    
    def Right_Bait(self, value):
        self.send("/Right_Bait", value)

    def start(self, value):
        self.send("/start", value)

    def ITI(self, value):
        self.send("/ITI", value)

    def DelayTime(self, value):
        self.send("/DelayTime", value)

    def ResponseTime(self, value):
        self.send("/ResponseTime", value)
    
    # waveform 1, location 1
    def WaveForm1_1(self, value):
        self.send("/WaveForm1_1", value)
    
    # waveform 2, location 1
    def WaveForm2_1(self, value):
        self.send("/WaveForm2_1", value)

    # waveform 1, location 2
    def WaveForm1_2(self, value):
        self.send("/WaveForm1_2", value)

    # waveform 2, location 2
    def WaveForm2_2(self, value):
        self.send("/WaveForm2_2", value)