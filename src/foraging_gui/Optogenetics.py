# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Optogenetics.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Optogenetics(object):
    def setupUi(self, Optogenetics):
        Optogenetics.setObjectName("Optogenetics")
        Optogenetics.resize(1269, 299)
        self.label = QtWidgets.QLabel(Optogenetics)
        self.label.setGeometry(QtCore.QRect(10, 32, 31, 16))
        self.label.setObjectName("label")
        self.Laser_1 = QtWidgets.QComboBox(Optogenetics)
        self.Laser_1.setGeometry(QtCore.QRect(50, 30, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Laser_1.sizePolicy().hasHeightForWidth())
        self.Laser_1.setSizePolicy(sizePolicy)
        self.Laser_1.setObjectName("Laser_1")
        self.Laser_1.addItem("")
        self.Laser_1.addItem("")
        self.Laser_1.addItem("")
        self.Laser_1.addItem("")
        self.Laser_1.addItem("")
        self.label1 = QtWidgets.QLabel(Optogenetics)
        self.label1.setGeometry(QtCore.QRect(140, 30, 51, 20))
        self.label1.setTextFormat(QtCore.Qt.AutoText)
        self.label1.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label1.setObjectName("label1")
        self.Location_1 = QtWidgets.QComboBox(Optogenetics)
        self.Location_1.setGeometry(QtCore.QRect(200, 30, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Location_1.sizePolicy().hasHeightForWidth())
        self.Location_1.setSizePolicy(sizePolicy)
        self.Location_1.setObjectName("Location_1")
        self.Location_1.addItem("")
        self.Location_1.addItem("")
        self.Location_1.addItem("")
        self.Location_1.addItem("")
        self.AlignTo_1 = QtWidgets.QComboBox(Optogenetics)
        self.AlignTo_1.setGeometry(QtCore.QRect(350, 30, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AlignTo_1.sizePolicy().hasHeightForWidth())
        self.AlignTo_1.setSizePolicy(sizePolicy)
        self.AlignTo_1.setObjectName("AlignTo_1")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.AlignTo_1.addItem("")
        self.label2 = QtWidgets.QLabel(Optogenetics)
        self.label2.setGeometry(QtCore.QRect(290, 30, 51, 20))
        self.label2.setTextFormat(QtCore.Qt.AutoText)
        self.label2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label2.setObjectName("label2")
        self.label4 = QtWidgets.QLabel(Optogenetics)
        self.label4.setGeometry(QtCore.QRect(600, 30, 71, 20))
        self.label4.setTextFormat(QtCore.Qt.AutoText)
        self.label4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label4.setObjectName("label4")
        self.Duration_1 = QtWidgets.QLineEdit(Optogenetics)
        self.Duration_1.setGeometry(QtCore.QRect(680, 30, 41, 20))
        self.Duration_1.setObjectName("Duration_1")
        self.label5 = QtWidgets.QLabel(Optogenetics)
        self.label5.setGeometry(QtCore.QRect(740, 30, 51, 20))
        self.label5.setTextFormat(QtCore.Qt.AutoText)
        self.label5.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label5.setObjectName("label5")
        self.Protocol_1 = QtWidgets.QComboBox(Optogenetics)
        self.Protocol_1.setGeometry(QtCore.QRect(800, 30, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Protocol_1.sizePolicy().hasHeightForWidth())
        self.Protocol_1.setSizePolicy(sizePolicy)
        self.Protocol_1.setObjectName("Protocol_1")
        self.Protocol_1.addItem("")
        self.Protocol_1.addItem("")
        self.Protocol_1.addItem("")
        self.label3 = QtWidgets.QLabel(Optogenetics)
        self.label3.setGeometry(QtCore.QRect(450, 30, 71, 20))
        self.label3.setTextFormat(QtCore.Qt.AutoText)
        self.label3.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label3.setObjectName("label3")
        self.Probability_1 = QtWidgets.QLineEdit(Optogenetics)
        self.Probability_1.setGeometry(QtCore.QRect(530, 30, 41, 20))
        self.Probability_1.setObjectName("Probability_1")
        self.Frequency_1 = QtWidgets.QLineEdit(Optogenetics)
        self.Frequency_1.setGeometry(QtCore.QRect(970, 30, 41, 20))
        self.Frequency_1.setObjectName("Frequency_1")
        self.label6 = QtWidgets.QLabel(Optogenetics)
        self.label6.setGeometry(QtCore.QRect(890, 30, 71, 20))
        self.label6.setTextFormat(QtCore.Qt.AutoText)
        self.label6.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label6.setObjectName("label6")
        self.label14 = QtWidgets.QLabel(Optogenetics)
        self.label14.setEnabled(False)
        self.label14.setGeometry(QtCore.QRect(740, 70, 51, 20))
        self.label14.setTextFormat(QtCore.Qt.AutoText)
        self.label14.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label14.setObjectName("label14")
        self.Frequency_2 = QtWidgets.QLineEdit(Optogenetics)
        self.Frequency_2.setEnabled(False)
        self.Frequency_2.setGeometry(QtCore.QRect(970, 70, 41, 20))
        self.Frequency_2.setObjectName("Frequency_2")
        self.Probability_2 = QtWidgets.QLineEdit(Optogenetics)
        self.Probability_2.setEnabled(False)
        self.Probability_2.setGeometry(QtCore.QRect(530, 70, 41, 20))
        self.Probability_2.setObjectName("Probability_2")
        self.label11 = QtWidgets.QLabel(Optogenetics)
        self.label11.setEnabled(False)
        self.label11.setGeometry(QtCore.QRect(290, 70, 51, 20))
        self.label11.setTextFormat(QtCore.Qt.AutoText)
        self.label11.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label11.setObjectName("label11")
        self.Protocol_2 = QtWidgets.QComboBox(Optogenetics)
        self.Protocol_2.setEnabled(False)
        self.Protocol_2.setGeometry(QtCore.QRect(800, 70, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Protocol_2.sizePolicy().hasHeightForWidth())
        self.Protocol_2.setSizePolicy(sizePolicy)
        self.Protocol_2.setObjectName("Protocol_2")
        self.Protocol_2.addItem("")
        self.Protocol_2.addItem("")
        self.Protocol_2.addItem("")
        self.Protocol_2.addItem("")
        self.label15 = QtWidgets.QLabel(Optogenetics)
        self.label15.setEnabled(False)
        self.label15.setGeometry(QtCore.QRect(890, 70, 71, 20))
        self.label15.setTextFormat(QtCore.Qt.AutoText)
        self.label15.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label15.setObjectName("label15")
        self.Location_2 = QtWidgets.QComboBox(Optogenetics)
        self.Location_2.setEnabled(False)
        self.Location_2.setGeometry(QtCore.QRect(200, 70, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Location_2.sizePolicy().hasHeightForWidth())
        self.Location_2.setSizePolicy(sizePolicy)
        self.Location_2.setObjectName("Location_2")
        self.Location_2.addItem("")
        self.Location_2.addItem("")
        self.Location_2.addItem("")
        self.Location_2.addItem("")
        self.label12 = QtWidgets.QLabel(Optogenetics)
        self.label12.setEnabled(False)
        self.label12.setGeometry(QtCore.QRect(450, 70, 71, 20))
        self.label12.setTextFormat(QtCore.Qt.AutoText)
        self.label12.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label12.setObjectName("label12")
        self.Laser_2 = QtWidgets.QComboBox(Optogenetics)
        self.Laser_2.setGeometry(QtCore.QRect(50, 70, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Laser_2.sizePolicy().hasHeightForWidth())
        self.Laser_2.setSizePolicy(sizePolicy)
        self.Laser_2.setObjectName("Laser_2")
        self.Laser_2.addItem("")
        self.Laser_2.addItem("")
        self.Laser_2.addItem("")
        self.Laser_2.addItem("")
        self.Laser_2.addItem("")
        self.label10 = QtWidgets.QLabel(Optogenetics)
        self.label10.setEnabled(False)
        self.label10.setGeometry(QtCore.QRect(140, 70, 51, 20))
        self.label10.setTextFormat(QtCore.Qt.AutoText)
        self.label10.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label10.setObjectName("label10")
        self.AlignTo_2 = QtWidgets.QComboBox(Optogenetics)
        self.AlignTo_2.setEnabled(False)
        self.AlignTo_2.setGeometry(QtCore.QRect(350, 70, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AlignTo_2.sizePolicy().hasHeightForWidth())
        self.AlignTo_2.setSizePolicy(sizePolicy)
        self.AlignTo_2.setObjectName("AlignTo_2")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.AlignTo_2.addItem("")
        self.label9 = QtWidgets.QLabel(Optogenetics)
        self.label9.setGeometry(QtCore.QRect(10, 72, 31, 16))
        self.label9.setObjectName("label9")
        self.label13 = QtWidgets.QLabel(Optogenetics)
        self.label13.setEnabled(False)
        self.label13.setGeometry(QtCore.QRect(600, 70, 71, 20))
        self.label13.setTextFormat(QtCore.Qt.AutoText)
        self.label13.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label13.setObjectName("label13")
        self.Duration_2 = QtWidgets.QLineEdit(Optogenetics)
        self.Duration_2.setEnabled(False)
        self.Duration_2.setGeometry(QtCore.QRect(680, 70, 41, 20))
        self.Duration_2.setObjectName("Duration_2")
        self.RD_1 = QtWidgets.QLineEdit(Optogenetics)
        self.RD_1.setGeometry(QtCore.QRect(1070, 30, 41, 20))
        self.RD_1.setObjectName("RD_1")
        self.label7 = QtWidgets.QLabel(Optogenetics)
        self.label7.setGeometry(QtCore.QRect(1010, 30, 51, 20))
        self.label7.setTextFormat(QtCore.Qt.AutoText)
        self.label7.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label7.setObjectName("label7")
        self.PulseDur_1 = QtWidgets.QLineEdit(Optogenetics)
        self.PulseDur_1.setEnabled(False)
        self.PulseDur_1.setGeometry(QtCore.QRect(1200, 30, 41, 20))
        self.PulseDur_1.setReadOnly(False)
        self.PulseDur_1.setObjectName("PulseDur_1")
        self.label8 = QtWidgets.QLabel(Optogenetics)
        self.label8.setEnabled(False)
        self.label8.setGeometry(QtCore.QRect(1120, 30, 71, 20))
        self.label8.setTextFormat(QtCore.Qt.AutoText)
        self.label8.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label8.setObjectName("label8")
        self.RD_2 = QtWidgets.QLineEdit(Optogenetics)
        self.RD_2.setEnabled(False)
        self.RD_2.setGeometry(QtCore.QRect(1070, 70, 41, 20))
        self.RD_2.setObjectName("RD_2")
        self.PulseDur_2 = QtWidgets.QLineEdit(Optogenetics)
        self.PulseDur_2.setEnabled(False)
        self.PulseDur_2.setGeometry(QtCore.QRect(1200, 70, 41, 20))
        self.PulseDur_2.setObjectName("PulseDur_2")
        self.label16 = QtWidgets.QLabel(Optogenetics)
        self.label16.setEnabled(False)
        self.label16.setGeometry(QtCore.QRect(1010, 70, 51, 20))
        self.label16.setTextFormat(QtCore.Qt.AutoText)
        self.label16.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label16.setObjectName("label16")
        self.label17 = QtWidgets.QLabel(Optogenetics)
        self.label17.setEnabled(False)
        self.label17.setGeometry(QtCore.QRect(1120, 70, 71, 20))
        self.label17.setTextFormat(QtCore.Qt.AutoText)
        self.label17.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label17.setObjectName("label17")
        self.label26 = QtWidgets.QLabel(Optogenetics)
        self.label26.setEnabled(False)
        self.label26.setGeometry(QtCore.QRect(1120, 110, 71, 20))
        self.label26.setTextFormat(QtCore.Qt.AutoText)
        self.label26.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label26.setObjectName("label26")
        self.label24 = QtWidgets.QLabel(Optogenetics)
        self.label24.setEnabled(False)
        self.label24.setGeometry(QtCore.QRect(890, 110, 71, 20))
        self.label24.setTextFormat(QtCore.Qt.AutoText)
        self.label24.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label24.setObjectName("label24")
        self.label19 = QtWidgets.QLabel(Optogenetics)
        self.label19.setEnabled(False)
        self.label19.setGeometry(QtCore.QRect(130, 110, 61, 20))
        self.label19.setTextFormat(QtCore.Qt.AutoText)
        self.label19.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label19.setObjectName("label19")
        self.label18 = QtWidgets.QLabel(Optogenetics)
        self.label18.setGeometry(QtCore.QRect(10, 112, 31, 16))
        self.label18.setObjectName("label18")
        self.Duration_3 = QtWidgets.QLineEdit(Optogenetics)
        self.Duration_3.setEnabled(False)
        self.Duration_3.setGeometry(QtCore.QRect(680, 110, 41, 20))
        self.Duration_3.setObjectName("Duration_3")
        self.Location_3 = QtWidgets.QComboBox(Optogenetics)
        self.Location_3.setEnabled(False)
        self.Location_3.setGeometry(QtCore.QRect(200, 110, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Location_3.sizePolicy().hasHeightForWidth())
        self.Location_3.setSizePolicy(sizePolicy)
        self.Location_3.setObjectName("Location_3")
        self.Location_3.addItem("")
        self.Location_3.addItem("")
        self.Location_3.addItem("")
        self.Location_3.addItem("")
        self.Laser_3 = QtWidgets.QComboBox(Optogenetics)
        self.Laser_3.setGeometry(QtCore.QRect(50, 110, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Laser_3.sizePolicy().hasHeightForWidth())
        self.Laser_3.setSizePolicy(sizePolicy)
        self.Laser_3.setObjectName("Laser_3")
        self.Laser_3.addItem("")
        self.Laser_3.addItem("")
        self.Laser_3.addItem("")
        self.Laser_3.addItem("")
        self.Laser_3.addItem("")
        self.label20 = QtWidgets.QLabel(Optogenetics)
        self.label20.setEnabled(False)
        self.label20.setGeometry(QtCore.QRect(290, 110, 51, 20))
        self.label20.setTextFormat(QtCore.Qt.AutoText)
        self.label20.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label20.setObjectName("label20")
        self.Protocol_3 = QtWidgets.QComboBox(Optogenetics)
        self.Protocol_3.setEnabled(False)
        self.Protocol_3.setGeometry(QtCore.QRect(800, 110, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Protocol_3.sizePolicy().hasHeightForWidth())
        self.Protocol_3.setSizePolicy(sizePolicy)
        self.Protocol_3.setObjectName("Protocol_3")
        self.Protocol_3.addItem("")
        self.Protocol_3.addItem("")
        self.Protocol_3.addItem("")
        self.Protocol_3.addItem("")
        self.label22 = QtWidgets.QLabel(Optogenetics)
        self.label22.setEnabled(False)
        self.label22.setGeometry(QtCore.QRect(600, 110, 71, 20))
        self.label22.setTextFormat(QtCore.Qt.AutoText)
        self.label22.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label22.setObjectName("label22")
        self.Probability_3 = QtWidgets.QLineEdit(Optogenetics)
        self.Probability_3.setEnabled(False)
        self.Probability_3.setGeometry(QtCore.QRect(530, 110, 41, 20))
        self.Probability_3.setObjectName("Probability_3")
        self.Frequency_3 = QtWidgets.QLineEdit(Optogenetics)
        self.Frequency_3.setEnabled(False)
        self.Frequency_3.setGeometry(QtCore.QRect(970, 110, 41, 20))
        self.Frequency_3.setObjectName("Frequency_3")
        self.label25 = QtWidgets.QLabel(Optogenetics)
        self.label25.setEnabled(False)
        self.label25.setGeometry(QtCore.QRect(1010, 110, 51, 20))
        self.label25.setTextFormat(QtCore.Qt.AutoText)
        self.label25.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label25.setObjectName("label25")
        self.label23 = QtWidgets.QLabel(Optogenetics)
        self.label23.setEnabled(False)
        self.label23.setGeometry(QtCore.QRect(740, 110, 51, 20))
        self.label23.setTextFormat(QtCore.Qt.AutoText)
        self.label23.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label23.setObjectName("label23")
        self.PulseDur_3 = QtWidgets.QLineEdit(Optogenetics)
        self.PulseDur_3.setEnabled(False)
        self.PulseDur_3.setGeometry(QtCore.QRect(1200, 110, 41, 20))
        self.PulseDur_3.setObjectName("PulseDur_3")
        self.label21 = QtWidgets.QLabel(Optogenetics)
        self.label21.setEnabled(False)
        self.label21.setGeometry(QtCore.QRect(450, 110, 71, 20))
        self.label21.setTextFormat(QtCore.Qt.AutoText)
        self.label21.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label21.setObjectName("label21")
        self.RD_3 = QtWidgets.QLineEdit(Optogenetics)
        self.RD_3.setEnabled(False)
        self.RD_3.setGeometry(QtCore.QRect(1070, 110, 41, 20))
        self.RD_3.setObjectName("RD_3")
        self.AlignTo_3 = QtWidgets.QComboBox(Optogenetics)
        self.AlignTo_3.setEnabled(False)
        self.AlignTo_3.setGeometry(QtCore.QRect(350, 110, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AlignTo_3.sizePolicy().hasHeightForWidth())
        self.AlignTo_3.setSizePolicy(sizePolicy)
        self.AlignTo_3.setObjectName("AlignTo_3")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.AlignTo_3.addItem("")
        self.label28 = QtWidgets.QLabel(Optogenetics)
        self.label28.setEnabled(False)
        self.label28.setGeometry(QtCore.QRect(140, 150, 51, 20))
        self.label28.setTextFormat(QtCore.Qt.AutoText)
        self.label28.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label28.setObjectName("label28")
        self.label31 = QtWidgets.QLabel(Optogenetics)
        self.label31.setEnabled(False)
        self.label31.setGeometry(QtCore.QRect(600, 150, 71, 20))
        self.label31.setTextFormat(QtCore.Qt.AutoText)
        self.label31.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label31.setObjectName("label31")
        self.label29 = QtWidgets.QLabel(Optogenetics)
        self.label29.setEnabled(False)
        self.label29.setGeometry(QtCore.QRect(290, 150, 51, 20))
        self.label29.setTextFormat(QtCore.Qt.AutoText)
        self.label29.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label29.setObjectName("label29")
        self.label32 = QtWidgets.QLabel(Optogenetics)
        self.label32.setEnabled(False)
        self.label32.setGeometry(QtCore.QRect(740, 150, 51, 20))
        self.label32.setTextFormat(QtCore.Qt.AutoText)
        self.label32.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label32.setObjectName("label32")
        self.RD_4 = QtWidgets.QLineEdit(Optogenetics)
        self.RD_4.setEnabled(False)
        self.RD_4.setGeometry(QtCore.QRect(1070, 150, 41, 20))
        self.RD_4.setObjectName("RD_4")
        self.Probability_4 = QtWidgets.QLineEdit(Optogenetics)
        self.Probability_4.setEnabled(False)
        self.Probability_4.setGeometry(QtCore.QRect(530, 150, 41, 20))
        self.Probability_4.setObjectName("Probability_4")
        self.label30 = QtWidgets.QLabel(Optogenetics)
        self.label30.setEnabled(False)
        self.label30.setGeometry(QtCore.QRect(450, 150, 71, 20))
        self.label30.setTextFormat(QtCore.Qt.AutoText)
        self.label30.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label30.setObjectName("label30")
        self.Frequency_4 = QtWidgets.QLineEdit(Optogenetics)
        self.Frequency_4.setEnabled(False)
        self.Frequency_4.setGeometry(QtCore.QRect(970, 150, 41, 20))
        self.Frequency_4.setObjectName("Frequency_4")
        self.label34 = QtWidgets.QLabel(Optogenetics)
        self.label34.setEnabled(False)
        self.label34.setGeometry(QtCore.QRect(1010, 150, 51, 20))
        self.label34.setTextFormat(QtCore.Qt.AutoText)
        self.label34.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label34.setObjectName("label34")
        self.Laser_4 = QtWidgets.QComboBox(Optogenetics)
        self.Laser_4.setGeometry(QtCore.QRect(50, 150, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Laser_4.sizePolicy().hasHeightForWidth())
        self.Laser_4.setSizePolicy(sizePolicy)
        self.Laser_4.setObjectName("Laser_4")
        self.Laser_4.addItem("")
        self.Laser_4.addItem("")
        self.Laser_4.addItem("")
        self.Laser_4.addItem("")
        self.Laser_4.addItem("")
        self.label35 = QtWidgets.QLabel(Optogenetics)
        self.label35.setEnabled(False)
        self.label35.setGeometry(QtCore.QRect(1120, 150, 71, 20))
        self.label35.setTextFormat(QtCore.Qt.AutoText)
        self.label35.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label35.setObjectName("label35")
        self.PulseDur_4 = QtWidgets.QLineEdit(Optogenetics)
        self.PulseDur_4.setEnabled(False)
        self.PulseDur_4.setGeometry(QtCore.QRect(1200, 150, 41, 20))
        self.PulseDur_4.setObjectName("PulseDur_4")
        self.Protocol_4 = QtWidgets.QComboBox(Optogenetics)
        self.Protocol_4.setEnabled(False)
        self.Protocol_4.setGeometry(QtCore.QRect(800, 150, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Protocol_4.sizePolicy().hasHeightForWidth())
        self.Protocol_4.setSizePolicy(sizePolicy)
        self.Protocol_4.setObjectName("Protocol_4")
        self.Protocol_4.addItem("")
        self.Protocol_4.addItem("")
        self.Protocol_4.addItem("")
        self.Protocol_4.addItem("")
        self.label33 = QtWidgets.QLabel(Optogenetics)
        self.label33.setEnabled(False)
        self.label33.setGeometry(QtCore.QRect(890, 150, 71, 20))
        self.label33.setTextFormat(QtCore.Qt.AutoText)
        self.label33.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label33.setObjectName("label33")
        self.label27 = QtWidgets.QLabel(Optogenetics)
        self.label27.setGeometry(QtCore.QRect(10, 152, 31, 16))
        self.label27.setObjectName("label27")
        self.Duration_4 = QtWidgets.QLineEdit(Optogenetics)
        self.Duration_4.setEnabled(False)
        self.Duration_4.setGeometry(QtCore.QRect(680, 150, 41, 20))
        self.Duration_4.setObjectName("Duration_4")
        self.Location_4 = QtWidgets.QComboBox(Optogenetics)
        self.Location_4.setEnabled(False)
        self.Location_4.setGeometry(QtCore.QRect(200, 150, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Location_4.sizePolicy().hasHeightForWidth())
        self.Location_4.setSizePolicy(sizePolicy)
        self.Location_4.setObjectName("Location_4")
        self.Location_4.addItem("")
        self.Location_4.addItem("")
        self.Location_4.addItem("")
        self.Location_4.addItem("")
        self.AlignTo_4 = QtWidgets.QComboBox(Optogenetics)
        self.AlignTo_4.setEnabled(False)
        self.AlignTo_4.setGeometry(QtCore.QRect(350, 150, 80, 20))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.AlignTo_4.sizePolicy().hasHeightForWidth())
        self.AlignTo_4.setSizePolicy(sizePolicy)
        self.AlignTo_4.setObjectName("AlignTo_4")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")
        self.AlignTo_4.addItem("")

        self.retranslateUi(Optogenetics)
        self.Protocol_2.setCurrentIndex(3)
        self.Location_2.setCurrentIndex(3)
        self.Laser_2.setCurrentIndex(4)
        self.AlignTo_2.setCurrentIndex(9)
        self.Location_3.setCurrentIndex(3)
        self.Laser_3.setCurrentIndex(4)
        self.Protocol_3.setCurrentIndex(3)
        self.AlignTo_3.setCurrentIndex(9)
        self.Laser_4.setCurrentIndex(4)
        self.Protocol_4.setCurrentIndex(3)
        self.Location_4.setCurrentIndex(3)
        self.AlignTo_4.setCurrentIndex(9)
        QtCore.QMetaObject.connectSlotsByName(Optogenetics)

    def retranslateUi(self, Optogenetics):
        _translate = QtCore.QCoreApplication.translate
        Optogenetics.setWindowTitle(_translate("Optogenetics", "Optogenetics"))
        self.label.setText(_translate("Optogenetics", "Laser"))
        self.Laser_1.setItemText(0, _translate("Optogenetics", "Blue"))
        self.Laser_1.setItemText(1, _translate("Optogenetics", "Red"))
        self.Laser_1.setItemText(2, _translate("Optogenetics", "Orange"))
        self.Laser_1.setItemText(3, _translate("Optogenetics", "Green"))
        self.Laser_1.setItemText(4, _translate("Optogenetics", "NA"))
        self.label1.setText(_translate("Optogenetics", "location ="))
        self.Location_1.setItemText(0, _translate("Optogenetics", "Both"))
        self.Location_1.setItemText(1, _translate("Optogenetics", "Left"))
        self.Location_1.setItemText(2, _translate("Optogenetics", "Right"))
        self.Location_1.setItemText(3, _translate("Optogenetics", "NA"))
        self.AlignTo_1.setItemText(0, _translate("Optogenetics", "Trial start"))
        self.AlignTo_1.setItemText(1, _translate("Optogenetics", "After go cue"))
        self.AlignTo_1.setItemText(2, _translate("Optogenetics", "Before go cue"))
        self.AlignTo_1.setItemText(3, _translate("Optogenetics", "Left choice"))
        self.AlignTo_1.setItemText(4, _translate("Optogenetics", "Right choice"))
        self.AlignTo_1.setItemText(5, _translate("Optogenetics", "Left reward"))
        self.AlignTo_1.setItemText(6, _translate("Optogenetics", "Right reward"))
        self.AlignTo_1.setItemText(7, _translate("Optogenetics", "Left no reward"))
        self.AlignTo_1.setItemText(8, _translate("Optogenetics", "Right no reward"))
        self.AlignTo_1.setItemText(9, _translate("Optogenetics", "NA"))
        self.label2.setText(_translate("Optogenetics", "align to ="))
        self.label4.setText(_translate("Optogenetics", "duration (s) ="))
        self.Duration_1.setText(_translate("Optogenetics", "5"))
        self.label5.setText(_translate("Optogenetics", "protocol ="))
        self.Protocol_1.setItemText(0, _translate("Optogenetics", "Sine"))
        self.Protocol_1.setItemText(1, _translate("Optogenetics", "Pulse"))
        self.Protocol_1.setItemText(2, _translate("Optogenetics", "Constant"))
        self.label3.setText(_translate("Optogenetics", "probability ="))
        self.Probability_1.setText(_translate("Optogenetics", "0.25"))
        self.Frequency_1.setText(_translate("Optogenetics", "40"))
        self.label6.setText(_translate("Optogenetics", "frequency ="))
        self.label14.setText(_translate("Optogenetics", "protocol ="))
        self.Frequency_2.setText(_translate("Optogenetics", "NA"))
        self.Probability_2.setText(_translate("Optogenetics", "NA"))
        self.label11.setText(_translate("Optogenetics", "align to ="))
        self.Protocol_2.setItemText(0, _translate("Optogenetics", "Sine"))
        self.Protocol_2.setItemText(1, _translate("Optogenetics", "Pulse"))
        self.Protocol_2.setItemText(2, _translate("Optogenetics", "Constant"))
        self.Protocol_2.setItemText(3, _translate("Optogenetics", "NA"))
        self.label15.setText(_translate("Optogenetics", "frequency ="))
        self.Location_2.setItemText(0, _translate("Optogenetics", "Both"))
        self.Location_2.setItemText(1, _translate("Optogenetics", "Left"))
        self.Location_2.setItemText(2, _translate("Optogenetics", "Right"))
        self.Location_2.setItemText(3, _translate("Optogenetics", "NA"))
        self.label12.setText(_translate("Optogenetics", "probability ="))
        self.Laser_2.setItemText(0, _translate("Optogenetics", "Blue"))
        self.Laser_2.setItemText(1, _translate("Optogenetics", "Red"))
        self.Laser_2.setItemText(2, _translate("Optogenetics", "Orange"))
        self.Laser_2.setItemText(3, _translate("Optogenetics", "Green"))
        self.Laser_2.setItemText(4, _translate("Optogenetics", "NA"))
        self.label10.setText(_translate("Optogenetics", "location ="))
        self.AlignTo_2.setItemText(0, _translate("Optogenetics", "Trial start"))
        self.AlignTo_2.setItemText(1, _translate("Optogenetics", "After go cue"))
        self.AlignTo_2.setItemText(2, _translate("Optogenetics", "Before go cue"))
        self.AlignTo_2.setItemText(3, _translate("Optogenetics", "Left choice"))
        self.AlignTo_2.setItemText(4, _translate("Optogenetics", "Right choice"))
        self.AlignTo_2.setItemText(5, _translate("Optogenetics", "Left reward"))
        self.AlignTo_2.setItemText(6, _translate("Optogenetics", "Right reward"))
        self.AlignTo_2.setItemText(7, _translate("Optogenetics", "Left no reward"))
        self.AlignTo_2.setItemText(8, _translate("Optogenetics", "Right no reward"))
        self.AlignTo_2.setItemText(9, _translate("Optogenetics", "NA"))
        self.label9.setText(_translate("Optogenetics", "Laser"))
        self.label13.setText(_translate("Optogenetics", "duration (s) ="))
        self.Duration_2.setText(_translate("Optogenetics", "NA"))
        self.RD_1.setText(_translate("Optogenetics", "1"))
        self.label7.setText(_translate("Optogenetics", "RD (s)="))
        self.PulseDur_1.setText(_translate("Optogenetics", "NA"))
        self.label8.setText(_translate("Optogenetics", "pulse dur(s)="))
        self.RD_2.setText(_translate("Optogenetics", "NA"))
        self.PulseDur_2.setText(_translate("Optogenetics", "NA"))
        self.label16.setText(_translate("Optogenetics", "RD (s)="))
        self.label17.setText(_translate("Optogenetics", "pulse dur(s)="))
        self.label26.setText(_translate("Optogenetics", "pulse dur(s)="))
        self.label24.setText(_translate("Optogenetics", "frequency ="))
        self.label19.setText(_translate("Optogenetics", "location ="))
        self.label18.setText(_translate("Optogenetics", "Laser"))
        self.Duration_3.setText(_translate("Optogenetics", "NA"))
        self.Location_3.setItemText(0, _translate("Optogenetics", "Both"))
        self.Location_3.setItemText(1, _translate("Optogenetics", "Left"))
        self.Location_3.setItemText(2, _translate("Optogenetics", "Right"))
        self.Location_3.setItemText(3, _translate("Optogenetics", "NA"))
        self.Laser_3.setItemText(0, _translate("Optogenetics", "Blue"))
        self.Laser_3.setItemText(1, _translate("Optogenetics", "Red"))
        self.Laser_3.setItemText(2, _translate("Optogenetics", "Orange"))
        self.Laser_3.setItemText(3, _translate("Optogenetics", "Green"))
        self.Laser_3.setItemText(4, _translate("Optogenetics", "NA"))
        self.label20.setText(_translate("Optogenetics", "align to ="))
        self.Protocol_3.setItemText(0, _translate("Optogenetics", "Sine"))
        self.Protocol_3.setItemText(1, _translate("Optogenetics", "Pulse"))
        self.Protocol_3.setItemText(2, _translate("Optogenetics", "Constant"))
        self.Protocol_3.setItemText(3, _translate("Optogenetics", "NA"))
        self.label22.setText(_translate("Optogenetics", "duration (s) ="))
        self.Probability_3.setText(_translate("Optogenetics", "NA"))
        self.Frequency_3.setText(_translate("Optogenetics", "NA"))
        self.label25.setText(_translate("Optogenetics", "RD (s)="))
        self.label23.setText(_translate("Optogenetics", "protocol ="))
        self.PulseDur_3.setText(_translate("Optogenetics", "NA"))
        self.label21.setText(_translate("Optogenetics", "probability ="))
        self.RD_3.setText(_translate("Optogenetics", "NA"))
        self.AlignTo_3.setItemText(0, _translate("Optogenetics", "Trial start"))
        self.AlignTo_3.setItemText(1, _translate("Optogenetics", "After go cue"))
        self.AlignTo_3.setItemText(2, _translate("Optogenetics", "Before go cue"))
        self.AlignTo_3.setItemText(3, _translate("Optogenetics", "Left choice"))
        self.AlignTo_3.setItemText(4, _translate("Optogenetics", "Right choice"))
        self.AlignTo_3.setItemText(5, _translate("Optogenetics", "Left reward"))
        self.AlignTo_3.setItemText(6, _translate("Optogenetics", "Right reward"))
        self.AlignTo_3.setItemText(7, _translate("Optogenetics", "Left no reward"))
        self.AlignTo_3.setItemText(8, _translate("Optogenetics", "Right no reward"))
        self.AlignTo_3.setItemText(9, _translate("Optogenetics", "NA"))
        self.label28.setText(_translate("Optogenetics", "location ="))
        self.label31.setText(_translate("Optogenetics", "duration (s) ="))
        self.label29.setText(_translate("Optogenetics", "align to ="))
        self.label32.setText(_translate("Optogenetics", "protocol ="))
        self.RD_4.setText(_translate("Optogenetics", "NA"))
        self.Probability_4.setText(_translate("Optogenetics", "NA"))
        self.label30.setText(_translate("Optogenetics", "probability ="))
        self.Frequency_4.setText(_translate("Optogenetics", "NA"))
        self.label34.setText(_translate("Optogenetics", "RD (s)="))
        self.Laser_4.setItemText(0, _translate("Optogenetics", "Blue"))
        self.Laser_4.setItemText(1, _translate("Optogenetics", "Red"))
        self.Laser_4.setItemText(2, _translate("Optogenetics", "Orange"))
        self.Laser_4.setItemText(3, _translate("Optogenetics", "Green"))
        self.Laser_4.setItemText(4, _translate("Optogenetics", "NA"))
        self.label35.setText(_translate("Optogenetics", "pulse dur(s)="))
        self.PulseDur_4.setText(_translate("Optogenetics", "NA"))
        self.Protocol_4.setItemText(0, _translate("Optogenetics", "Sine"))
        self.Protocol_4.setItemText(1, _translate("Optogenetics", "Pulse"))
        self.Protocol_4.setItemText(2, _translate("Optogenetics", "Constant"))
        self.Protocol_4.setItemText(3, _translate("Optogenetics", "NA"))
        self.label33.setText(_translate("Optogenetics", "frequency ="))
        self.label27.setText(_translate("Optogenetics", "Laser"))
        self.Duration_4.setText(_translate("Optogenetics", "NA"))
        self.Location_4.setItemText(0, _translate("Optogenetics", "Both"))
        self.Location_4.setItemText(1, _translate("Optogenetics", "Left"))
        self.Location_4.setItemText(2, _translate("Optogenetics", "Right"))
        self.Location_4.setItemText(3, _translate("Optogenetics", "NA"))
        self.AlignTo_4.setItemText(0, _translate("Optogenetics", "Trial start"))
        self.AlignTo_4.setItemText(1, _translate("Optogenetics", "After go cue"))
        self.AlignTo_4.setItemText(2, _translate("Optogenetics", "Before go cue"))
        self.AlignTo_4.setItemText(3, _translate("Optogenetics", "Left choice"))
        self.AlignTo_4.setItemText(4, _translate("Optogenetics", "Right choice"))
        self.AlignTo_4.setItemText(5, _translate("Optogenetics", "Left reward"))
        self.AlignTo_4.setItemText(6, _translate("Optogenetics", "Right reward"))
        self.AlignTo_4.setItemText(7, _translate("Optogenetics", "Left no reward"))
        self.AlignTo_4.setItemText(8, _translate("Optogenetics", "Right no reward"))
        self.AlignTo_4.setItemText(9, _translate("Optogenetics", "NA"))
