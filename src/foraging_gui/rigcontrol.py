import time
import queue
import logging

from pyOSC3.OSC3 import OSCMessage


class RigClient:
    def __init__(self, client):
        self.client = client
        self.client.addMsgHandler("default", self.msg_handler)
        self.msgs = queue.Queue(maxsize=0)
        self.last_message_time = time.time()

        # Keep track photometry message history
        self.photometry_messages = {}
        self.photometry_message_tolerance = 2

    def track_photometry_messages(self, message):
        """
        Keep track of when we last displayed each type of photometry signal
        """
        if message in self.photometry_messages:
            # We have seen this message before, check for tolerance
            now = time.time()
            if (
                now - self.photometry_messages[message]
            ) < self.photometry_message_tolerance:
                # It has been less than tolerance, return False and do not display message
                return False
            else:
                # It has been greater than tolerance, record new time, and display message
                self.photometry_messages[message] = time.time()
                return True
        else:
            # We have not seen this message before, enter time, and display message
            self.photometry_messages[message] = time.time()
            return True

    def msg_handler(self, address, *args):
        msg = OSCMessage(address, args)
        CurrentMessage = [
            msg.address,
            args[1][0],
            msg.values()[2],
            msg.values()[3],
        ]
        self.msgs.put([msg, args])
        msg_str = str(CurrentMessage)
        self.last_message_time = time.time()

        # Selectively log photometry messages
        if ("PhotometryRising" in msg_str) or ("PhotometryFalling" in msg_str):
            # Only selectively log these two messages

            if self.track_photometry_messages(msg.address):
                # It was has been more than self.photometry_message_tolerance for this message
                print(
                    msg_str
                    + ", displaying at {} Hz".format(
                        1 / self.photometry_message_tolerance
                    )
                )
                logging.info(
                    msg_str
                    + ", displaying at {} Hz".format(
                        1 / self.photometry_message_tolerance
                    )
                )
        else:
            # Print and add to log
            print(CurrentMessage)
            logging.info(CurrentMessage)

    def send(self, address="", *args):
        message = OSCMessage(address, *args)
        return self.client.sendOSC(message)

    def receive(self):
        return self.msgs.get(block=True)

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

    def RewardDelay(self, value):
        self.send("/RewardDelay", value)

    def DelayTime(self, value):
        self.send("/DelayTime", value)

    def ResponseTime(self, value):
        self.send("/ResponseTime", value)

    def TriggerITIStart_Wave1(self, value):
        self.send("/TriggerITIStart_Wave1", value)

    def TriggerITIStart_Wave2(self, value):
        self.send("/TriggerITIStart_Wave2", value)

    def Trigger_Location1(self, value):  # location 1
        self.send("/Trigger_Location1", value)

    def Trigger_Location2(self, value):  # location 2
        self.send("/Trigger_Location2", value)

    def TriggerGoCue_Wave1(self, value):  # location 1
        self.send("/TriggerGoCue_Wave1", value)

    def TriggerGoCue_Wave2(self, value):  # location 2
        self.send("/TriggerGoCue_Wave2", value)

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

    def LeftValue(self, value):
        self.send("/LeftValueSize", value)

    def RightValue(self, value):
        self.send("/RightValueSize", value)

    def LeftValue1(self, value):
        self.send("/LeftValueSize1", value)

    def RightValue1(self, value):
        self.send("/RightValueSize1", value)

    def RewardConsumeTime(self, value):
        self.send("/RewardConsumeTime", value)

    def ManualWater_Left(self, value):
        self.send("/ManualWater_Left", value)

    def ManualWater_Right(self, value):
        self.send("/ManualWater_Right", value)

    def AutoWater_Left(self, value):
        self.send("/AutoWater_Left", value)

    def AutoWater_Right(self, value):
        self.send("/AutoWater_Right", value)

    def Location1_Size(self, value):
        self.send("/Location1Size", value)

    def Location2_Size(self, value):
        self.send("/Location2Size", value)

    def TriggerSource(self, value):
        self.send("/TriggerSource", value)

    def OptogeneticsCalibration(self, value):
        self.send("/OptogeneticsCalibration", value)

    def CameraControl(self, value):
        self.send("/cameracontrol", value)

    def CameraFrequency(self, value):
        self.send("/camerafrequency", value)

    def SideCameraFile(self, value):
        # save file name of the SideCamera
        self.send("/sidecamerafile", value)

    def BottomCameraFile(self, value):
        # save file name of the BottomCamera
        self.send("/bottomcamerafile", value)

    def SideCameraCSV(self, value):
        # save file name of the SideCamera csv
        self.send("/sidecameracsv", value)

    def BottomCameraCSV(self, value):
        # save file name of the BottomCamera csv
        self.send("/bottomcameracsv", value)

    def StopLogging(self, value):
        # stop the logging
        self.send("/stoplogging", value)

    def StartLogging(self, value):
        # start the logging
        self.send("/startlogging", value)

    def DO0(self, value):
        # open DO0
        self.send("/DO0", value)

    def DO1(self, value):
        # open DO1
        self.send("/DO1", value)

    def DO2(self, value):
        # open DO2
        self.send("/DO2", value)

    def DO3(self, value):
        # open DO3
        self.send("/DO3", value)

    def Port2(self, value):
        # open Port2
        self.send("/Port2", value)

    def PassITI(self, value):
        # Trigger waveform after ITI for optogenetics
        self.send("/PassITI", value)

    def PassGoCue(self, value):
        # Trigger waveform after Go cue for optogenetics
        self.send("/PassGoCue", value)

    def PassRewardOutcome(self, value):
        # Trigger waveform after Rewardoutcome for optogenetics
        self.send("/PassRewardOutcome", value)

    def CameraStartType(self, value):
        # 1, start recording; 2, start preview
        self.send("/camerastarttype", value)

    def StopCameraPreview(self, value):
        # stop the camera preview workflow
        self.send("/stopcamerapreview", value)
