# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Camera.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Camera(object):
    def setupUi(self, Camera):
        Camera.setObjectName("Camera")
        Camera.resize(261, 448)
        self.label_6 = QtWidgets.QLabel(Camera)
        self.label_6.setGeometry(QtCore.QRect(23, 260, 91, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy)
        self.label_6.setTextFormat(QtCore.Qt.AutoText)
        self.label_6.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_6.setObjectName("label_6")
        self.StartCamera = QtWidgets.QPushButton(Camera)
        self.StartCamera.setGeometry(QtCore.QRect(120, 50, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.StartCamera.sizePolicy().hasHeightForWidth())
        self.StartCamera.setSizePolicy(sizePolicy)
        self.StartCamera.setCheckable(True)
        self.StartCamera.setObjectName("StartCamera")
        self.label_7 = QtWidgets.QLabel(Camera)
        self.label_7.setGeometry(QtCore.QRect(23, 120, 91, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)
        self.label_7.setTextFormat(QtCore.Qt.AutoText)
        self.label_7.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_7.setObjectName("label_7")
        self.AutoControl = QtWidgets.QComboBox(Camera)
        self.AutoControl.setGeometry(QtCore.QRect(120, 120, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AutoControl.sizePolicy().hasHeightForWidth())
        self.AutoControl.setSizePolicy(sizePolicy)
        self.AutoControl.setObjectName("AutoControl")
        self.AutoControl.addItem("")
        self.AutoControl.addItem("")
        self.label_8 = QtWidgets.QLabel(Camera)
        self.label_8.setGeometry(QtCore.QRect(23, 84, 91, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy)
        self.label_8.setTextFormat(QtCore.Qt.AutoText)
        self.label_8.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_8.setObjectName("label_8")
        self.CollectVideo = QtWidgets.QComboBox(Camera)
        self.CollectVideo.setGeometry(QtCore.QRect(120, 84, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.CollectVideo.sizePolicy().hasHeightForWidth())
        self.CollectVideo.setSizePolicy(sizePolicy)
        self.CollectVideo.setFrame(True)
        self.CollectVideo.setObjectName("CollectVideo")
        self.CollectVideo.addItem("")
        self.CollectVideo.addItem("")
        self.FrameRate = QtWidgets.QSpinBox(Camera)
        self.FrameRate.setGeometry(QtCore.QRect(120, 260, 81, 22))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.FrameRate.sizePolicy().hasHeightForWidth())
        self.FrameRate.setSizePolicy(sizePolicy)
        self.FrameRate.setMaximum(100000)
        self.FrameRate.setSingleStep(5)
        self.FrameRate.setProperty("value", 500)
        self.FrameRate.setDisplayIntegerBase(10)
        self.FrameRate.setObjectName("FrameRate")
        self.WarningLabelFileIsInUse = QtWidgets.QLabel(Camera)
        self.WarningLabelFileIsInUse.setGeometry(QtCore.QRect(50, 360, 171, 51))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.WarningLabelFileIsInUse.sizePolicy().hasHeightForWidth())
        self.WarningLabelFileIsInUse.setSizePolicy(sizePolicy)
        self.WarningLabelFileIsInUse.setText("")
        self.WarningLabelFileIsInUse.setTextFormat(QtCore.Qt.AutoText)
        self.WarningLabelFileIsInUse.setScaledContents(False)
        self.WarningLabelFileIsInUse.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.WarningLabelFileIsInUse.setObjectName("WarningLabelFileIsInUse")
        self.ClearTemporaryVideo = QtWidgets.QPushButton(Camera)
        self.ClearTemporaryVideo.setGeometry(QtCore.QRect(120, 156, 81, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ClearTemporaryVideo.sizePolicy().hasHeightForWidth())
        self.ClearTemporaryVideo.setSizePolicy(sizePolicy)
        self.ClearTemporaryVideo.setCheckable(False)
        self.ClearTemporaryVideo.setObjectName("ClearTemporaryVideo")
        self.WarningLabelCameraOn = QtWidgets.QLabel(Camera)
        self.WarningLabelCameraOn.setGeometry(QtCore.QRect(50, 370, 171, 51))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.WarningLabelCameraOn.sizePolicy().hasHeightForWidth())
        self.WarningLabelCameraOn.setSizePolicy(sizePolicy)
        self.WarningLabelCameraOn.setText("")
        self.WarningLabelCameraOn.setTextFormat(QtCore.Qt.AutoText)
        self.WarningLabelCameraOn.setScaledContents(False)
        self.WarningLabelCameraOn.setAlignment(QtCore.Qt.AlignCenter)
        self.WarningLabelCameraOn.setObjectName("WarningLabelCameraOn")
        self.OpenSaveFolder = QtWidgets.QPushButton(Camera)
        self.OpenSaveFolder.setGeometry(QtCore.QRect(120, 190, 81, 21))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.OpenSaveFolder.sizePolicy().hasHeightForWidth())
        self.OpenSaveFolder.setSizePolicy(sizePolicy)
        self.OpenSaveFolder.setCheckable(False)
        self.OpenSaveFolder.setObjectName("OpenSaveFolder")
        self.RestartLogging = QtWidgets.QPushButton(Camera)
        self.RestartLogging.setGeometry(QtCore.QRect(120, 225, 81, 21))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.RestartLogging.sizePolicy().hasHeightForWidth())
        self.RestartLogging.setSizePolicy(sizePolicy)
        self.RestartLogging.setCheckable(False)
        self.RestartLogging.setObjectName("RestartLogging")
        self.WarningLabelLogging = QtWidgets.QLabel(Camera)
        self.WarningLabelLogging.setGeometry(QtCore.QRect(50, 320, 171, 51))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.WarningLabelLogging.sizePolicy().hasHeightForWidth())
        self.WarningLabelLogging.setSizePolicy(sizePolicy)
        self.WarningLabelLogging.setText("")
        self.WarningLabelLogging.setTextFormat(QtCore.Qt.AutoText)
        self.WarningLabelLogging.setScaledContents(False)
        self.WarningLabelLogging.setAlignment(QtCore.Qt.AlignCenter)
        self.WarningLabelLogging.setObjectName("WarningLabelLogging")
        self.WarningLabelOpenSave = QtWidgets.QLabel(Camera)
        self.WarningLabelOpenSave.setGeometry(QtCore.QRect(50, 330, 171, 51))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.WarningLabelOpenSave.sizePolicy().hasHeightForWidth())
        self.WarningLabelOpenSave.setSizePolicy(sizePolicy)
        self.WarningLabelOpenSave.setText("")
        self.WarningLabelOpenSave.setTextFormat(QtCore.Qt.AutoText)
        self.WarningLabelOpenSave.setScaledContents(False)
        self.WarningLabelOpenSave.setAlignment(QtCore.Qt.AlignCenter)
        self.WarningLabelOpenSave.setObjectName("WarningLabelOpenSave")

        self.retranslateUi(Camera)
        self.AutoControl.setCurrentIndex(1)
        self.CollectVideo.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(Camera)

    def retranslateUi(self, Camera):
        _translate = QtCore.QCoreApplication.translate
        Camera.setWindowTitle(_translate("Camera", "Camera"))
        self.label_6.setText(_translate("Camera", "frame rate="))
        self.StartCamera.setText(_translate("Camera", "Start"))
        self.label_7.setText(_translate("Camera", "auto control="))
        self.AutoControl.setItemText(0, _translate("Camera", "Yes"))
        self.AutoControl.setItemText(1, _translate("Camera", "No"))
        self.label_8.setText(_translate("Camera", "collect video="))
        self.CollectVideo.setItemText(0, _translate("Camera", "Yes"))
        self.CollectVideo.setItemText(1, _translate("Camera", "No"))
        self.ClearTemporaryVideo.setText(_translate("Camera", "Clear tem file"))
        self.OpenSaveFolder.setText(_translate("Camera", "Open save"))
        self.RestartLogging.setText(_translate("Camera", "Restart log"))
