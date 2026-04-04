# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QScrollBar, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QSplitter,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(1121, 641)
        self.horizontalLayout_21 = QHBoxLayout(Widget)
        self.horizontalLayout_21.setSpacing(3)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(3, 3, 3, 3)
        self.wgtLeft = QWidget(Widget)
        self.wgtLeft.setObjectName(u"wgtLeft")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wgtLeft.sizePolicy().hasHeightForWidth())
        self.wgtLeft.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.wgtLeft)
        self.verticalLayout_3.setSpacing(3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(3, 3, 3, 3)
        self.wgtBias = QWidget(self.wgtLeft)
        self.wgtBias.setObjectName(u"wgtBias")
        self.verticalLayout_2 = QVBoxLayout(self.wgtBias)
        self.verticalLayout_2.setSpacing(3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(3, 3, 3, 3)
        self.tbLeft = QTabWidget(self.wgtBias)
        self.tbLeft.setObjectName(u"tbLeft")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(2)
        sizePolicy1.setHeightForWidth(self.tbLeft.sizePolicy().hasHeightForWidth())
        self.tbLeft.setSizePolicy(sizePolicy1)
        self.tbConfiguration = QWidget()
        self.tbConfiguration.setObjectName(u"tbConfiguration")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(1)
        sizePolicy2.setHeightForWidth(self.tbConfiguration.sizePolicy().hasHeightForWidth())
        self.tbConfiguration.setSizePolicy(sizePolicy2)
        self.verticalLayout_10 = QVBoxLayout(self.tbConfiguration)
        self.verticalLayout_10.setSpacing(3)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(3, 3, 3, 3)
        self.wgtSerial = QWidget(self.tbConfiguration)
        self.wgtSerial.setObjectName(u"wgtSerial")
        self.horizontalLayout_11 = QHBoxLayout(self.wgtSerial)
        self.horizontalLayout_11.setSpacing(3)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(2, 2, 2, 2)
        self.cmdOpen = QPushButton(self.wgtSerial)
        self.cmdOpen.setObjectName(u"cmdOpen")

        self.horizontalLayout_11.addWidget(self.cmdOpen)

        self.cmdReset = QPushButton(self.wgtSerial)
        self.cmdReset.setObjectName(u"cmdReset")

        self.horizontalLayout_11.addWidget(self.cmdReset)

        self.cmdClear = QPushButton(self.wgtSerial)
        self.cmdClear.setObjectName(u"cmdClear")

        self.horizontalLayout_11.addWidget(self.cmdClear)

        self.lePort = QLineEdit(self.wgtSerial)
        self.lePort.setObjectName(u"lePort")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(7)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lePort.sizePolicy().hasHeightForWidth())
        self.lePort.setSizePolicy(sizePolicy3)

        self.horizontalLayout_11.addWidget(self.lePort)


        self.verticalLayout_10.addWidget(self.wgtSerial)

        self.line = QFrame(self.tbConfiguration)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_10.addWidget(self.line)

        self.wgtDACX = QWidget(self.tbConfiguration)
        self.wgtDACX.setObjectName(u"wgtDACX")
        self.horizontalLayout_4 = QHBoxLayout(self.wgtDACX)
        self.horizontalLayout_4.setSpacing(3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(3, 3, 3, 3)
        self.lblBias_2 = QLabel(self.wgtDACX)
        self.lblBias_2.setObjectName(u"lblBias_2")

        self.horizontalLayout_4.addWidget(self.lblBias_2)

        self.spnDACX = QSpinBox(self.wgtDACX)
        self.spnDACX.setObjectName(u"spnDACX")
        self.spnDACX.setMinimum(0)
        self.spnDACX.setMaximum(65535)
        self.spnDACX.setSingleStep(5)
        self.spnDACX.setValue(32768)

        self.horizontalLayout_4.addWidget(self.spnDACX)

        self.lblDACXVal = QLabel(self.wgtDACX)
        self.lblDACXVal.setObjectName(u"lblDACXVal")

        self.horizontalLayout_4.addWidget(self.lblDACXVal)


        self.verticalLayout_10.addWidget(self.wgtDACX)

        self.scr_DACX = QScrollBar(self.tbConfiguration)
        self.scr_DACX.setObjectName(u"scr_DACX")
        self.scr_DACX.setMaximum(65535)
        self.scr_DACX.setSingleStep(10)
        self.scr_DACX.setPageStep(100)
        self.scr_DACX.setValue(32768)
        self.scr_DACX.setOrientation(Qt.Horizontal)

        self.verticalLayout_10.addWidget(self.scr_DACX)

        self.wgtDACY = QWidget(self.tbConfiguration)
        self.wgtDACY.setObjectName(u"wgtDACY")
        self.horizontalLayout_6 = QHBoxLayout(self.wgtDACY)
        self.horizontalLayout_6.setSpacing(3)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(3, 3, 3, 3)
        self.lblDACY = QLabel(self.wgtDACY)
        self.lblDACY.setObjectName(u"lblDACY")

        self.horizontalLayout_6.addWidget(self.lblDACY)

        self.spnDACY = QSpinBox(self.wgtDACY)
        self.spnDACY.setObjectName(u"spnDACY")
        self.spnDACY.setMinimum(0)
        self.spnDACY.setMaximum(65535)
        self.spnDACY.setSingleStep(5)
        self.spnDACY.setValue(32768)

        self.horizontalLayout_6.addWidget(self.spnDACY)

        self.lblDACYVal = QLabel(self.wgtDACY)
        self.lblDACYVal.setObjectName(u"lblDACYVal")

        self.horizontalLayout_6.addWidget(self.lblDACYVal)


        self.verticalLayout_10.addWidget(self.wgtDACY)

        self.scr_DACY = QScrollBar(self.tbConfiguration)
        self.scr_DACY.setObjectName(u"scr_DACY")
        self.scr_DACY.setMaximum(65535)
        self.scr_DACY.setSingleStep(10)
        self.scr_DACY.setPageStep(100)
        self.scr_DACY.setValue(32768)
        self.scr_DACY.setOrientation(Qt.Horizontal)

        self.verticalLayout_10.addWidget(self.scr_DACY)

        self.wgtDACZ = QWidget(self.tbConfiguration)
        self.wgtDACZ.setObjectName(u"wgtDACZ")
        self.horizontalLayout_5 = QHBoxLayout(self.wgtDACZ)
        self.horizontalLayout_5.setSpacing(3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(3, 3, 3, 3)
        self.lblDACZ = QLabel(self.wgtDACZ)
        self.lblDACZ.setObjectName(u"lblDACZ")

        self.horizontalLayout_5.addWidget(self.lblDACZ)

        self.spnDACZ = QSpinBox(self.wgtDACZ)
        self.spnDACZ.setObjectName(u"spnDACZ")
        self.spnDACZ.setMinimum(0)
        self.spnDACZ.setMaximum(65535)
        self.spnDACZ.setSingleStep(5)
        self.spnDACZ.setValue(32768)

        self.horizontalLayout_5.addWidget(self.spnDACZ)

        self.lblDACZVal = QLabel(self.wgtDACZ)
        self.lblDACZVal.setObjectName(u"lblDACZVal")

        self.horizontalLayout_5.addWidget(self.lblDACZVal)


        self.verticalLayout_10.addWidget(self.wgtDACZ)

        self.scr_DACZ = QScrollBar(self.tbConfiguration)
        self.scr_DACZ.setObjectName(u"scr_DACZ")
        self.scr_DACZ.setMaximum(65535)
        self.scr_DACZ.setSingleStep(10)
        self.scr_DACZ.setPageStep(100)
        self.scr_DACZ.setValue(32769)
        self.scr_DACZ.setOrientation(Qt.Horizontal)

        self.verticalLayout_10.addWidget(self.scr_DACZ)

        self.cmdSetDAC = QPushButton(self.tbConfiguration)
        self.cmdSetDAC.setObjectName(u"cmdSetDAC")

        self.verticalLayout_10.addWidget(self.cmdSetDAC)

        self.wgtBiasCtls = QWidget(self.tbConfiguration)
        self.wgtBiasCtls.setObjectName(u"wgtBiasCtls")
        self.horizontalLayout_3 = QHBoxLayout(self.wgtBiasCtls)
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(3, 3, 3, 3)
        self.cmdSendBias = QPushButton(self.wgtBiasCtls)
        self.cmdSendBias.setObjectName(u"cmdSendBias")

        self.horizontalLayout_3.addWidget(self.cmdSendBias)

        self.lblBias = QLabel(self.wgtBiasCtls)
        self.lblBias.setObjectName(u"lblBias")

        self.horizontalLayout_3.addWidget(self.lblBias)

        self.spnBias = QSpinBox(self.wgtBiasCtls)
        self.spnBias.setObjectName(u"spnBias")
        self.spnBias.setMinimum(0)
        self.spnBias.setMaximum(65535)
        self.spnBias.setSingleStep(5)
        self.spnBias.setValue(32768)

        self.horizontalLayout_3.addWidget(self.spnBias)

        self.lblBiasVal = QLabel(self.wgtBiasCtls)
        self.lblBiasVal.setObjectName(u"lblBiasVal")

        self.horizontalLayout_3.addWidget(self.lblBiasVal)


        self.verticalLayout_10.addWidget(self.wgtBiasCtls)

        self.scr_Bias = QScrollBar(self.tbConfiguration)
        self.scr_Bias.setObjectName(u"scr_Bias")
        self.scr_Bias.setMaximum(65535)
        self.scr_Bias.setSingleStep(10)
        self.scr_Bias.setPageStep(100)
        self.scr_Bias.setValue(32768)
        self.scr_Bias.setOrientation(Qt.Horizontal)

        self.verticalLayout_10.addWidget(self.scr_Bias)

        self.wgtApproach = QWidget(self.tbConfiguration)
        self.wgtApproach.setObjectName(u"wgtApproach")
        self.horizontalLayout_8 = QHBoxLayout(self.wgtApproach)
        self.horizontalLayout_8.setSpacing(3)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(3, 3, 3, 3)
        self.cmdApproach = QPushButton(self.wgtApproach)
        self.cmdApproach.setObjectName(u"cmdApproach")

        self.horizontalLayout_8.addWidget(self.cmdApproach)

        self.cmdStop = QPushButton(self.wgtApproach)
        self.cmdStop.setObjectName(u"cmdStop")

        self.horizontalLayout_8.addWidget(self.cmdStop)

        self.leTargetDAC = QLineEdit(self.wgtApproach)
        self.leTargetDAC.setObjectName(u"leTargetDAC")

        self.horizontalLayout_8.addWidget(self.leTargetDAC)

        self.leSteps = QLineEdit(self.wgtApproach)
        self.leSteps.setObjectName(u"leSteps")

        self.horizontalLayout_8.addWidget(self.leSteps)


        self.verticalLayout_10.addWidget(self.wgtApproach)

        self.wgtSettle = QWidget(self.tbConfiguration)
        self.wgtSettle.setObjectName(u"wgtSettle")
        self.verticalLayout_19 = QVBoxLayout(self.wgtSettle)
        self.verticalLayout_19.setSpacing(2)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(2, 2, 2, 2)
        self.wgtTopSettle = QWidget(self.wgtSettle)
        self.wgtTopSettle.setObjectName(u"wgtTopSettle")
        self.horizontalLayout_30 = QHBoxLayout(self.wgtTopSettle)
        self.horizontalLayout_30.setSpacing(3)
        self.horizontalLayout_30.setObjectName(u"horizontalLayout_30")
        self.horizontalLayout_30.setContentsMargins(3, 3, 3, 3)
        self.wgtXSettle = QWidget(self.wgtTopSettle)
        self.wgtXSettle.setObjectName(u"wgtXSettle")
        self.horizontalLayout_25 = QHBoxLayout(self.wgtXSettle)
        self.horizontalLayout_25.setSpacing(2)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.horizontalLayout_25.setContentsMargins(2, 2, 2, 2)
        self.lbXSettle = QLabel(self.wgtXSettle)
        self.lbXSettle.setObjectName(u"lbXSettle")

        self.horizontalLayout_25.addWidget(self.lbXSettle)

        self.spnXSettle = QSpinBox(self.wgtXSettle)
        self.spnXSettle.setObjectName(u"spnXSettle")
        self.spnXSettle.setMaximum(1000)
        self.spnXSettle.setSingleStep(1)
        self.spnXSettle.setValue(5)

        self.horizontalLayout_25.addWidget(self.spnXSettle)


        self.horizontalLayout_30.addWidget(self.wgtXSettle)

        self.wgtYSettle = QWidget(self.wgtTopSettle)
        self.wgtYSettle.setObjectName(u"wgtYSettle")
        self.horizontalLayout_27 = QHBoxLayout(self.wgtYSettle)
        self.horizontalLayout_27.setSpacing(2)
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.horizontalLayout_27.setContentsMargins(2, 2, 2, 2)
        self.lblYSettle = QLabel(self.wgtYSettle)
        self.lblYSettle.setObjectName(u"lblYSettle")

        self.horizontalLayout_27.addWidget(self.lblYSettle)

        self.spnYSettle = QSpinBox(self.wgtYSettle)
        self.spnYSettle.setObjectName(u"spnYSettle")
        self.spnYSettle.setMaximum(1000)
        self.spnYSettle.setSingleStep(1)
        self.spnYSettle.setValue(5)

        self.horizontalLayout_27.addWidget(self.spnYSettle)


        self.horizontalLayout_30.addWidget(self.wgtYSettle)


        self.verticalLayout_19.addWidget(self.wgtTopSettle)

        self.wgtMidSettle = QWidget(self.wgtSettle)
        self.wgtMidSettle.setObjectName(u"wgtMidSettle")
        self.horizontalLayout_31 = QHBoxLayout(self.wgtMidSettle)
        self.horizontalLayout_31.setSpacing(3)
        self.horizontalLayout_31.setObjectName(u"horizontalLayout_31")
        self.horizontalLayout_31.setContentsMargins(3, 3, 3, 3)
        self.wgtZSettle = QWidget(self.wgtMidSettle)
        self.wgtZSettle.setObjectName(u"wgtZSettle")
        self.horizontalLayout_28 = QHBoxLayout(self.wgtZSettle)
        self.horizontalLayout_28.setSpacing(2)
        self.horizontalLayout_28.setObjectName(u"horizontalLayout_28")
        self.horizontalLayout_28.setContentsMargins(2, 2, 2, 2)
        self.lblZSettle = QLabel(self.wgtZSettle)
        self.lblZSettle.setObjectName(u"lblZSettle")

        self.horizontalLayout_28.addWidget(self.lblZSettle)

        self.spnZSettle = QSpinBox(self.wgtZSettle)
        self.spnZSettle.setObjectName(u"spnZSettle")
        self.spnZSettle.setMaximum(1000)
        self.spnZSettle.setSingleStep(1)
        self.spnZSettle.setValue(5)

        self.horizontalLayout_28.addWidget(self.spnZSettle)


        self.horizontalLayout_31.addWidget(self.wgtZSettle)

        self.wgtBiasSettle = QWidget(self.wgtMidSettle)
        self.wgtBiasSettle.setObjectName(u"wgtBiasSettle")
        self.horizontalLayout_29 = QHBoxLayout(self.wgtBiasSettle)
        self.horizontalLayout_29.setSpacing(2)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(2, 2, 2, 2)
        self.lblBiasSettle = QLabel(self.wgtBiasSettle)
        self.lblBiasSettle.setObjectName(u"lblBiasSettle")

        self.horizontalLayout_29.addWidget(self.lblBiasSettle)

        self.spnBiasSettle = QSpinBox(self.wgtBiasSettle)
        self.spnBiasSettle.setObjectName(u"spnBiasSettle")
        self.spnBiasSettle.setMaximum(1000)
        self.spnBiasSettle.setSingleStep(5)
        self.spnBiasSettle.setValue(100)

        self.horizontalLayout_29.addWidget(self.spnBiasSettle)


        self.horizontalLayout_31.addWidget(self.wgtBiasSettle)


        self.verticalLayout_19.addWidget(self.wgtMidSettle)

        self.wgtCmdSettle = QWidget(self.wgtSettle)
        self.wgtCmdSettle.setObjectName(u"wgtCmdSettle")
        self.horizontalLayout_32 = QHBoxLayout(self.wgtCmdSettle)
        self.horizontalLayout_32.setSpacing(2)
        self.horizontalLayout_32.setObjectName(u"horizontalLayout_32")
        self.horizontalLayout_32.setContentsMargins(2, 2, 2, 2)
        self.cmdSettle = QPushButton(self.wgtCmdSettle)
        self.cmdSettle.setObjectName(u"cmdSettle")

        self.horizontalLayout_32.addWidget(self.cmdSettle)

        self.horizontalSpacer_12 = QSpacerItem(348, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_32.addItem(self.horizontalSpacer_12)


        self.verticalLayout_19.addWidget(self.wgtCmdSettle)


        self.verticalLayout_10.addWidget(self.wgtSettle)

        self.wgtDAC = QWidget(self.tbConfiguration)
        self.wgtDAC.setObjectName(u"wgtDAC")
        self.horizontalLayout_7 = QHBoxLayout(self.wgtDAC)
        self.horizontalLayout_7.setSpacing(3)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(3, 3, 3, 3)

        self.verticalLayout_10.addWidget(self.wgtDAC)

        self.verticalSpacer = QSpacerItem(20, 184, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_10.addItem(self.verticalSpacer)

        self.tbLeft.addTab(self.tbConfiguration, "")
        self.tbScanning = QWidget()
        self.tbScanning.setObjectName(u"tbScanning")
        sizePolicy2.setHeightForWidth(self.tbScanning.sizePolicy().hasHeightForWidth())
        self.tbScanning.setSizePolicy(sizePolicy2)
        self.verticalLayout_12 = QVBoxLayout(self.tbScanning)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.grpScan = QGroupBox(self.tbScanning)
        self.grpScan.setObjectName(u"grpScan")
        self.verticalLayout_8 = QVBoxLayout(self.grpScan)
        self.verticalLayout_8.setSpacing(3)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(3, 3, 3, 3)
        self.wgtscanctl = QWidget(self.grpScan)
        self.wgtscanctl.setObjectName(u"wgtscanctl")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(4)
        sizePolicy4.setHeightForWidth(self.wgtscanctl.sizePolicy().hasHeightForWidth())
        self.wgtscanctl.setSizePolicy(sizePolicy4)

        self.verticalLayout_8.addWidget(self.wgtscanctl)

        self.wgtPIDLbls_2 = QWidget(self.grpScan)
        self.wgtPIDLbls_2.setObjectName(u"wgtPIDLbls_2")
        self.horizontalLayout_16 = QHBoxLayout(self.wgtPIDLbls_2)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(3, 3, 3, 3)
        self.lblBlank_2 = QLabel(self.wgtPIDLbls_2)
        self.lblBlank_2.setObjectName(u"lblBlank_2")

        self.horizontalLayout_16.addWidget(self.lblBlank_2)

        self.lblStart = QLabel(self.wgtPIDLbls_2)
        self.lblStart.setObjectName(u"lblStart")
        sizePolicy.setHeightForWidth(self.lblStart.sizePolicy().hasHeightForWidth())
        self.lblStart.setSizePolicy(sizePolicy)

        self.horizontalLayout_16.addWidget(self.lblStart)

        self.lblEnd = QLabel(self.wgtPIDLbls_2)
        self.lblEnd.setObjectName(u"lblEnd")
        sizePolicy.setHeightForWidth(self.lblEnd.sizePolicy().hasHeightForWidth())
        self.lblEnd.setSizePolicy(sizePolicy)

        self.horizontalLayout_16.addWidget(self.lblEnd)

        self.lblRes = QLabel(self.wgtPIDLbls_2)
        self.lblRes.setObjectName(u"lblRes")
        sizePolicy.setHeightForWidth(self.lblRes.sizePolicy().hasHeightForWidth())
        self.lblRes.setSizePolicy(sizePolicy)

        self.horizontalLayout_16.addWidget(self.lblRes)


        self.verticalLayout_8.addWidget(self.wgtPIDLbls_2)

        self.wgtLePID_3 = QWidget(self.grpScan)
        self.wgtLePID_3.setObjectName(u"wgtLePID_3")
        self.horizontalLayout_18 = QHBoxLayout(self.wgtLePID_3)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(3, 3, 3, 3)
        self.lblXScan = QLabel(self.wgtLePID_3)
        self.lblXScan.setObjectName(u"lblXScan")

        self.horizontalLayout_18.addWidget(self.lblXScan)

        self.leXStart = QLineEdit(self.wgtLePID_3)
        self.leXStart.setObjectName(u"leXStart")

        self.horizontalLayout_18.addWidget(self.leXStart)

        self.leXEnd = QLineEdit(self.wgtLePID_3)
        self.leXEnd.setObjectName(u"leXEnd")

        self.horizontalLayout_18.addWidget(self.leXEnd)

        self.leXRes = QLineEdit(self.wgtLePID_3)
        self.leXRes.setObjectName(u"leXRes")

        self.horizontalLayout_18.addWidget(self.leXRes)


        self.verticalLayout_8.addWidget(self.wgtLePID_3)

        self.wgtLePID_2 = QWidget(self.grpScan)
        self.wgtLePID_2.setObjectName(u"wgtLePID_2")
        self.horizontalLayout_17 = QHBoxLayout(self.wgtLePID_2)
        self.horizontalLayout_17.setSpacing(3)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(3, 3, 3, 3)
        self.lblYScan = QLabel(self.wgtLePID_2)
        self.lblYScan.setObjectName(u"lblYScan")

        self.horizontalLayout_17.addWidget(self.lblYScan)

        self.leYStart = QLineEdit(self.wgtLePID_2)
        self.leYStart.setObjectName(u"leYStart")

        self.horizontalLayout_17.addWidget(self.leYStart)

        self.leYEnd = QLineEdit(self.wgtLePID_2)
        self.leYEnd.setObjectName(u"leYEnd")

        self.horizontalLayout_17.addWidget(self.leYEnd)

        self.leYRes = QLineEdit(self.wgtLePID_2)
        self.leYRes.setObjectName(u"leYRes")

        self.horizontalLayout_17.addWidget(self.leYRes)


        self.verticalLayout_8.addWidget(self.wgtLePID_2)

        self.wgtLePID = QWidget(self.grpScan)
        self.wgtLePID.setObjectName(u"wgtLePID")
        self.horizontalLayout_14 = QHBoxLayout(self.wgtLePID)
        self.horizontalLayout_14.setSpacing(3)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(3, 3, 3, 3)
        self.pushButton = QPushButton(self.wgtLePID)
        self.pushButton.setObjectName(u"pushButton")

        self.horizontalLayout_14.addWidget(self.pushButton)

        self.lblKp = QLabel(self.wgtLePID)
        self.lblKp.setObjectName(u"lblKp")

        self.horizontalLayout_14.addWidget(self.lblKp)

        self.leKp = QLineEdit(self.wgtLePID)
        self.leKp.setObjectName(u"leKp")

        self.horizontalLayout_14.addWidget(self.leKp)

        self.lblKi = QLabel(self.wgtLePID)
        self.lblKi.setObjectName(u"lblKi")

        self.horizontalLayout_14.addWidget(self.lblKi)

        self.leKi = QLineEdit(self.wgtLePID)
        self.leKi.setObjectName(u"leKi")

        self.horizontalLayout_14.addWidget(self.leKi)

        self.lblKd = QLabel(self.wgtLePID)
        self.lblKd.setObjectName(u"lblKd")

        self.horizontalLayout_14.addWidget(self.lblKd)

        self.leKd = QLineEdit(self.wgtLePID)
        self.leKd.setObjectName(u"leKd")

        self.horizontalLayout_14.addWidget(self.leKd)


        self.verticalLayout_8.addWidget(self.wgtLePID)

        self.wgtConstCurrent = QWidget(self.grpScan)
        self.wgtConstCurrent.setObjectName(u"wgtConstCurrent")
        self.horizontalLayout_15 = QHBoxLayout(self.wgtConstCurrent)
        self.horizontalLayout_15.setSpacing(3)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(3, 3, 3, 3)
        self.chkConstCurrent = QCheckBox(self.wgtConstCurrent)
        self.chkConstCurrent.setObjectName(u"chkConstCurrent")

        self.horizontalLayout_15.addWidget(self.chkConstCurrent)

        self.lblCCTarget = QLabel(self.wgtConstCurrent)
        self.lblCCTarget.setObjectName(u"lblCCTarget")

        self.horizontalLayout_15.addWidget(self.lblCCTarget)

        self.leCCVal = QLineEdit(self.wgtConstCurrent)
        self.leCCVal.setObjectName(u"leCCVal")

        self.horizontalLayout_15.addWidget(self.leCCVal)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_13)


        self.verticalLayout_8.addWidget(self.wgtConstCurrent)

        self.wgtScan = QWidget(self.grpScan)
        self.wgtScan.setObjectName(u"wgtScan")
        self.horizontalLayout_19 = QHBoxLayout(self.wgtScan)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.horizontalLayout_19.setContentsMargins(3, 3, 3, 3)
        self.cmdScan = QPushButton(self.wgtScan)
        self.cmdScan.setObjectName(u"cmdScan")

        self.horizontalLayout_19.addWidget(self.cmdScan)

        self.lblscanSPP = QLabel(self.wgtScan)
        self.lblscanSPP.setObjectName(u"lblscanSPP")

        self.horizontalLayout_19.addWidget(self.lblscanSPP)

        self.leSamples = QLineEdit(self.wgtScan)
        self.leSamples.setObjectName(u"leSamples")

        self.horizontalLayout_19.addWidget(self.leSamples)

        self.cmdScanMulti = QPushButton(self.wgtScan)
        self.cmdScanMulti.setObjectName(u"cmdScanMulti")

        self.horizontalLayout_19.addWidget(self.cmdScanMulti)

        self.lblRepeat = QLabel(self.wgtScan)
        self.lblRepeat.setObjectName(u"lblRepeat")

        self.horizontalLayout_19.addWidget(self.lblRepeat)

        self.leMultiScanTimes = QLineEdit(self.wgtScan)
        self.leMultiScanTimes.setObjectName(u"leMultiScanTimes")

        self.horizontalLayout_19.addWidget(self.leMultiScanTimes)


        self.verticalLayout_8.addWidget(self.wgtScan)

        self.widget_5 = QWidget(self.grpScan)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout_22 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_22.setSpacing(3)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalLayout_22.setContentsMargins(3, 3, 3, 3)
        self.cmdSaveScan = QPushButton(self.widget_5)
        self.cmdSaveScan.setObjectName(u"cmdSaveScan")

        self.horizontalLayout_22.addWidget(self.cmdSaveScan)

        self.leSave = QLineEdit(self.widget_5)
        self.leSave.setObjectName(u"leSave")

        self.horizontalLayout_22.addWidget(self.leSave)


        self.verticalLayout_8.addWidget(self.widget_5)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_3)


        self.verticalLayout_12.addWidget(self.grpScan)

        self.tbLeft.addTab(self.tbScanning, "")

        self.verticalLayout_2.addWidget(self.tbLeft)

        self.wgtMotor = QWidget(self.wgtBias)
        self.wgtMotor.setObjectName(u"wgtMotor")
        self.horizontalLayout_13 = QHBoxLayout(self.wgtMotor)
        self.horizontalLayout_13.setSpacing(3)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(3, 3, 3, 3)
        self.lblMotor = QLabel(self.wgtMotor)
        self.lblMotor.setObjectName(u"lblMotor")

        self.horizontalLayout_13.addWidget(self.lblMotor)

        self.cmbMotDir = QComboBox(self.wgtMotor)
        self.cmbMotDir.addItem("")
        self.cmbMotDir.addItem("")
        self.cmbMotDir.setObjectName(u"cmbMotDir")

        self.horizontalLayout_13.addWidget(self.cmbMotDir)

        self.cmdMotOff = QPushButton(self.wgtMotor)
        self.cmdMotOff.setObjectName(u"cmdMotOff")

        self.horizontalLayout_13.addWidget(self.cmdMotOff)

        self.cmdMotDown = QPushButton(self.wgtMotor)
        self.cmdMotDown.setObjectName(u"cmdMotDown")

        self.horizontalLayout_13.addWidget(self.cmdMotDown)

        self.spnMot = QSpinBox(self.wgtMotor)
        self.spnMot.setObjectName(u"spnMot")
        self.spnMot.setMaximum(5000)
        self.spnMot.setSingleStep(5)
        self.spnMot.setValue(50)

        self.horizontalLayout_13.addWidget(self.spnMot)

        self.cmdMotUp = QPushButton(self.wgtMotor)
        self.cmdMotUp.setObjectName(u"cmdMotUp")

        self.horizontalLayout_13.addWidget(self.cmdMotUp)


        self.verticalLayout_2.addWidget(self.wgtMotor)

        self.wgtSend = QWidget(self.wgtBias)
        self.wgtSend.setObjectName(u"wgtSend")
        self.horizontalLayout_23 = QHBoxLayout(self.wgtSend)
        self.horizontalLayout_23.setSpacing(3)
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.horizontalLayout_23.setContentsMargins(3, 3, 3, 3)
        self.cmdSend = QPushButton(self.wgtSend)
        self.cmdSend.setObjectName(u"cmdSend")

        self.horizontalLayout_23.addWidget(self.cmdSend)

        self.leCommand = QLineEdit(self.wgtSend)
        self.leCommand.setObjectName(u"leCommand")

        self.horizontalLayout_23.addWidget(self.leCommand)


        self.verticalLayout_2.addWidget(self.wgtSend)

        self.txtLog = QTextBrowser(self.wgtBias)
        self.txtLog.setObjectName(u"txtLog")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.txtLog.sizePolicy().hasHeightForWidth())
        self.txtLog.setSizePolicy(sizePolicy5)

        self.verticalLayout_2.addWidget(self.txtLog)


        self.verticalLayout_3.addWidget(self.wgtBias)


        self.horizontalLayout_21.addWidget(self.wgtLeft)

        self.tabWidget = QTabWidget(Widget)
        self.tabWidget.setObjectName(u"tabWidget")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy6.setHorizontalStretch(3)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy6)
        self.tbMain = QWidget()
        self.tbMain.setObjectName(u"tbMain")
        self.verticalLayout_6 = QVBoxLayout(self.tbMain)
        self.verticalLayout_6.setSpacing(3)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(3, 3, 3, 3)
        self.wgtMainTop = QWidget(self.tbMain)
        self.wgtMainTop.setObjectName(u"wgtMainTop")
        sizePolicy2.setHeightForWidth(self.wgtMainTop.sizePolicy().hasHeightForWidth())
        self.wgtMainTop.setSizePolicy(sizePolicy2)
        self.verticalLayout_7 = QVBoxLayout(self.wgtMainTop)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(3, 3, 3, 3)
        self.splitter_3 = QSplitter(self.wgtMainTop)
        self.splitter_3.setObjectName(u"splitter_3")
        self.splitter_3.setOrientation(Qt.Vertical)
        self.wgtTopSplitter = QWidget(self.splitter_3)
        self.wgtTopSplitter.setObjectName(u"wgtTopSplitter")
        self.verticalLayout_9 = QVBoxLayout(self.wgtTopSplitter)
        self.verticalLayout_9.setSpacing(3)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(3, 3, 3, 3)
        self.splitter = QSplitter(self.wgtTopSplitter)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.pltCurrent = QWidget(self.splitter)
        self.pltCurrent.setObjectName(u"pltCurrent")
        sizePolicy5.setHeightForWidth(self.pltCurrent.sizePolicy().hasHeightForWidth())
        self.pltCurrent.setSizePolicy(sizePolicy5)
        self.splitter.addWidget(self.pltCurrent)
        self.pltDAC = QWidget(self.splitter)
        self.pltDAC.setObjectName(u"pltDAC")
        sizePolicy5.setHeightForWidth(self.pltDAC.sizePolicy().hasHeightForWidth())
        self.pltDAC.setSizePolicy(sizePolicy5)
        self.splitter.addWidget(self.pltDAC)

        self.verticalLayout_9.addWidget(self.splitter)

        self.splitter_3.addWidget(self.wgtTopSplitter)
        self.wgtBottomSplitter = QWidget(self.splitter_3)
        self.wgtBottomSplitter.setObjectName(u"wgtBottomSplitter")
        self.verticalLayout_11 = QVBoxLayout(self.wgtBottomSplitter)
        self.verticalLayout_11.setSpacing(3)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(3, 3, 3, 3)
        self.splitter_2 = QSplitter(self.wgtBottomSplitter)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Horizontal)
        self.pltSteps = QWidget(self.splitter_2)
        self.pltSteps.setObjectName(u"pltSteps")
        sizePolicy5.setHeightForWidth(self.pltSteps.sizePolicy().hasHeightForWidth())
        self.pltSteps.setSizePolicy(sizePolicy5)
        self.splitter_2.addWidget(self.pltSteps)
        self.pltVals = QWidget(self.splitter_2)
        self.pltVals.setObjectName(u"pltVals")
        sizePolicy5.setHeightForWidth(self.pltVals.sizePolicy().hasHeightForWidth())
        self.pltVals.setSizePolicy(sizePolicy5)
        self.splitter_2.addWidget(self.pltVals)

        self.verticalLayout_11.addWidget(self.splitter_2)

        self.splitter_3.addWidget(self.wgtBottomSplitter)

        self.verticalLayout_7.addWidget(self.splitter_3)


        self.verticalLayout_6.addWidget(self.wgtMainTop)

        self.wgtFrameBottom = QFrame(self.tbMain)
        self.wgtFrameBottom.setObjectName(u"wgtFrameBottom")
        self.wgtFrameBottom.setFrameShape(QFrame.StyledPanel)
        self.wgtFrameBottom.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.wgtFrameBottom)
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(2, 3, 3, 3)
        self.wgtAutoLevels = QWidget(self.wgtFrameBottom)
        self.wgtAutoLevels.setObjectName(u"wgtAutoLevels")
        self.horizontalLayout_12 = QHBoxLayout(self.wgtAutoLevels)
        self.horizontalLayout_12.setSpacing(3)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(3, 3, 3, 3)
        self.horizontalSpacer = QSpacerItem(565, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer)

        self.label = QLabel(self.wgtAutoLevels)
        self.label.setObjectName(u"label")

        self.horizontalLayout_12.addWidget(self.label)

        self.cmbColorPal = QComboBox(self.wgtAutoLevels)
        self.cmbColorPal.addItem("")
        self.cmbColorPal.addItem("")
        self.cmbColorPal.addItem("")
        self.cmbColorPal.addItem("")
        self.cmbColorPal.addItem("")
        self.cmbColorPal.addItem("")
        self.cmbColorPal.setObjectName(u"cmbColorPal")

        self.horizontalLayout_12.addWidget(self.cmbColorPal)


        self.verticalLayout.addWidget(self.wgtAutoLevels)


        self.verticalLayout_6.addWidget(self.wgtFrameBottom)

        self.tabWidget.addTab(self.tbMain, "")
        self.tbIV = QWidget()
        self.tbIV.setObjectName(u"tbIV")
        self.verticalLayout_5 = QVBoxLayout(self.tbIV)
        self.verticalLayout_5.setSpacing(3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(3, 3, 3, 3)
        self.widget = QWidget(self.tbIV)
        self.widget.setObjectName(u"widget")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy7)
        self.widget.setSizeIncrement(QSize(0, 4))
        self.verticalLayout_15 = QVBoxLayout(self.widget)
        self.verticalLayout_15.setSpacing(3)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(3, 3, 3, 3)
        self.splitter_4 = QSplitter(self.widget)
        self.splitter_4.setObjectName(u"splitter_4")
        self.splitter_4.setOrientation(Qt.Horizontal)
        self.pltIV = QWidget(self.splitter_4)
        self.pltIV.setObjectName(u"pltIV")
        sizePolicy2.setHeightForWidth(self.pltIV.sizePolicy().hasHeightForWidth())
        self.pltIV.setSizePolicy(sizePolicy2)
        self.splitter_4.addWidget(self.pltIV)
        self.pltdIdV = QWidget(self.splitter_4)
        self.pltdIdV.setObjectName(u"pltdIdV")
        self.splitter_4.addWidget(self.pltdIdV)

        self.verticalLayout_15.addWidget(self.splitter_4)


        self.verticalLayout_5.addWidget(self.widget)

        self.wgtScanIV = QWidget(self.tbIV)
        self.wgtScanIV.setObjectName(u"wgtScanIV")
        self.wgtScanIV.setSizeIncrement(QSize(0, 1))
        self.verticalLayout_4 = QVBoxLayout(self.wgtScanIV)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(3, 3, 3, 3)
        self.wgtPlotControls = QWidget(self.wgtScanIV)
        self.wgtPlotControls.setObjectName(u"wgtPlotControls")
        self.horizontalLayout_9 = QHBoxLayout(self.wgtPlotControls)
        self.horizontalLayout_9.setSpacing(3)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(3, 3, 3, 3)
        self.cmdScanIV = QPushButton(self.wgtPlotControls)
        self.cmdScanIV.setObjectName(u"cmdScanIV")

        self.horizontalLayout_9.addWidget(self.cmdScanIV)

        self.leIVStart = QLineEdit(self.wgtPlotControls)
        self.leIVStart.setObjectName(u"leIVStart")

        self.horizontalLayout_9.addWidget(self.leIVStart)

        self.leIVEnd = QLineEdit(self.wgtPlotControls)
        self.leIVEnd.setObjectName(u"leIVEnd")

        self.horizontalLayout_9.addWidget(self.leIVEnd)

        self.leIVStep = QLineEdit(self.wgtPlotControls)
        self.leIVStep.setObjectName(u"leIVStep")

        self.horizontalLayout_9.addWidget(self.leIVStep)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_5)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_4)


        self.verticalLayout_4.addWidget(self.wgtPlotControls)

        self.wgtIVButtons2 = QWidget(self.wgtScanIV)
        self.wgtIVButtons2.setObjectName(u"wgtIVButtons2")
        self.horizontalLayout_10 = QHBoxLayout(self.wgtIVButtons2)
        self.horizontalLayout_10.setSpacing(3)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(3, 3, 3, 3)
        self.cmdSaveIV = QPushButton(self.wgtIVButtons2)
        self.cmdSaveIV.setObjectName(u"cmdSaveIV")

        self.horizontalLayout_10.addWidget(self.cmdSaveIV)

        self.leIVFilename = QLineEdit(self.wgtIVButtons2)
        self.leIVFilename.setObjectName(u"leIVFilename")

        self.horizontalLayout_10.addWidget(self.leIVFilename)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_3)


        self.verticalLayout_4.addWidget(self.wgtIVButtons2)


        self.verticalLayout_5.addWidget(self.wgtScanIV)

        self.tabWidget.addTab(self.tbIV, "")
        self.tbdIdZ = QWidget()
        self.tbdIdZ.setObjectName(u"tbdIdZ")
        self.verticalLayout_14 = QVBoxLayout(self.tbdIdZ)
        self.verticalLayout_14.setSpacing(3)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(3, 3, 3, 3)
        self.pltdIdZ = QWidget(self.tbdIdZ)
        self.pltdIdZ.setObjectName(u"pltdIdZ")
        sizePolicy2.setHeightForWidth(self.pltdIdZ.sizePolicy().hasHeightForWidth())
        self.pltdIdZ.setSizePolicy(sizePolicy2)

        self.verticalLayout_14.addWidget(self.pltdIdZ)

        self.wgtScanIV_2 = QWidget(self.tbdIdZ)
        self.wgtScanIV_2.setObjectName(u"wgtScanIV_2")
        self.verticalLayout_13 = QVBoxLayout(self.wgtScanIV_2)
        self.verticalLayout_13.setSpacing(3)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(3, 3, 3, 3)
        self.wgtPlotdIdZControls = QWidget(self.wgtScanIV_2)
        self.wgtPlotdIdZControls.setObjectName(u"wgtPlotdIdZControls")
        self.horizontalLayout_20 = QHBoxLayout(self.wgtPlotdIdZControls)
        self.horizontalLayout_20.setSpacing(3)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(3, 3, 3, 3)
        self.cmdScandIdZ = QPushButton(self.wgtPlotdIdZControls)
        self.cmdScandIdZ.setObjectName(u"cmdScandIdZ")

        self.horizontalLayout_20.addWidget(self.cmdScandIdZ)

        self.ledIdZStart = QLineEdit(self.wgtPlotdIdZControls)
        self.ledIdZStart.setObjectName(u"ledIdZStart")

        self.horizontalLayout_20.addWidget(self.ledIdZStart)

        self.ledIdZEnd = QLineEdit(self.wgtPlotdIdZControls)
        self.ledIdZEnd.setObjectName(u"ledIdZEnd")

        self.horizontalLayout_20.addWidget(self.ledIdZEnd)

        self.ledIdZStep = QLineEdit(self.wgtPlotdIdZControls)
        self.ledIdZStep.setObjectName(u"ledIdZStep")

        self.horizontalLayout_20.addWidget(self.ledIdZStep)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_6)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_7)


        self.verticalLayout_13.addWidget(self.wgtPlotdIdZControls)

        self.wgtIVButtons2_2 = QWidget(self.wgtScanIV_2)
        self.wgtIVButtons2_2.setObjectName(u"wgtIVButtons2_2")
        self.horizontalLayout_24 = QHBoxLayout(self.wgtIVButtons2_2)
        self.horizontalLayout_24.setSpacing(3)
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.horizontalLayout_24.setContentsMargins(3, 3, 3, 3)
        self.cmdSaveIV_2 = QPushButton(self.wgtIVButtons2_2)
        self.cmdSaveIV_2.setObjectName(u"cmdSaveIV_2")

        self.horizontalLayout_24.addWidget(self.cmdSaveIV_2)

        self.leIVFilename_2 = QLineEdit(self.wgtIVButtons2_2)
        self.leIVFilename_2.setObjectName(u"leIVFilename_2")

        self.horizontalLayout_24.addWidget(self.leIVFilename_2)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer_8)


        self.verticalLayout_13.addWidget(self.wgtIVButtons2_2)


        self.verticalLayout_14.addWidget(self.wgtScanIV_2)

        self.tabWidget.addTab(self.tbdIdZ, "")
        self.tbGridSpectro = QWidget()
        self.tbGridSpectro.setObjectName(u"tbGridSpectro")
        self.verticalLayout_17 = QVBoxLayout(self.tbGridSpectro)
        self.verticalLayout_17.setSpacing(3)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(3, 3, 3, 3)
        self.wgtTopGrid = QWidget(self.tbGridSpectro)
        self.wgtTopGrid.setObjectName(u"wgtTopGrid")
        sizePolicy8 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(4)
        sizePolicy8.setHeightForWidth(self.wgtTopGrid.sizePolicy().hasHeightForWidth())
        self.wgtTopGrid.setSizePolicy(sizePolicy8)
        self.wgtTopGrid.setMinimumSize(QSize(0, 50))
        self.horizontalLayout = QHBoxLayout(self.wgtTopGrid)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(3, 3, 3, 3)
        self.pltGridImage = QWidget(self.wgtTopGrid)
        self.pltGridImage.setObjectName(u"pltGridImage")
        sizePolicy5.setHeightForWidth(self.pltGridImage.sizePolicy().hasHeightForWidth())
        self.pltGridImage.setSizePolicy(sizePolicy5)
        self.pltGridImage.setSizeIncrement(QSize(0, 0))

        self.horizontalLayout.addWidget(self.pltGridImage)

        self.wgtRightGridBias = QWidget(self.wgtTopGrid)
        self.wgtRightGridBias.setObjectName(u"wgtRightGridBias")
        self.verticalLayout_18 = QVBoxLayout(self.wgtRightGridBias)
        self.verticalLayout_18.setSpacing(3)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(3, 3, 3, 3)
        self.lblGridBias = QLabel(self.wgtRightGridBias)
        self.lblGridBias.setObjectName(u"lblGridBias")

        self.verticalLayout_18.addWidget(self.lblGridBias)

        self.sldGridBias = QSlider(self.wgtRightGridBias)
        self.sldGridBias.setObjectName(u"sldGridBias")
        self.sldGridBias.setMaximum(65535)
        self.sldGridBias.setSingleStep(10)
        self.sldGridBias.setPageStep(100)
        self.sldGridBias.setOrientation(Qt.Vertical)

        self.verticalLayout_18.addWidget(self.sldGridBias)

        self.spnGridBias = QSpinBox(self.wgtRightGridBias)
        self.spnGridBias.setObjectName(u"spnGridBias")
        self.spnGridBias.setMaximum(65535)
        self.spnGridBias.setSingleStep(10)

        self.verticalLayout_18.addWidget(self.spnGridBias)


        self.horizontalLayout.addWidget(self.wgtRightGridBias)


        self.verticalLayout_17.addWidget(self.wgtTopGrid)

        self.pltGridChart = QWidget(self.tbGridSpectro)
        self.pltGridChart.setObjectName(u"pltGridChart")
        sizePolicy9 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy9.setHorizontalStretch(0)
        sizePolicy9.setVerticalStretch(2)
        sizePolicy9.setHeightForWidth(self.pltGridChart.sizePolicy().hasHeightForWidth())
        self.pltGridChart.setSizePolicy(sizePolicy9)

        self.verticalLayout_17.addWidget(self.pltGridChart)

        self.wgtScanGrid = QWidget(self.tbGridSpectro)
        self.wgtScanGrid.setObjectName(u"wgtScanGrid")
        self.verticalLayout_16 = QVBoxLayout(self.wgtScanGrid)
        self.verticalLayout_16.setSpacing(3)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(3, 3, 3, 3)
        self.wgtGridBiasControls = QWidget(self.wgtScanGrid)
        self.wgtGridBiasControls.setObjectName(u"wgtGridBiasControls")
        self.wgtGridBiasControls.setSizeIncrement(QSize(0, 0))
        self.horizontalLayout_2 = QHBoxLayout(self.wgtGridBiasControls)
        self.horizontalLayout_2.setSpacing(3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(3, 3, 3, 3)
        self.cmdGridSpectro = QPushButton(self.wgtGridBiasControls)
        self.cmdGridSpectro.setObjectName(u"cmdGridSpectro")

        self.horizontalLayout_2.addWidget(self.cmdGridSpectro)

        self.leGridBiasStart = QLineEdit(self.wgtGridBiasControls)
        self.leGridBiasStart.setObjectName(u"leGridBiasStart")

        self.horizontalLayout_2.addWidget(self.leGridBiasStart)

        self.leGridBiasEnd = QLineEdit(self.wgtGridBiasControls)
        self.leGridBiasEnd.setObjectName(u"leGridBiasEnd")

        self.horizontalLayout_2.addWidget(self.leGridBiasEnd)

        self.leGridBiasPoints = QLineEdit(self.wgtGridBiasControls)
        self.leGridBiasPoints.setObjectName(u"leGridBiasPoints")

        self.horizontalLayout_2.addWidget(self.leGridBiasPoints)

        self.cmbGridSpectChoice = QComboBox(self.wgtGridBiasControls)
        self.cmbGridSpectChoice.addItem("")
        self.cmbGridSpectChoice.addItem("")
        self.cmbGridSpectChoice.setObjectName(u"cmbGridSpectChoice")

        self.horizontalLayout_2.addWidget(self.cmbGridSpectChoice)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_9)

        self.lblColorPalGrid = QLabel(self.wgtGridBiasControls)
        self.lblColorPalGrid.setObjectName(u"lblColorPalGrid")

        self.horizontalLayout_2.addWidget(self.lblColorPalGrid)

        self.cmbGridColorPal = QComboBox(self.wgtGridBiasControls)
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.addItem("")
        self.cmbGridColorPal.setObjectName(u"cmbGridColorPal")

        self.horizontalLayout_2.addWidget(self.cmbGridColorPal)

        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_10)


        self.verticalLayout_16.addWidget(self.wgtGridBiasControls)

        self.wgtGridSave = QWidget(self.wgtScanGrid)
        self.wgtGridSave.setObjectName(u"wgtGridSave")
        self.horizontalLayout_26 = QHBoxLayout(self.wgtGridSave)
        self.horizontalLayout_26.setSpacing(3)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_26.setContentsMargins(3, 3, 3, 3)
        self.cmdGridSave = QPushButton(self.wgtGridSave)
        self.cmdGridSave.setObjectName(u"cmdGridSave")

        self.horizontalLayout_26.addWidget(self.cmdGridSave)

        self.leGridFilename = QLineEdit(self.wgtGridSave)
        self.leGridFilename.setObjectName(u"leGridFilename")

        self.horizontalLayout_26.addWidget(self.leGridFilename)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_26.addItem(self.horizontalSpacer_11)


        self.verticalLayout_16.addWidget(self.wgtGridSave)

        self.progressBar = QProgressBar(self.wgtScanGrid)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.verticalLayout_16.addWidget(self.progressBar)


        self.verticalLayout_17.addWidget(self.wgtScanGrid)

        self.tabWidget.addTab(self.tbGridSpectro, "")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_20 = QVBoxLayout(self.tab)
        self.verticalLayout_20.setSpacing(3)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(3, 3, 3, 3)
        self.pltNoise = QWidget(self.tab)
        self.pltNoise.setObjectName(u"pltNoise")
        sizePolicy7.setHeightForWidth(self.pltNoise.sizePolicy().hasHeightForWidth())
        self.pltNoise.setSizePolicy(sizePolicy7)

        self.verticalLayout_20.addWidget(self.pltNoise)

        self.wgtNoise = QWidget(self.tab)
        self.wgtNoise.setObjectName(u"wgtNoise")
        self.horizontalLayout_33 = QHBoxLayout(self.wgtNoise)
        self.horizontalLayout_33.setSpacing(3)
        self.horizontalLayout_33.setObjectName(u"horizontalLayout_33")
        self.horizontalLayout_33.setContentsMargins(3, 3, 3, 3)
        self.cmdNoiseScan = QPushButton(self.wgtNoise)
        self.cmdNoiseScan.setObjectName(u"cmdNoiseScan")

        self.horizontalLayout_33.addWidget(self.cmdNoiseScan)

        self.lblXResNoise = QLabel(self.wgtNoise)
        self.lblXResNoise.setObjectName(u"lblXResNoise")

        self.horizontalLayout_33.addWidget(self.lblXResNoise)

        self.spnNoiseX = QSpinBox(self.wgtNoise)
        self.spnNoiseX.setObjectName(u"spnNoiseX")
        self.spnNoiseX.setMinimum(16)
        self.spnNoiseX.setMaximum(512)
        self.spnNoiseX.setSingleStep(16)
        self.spnNoiseX.setValue(256)

        self.horizontalLayout_33.addWidget(self.spnNoiseX)

        self.lblYResNoise = QLabel(self.wgtNoise)
        self.lblYResNoise.setObjectName(u"lblYResNoise")

        self.horizontalLayout_33.addWidget(self.lblYResNoise)

        self.spnNoiseY = QSpinBox(self.wgtNoise)
        self.spnNoiseY.setObjectName(u"spnNoiseY")
        self.spnNoiseY.setMinimum(16)
        self.spnNoiseY.setMaximum(512)
        self.spnNoiseY.setSingleStep(16)
        self.spnNoiseY.setValue(256)

        self.horizontalLayout_33.addWidget(self.spnNoiseY)

        self.lblSamplesNoise = QLabel(self.wgtNoise)
        self.lblSamplesNoise.setObjectName(u"lblSamplesNoise")

        self.horizontalLayout_33.addWidget(self.lblSamplesNoise)

        self.spnNoiseSamples = QSpinBox(self.wgtNoise)
        self.spnNoiseSamples.setObjectName(u"spnNoiseSamples")
        self.spnNoiseSamples.setMinimum(1)
        self.spnNoiseSamples.setMaximum(100)
        self.spnNoiseSamples.setValue(10)

        self.horizontalLayout_33.addWidget(self.spnNoiseSamples)

        self.lblNoiseDelay = QLabel(self.wgtNoise)
        self.lblNoiseDelay.setObjectName(u"lblNoiseDelay")

        self.horizontalLayout_33.addWidget(self.lblNoiseDelay)

        self.spnNoiseDelay = QSpinBox(self.wgtNoise)
        self.spnNoiseDelay.setObjectName(u"spnNoiseDelay")
        self.spnNoiseDelay.setMaximum(500)
        self.spnNoiseDelay.setValue(10)

        self.horizontalLayout_33.addWidget(self.spnNoiseDelay)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_33.addItem(self.horizontalSpacer_2)


        self.verticalLayout_20.addWidget(self.wgtNoise)

        self.tabWidget.addTab(self.tab, "")

        self.horizontalLayout_21.addWidget(self.tabWidget)


        self.retranslateUi(Widget)

        self.tbLeft.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Widget", None))
        self.cmdOpen.setText(QCoreApplication.translate("Widget", u"Open", None))
        self.cmdReset.setText(QCoreApplication.translate("Widget", u"Reset", None))
        self.cmdClear.setText(QCoreApplication.translate("Widget", u"Clear", None))
        self.lePort.setText(QCoreApplication.translate("Widget", u"/dev/ttyACM0", None))
        self.lblBias_2.setText(QCoreApplication.translate("Widget", u"DACX", None))
        self.lblDACXVal.setText(QCoreApplication.translate("Widget", u":", None))
        self.lblDACY.setText(QCoreApplication.translate("Widget", u"DACY", None))
        self.lblDACYVal.setText(QCoreApplication.translate("Widget", u":", None))
        self.lblDACZ.setText(QCoreApplication.translate("Widget", u"DACZ", None))
        self.lblDACZVal.setText(QCoreApplication.translate("Widget", u":", None))
        self.cmdSetDAC.setText(QCoreApplication.translate("Widget", u"Set All DAC", None))
        self.cmdSendBias.setText(QCoreApplication.translate("Widget", u"Set Bias", None))
        self.lblBias.setText(QCoreApplication.translate("Widget", u"Sample Bias  ", None))
        self.lblBiasVal.setText(QCoreApplication.translate("Widget", u":", None))
        self.cmdApproach.setText(QCoreApplication.translate("Widget", u"Approach", None))
        self.cmdStop.setText(QCoreApplication.translate("Widget", u"Stop", None))
        self.leTargetDAC.setText(QCoreApplication.translate("Widget", u"500", None))
        self.leSteps.setText(QCoreApplication.translate("Widget", u"1", None))
        self.lbXSettle.setText(QCoreApplication.translate("Widget", u"X Settle", None))
        self.spnXSettle.setSuffix(QCoreApplication.translate("Widget", u" uS", None))
        self.lblYSettle.setText(QCoreApplication.translate("Widget", u"Y Settle", None))
        self.spnYSettle.setSuffix(QCoreApplication.translate("Widget", u" uS", None))
        self.lblZSettle.setText(QCoreApplication.translate("Widget", u"Z Settle", None))
        self.spnZSettle.setSuffix(QCoreApplication.translate("Widget", u" uS", None))
        self.lblBiasSettle.setText(QCoreApplication.translate("Widget", u"Bias Settle", None))
        self.spnBiasSettle.setSuffix(QCoreApplication.translate("Widget", u" uS", None))
        self.cmdSettle.setText(QCoreApplication.translate("Widget", u"Settle", None))
        self.tbLeft.setTabText(self.tbLeft.indexOf(self.tbConfiguration), QCoreApplication.translate("Widget", u"Configuraton", None))
        self.grpScan.setTitle(QCoreApplication.translate("Widget", u"Scanning", None))
        self.lblBlank_2.setText("")
        self.lblStart.setText(QCoreApplication.translate("Widget", u"Start", None))
        self.lblEnd.setText(QCoreApplication.translate("Widget", u"End", None))
        self.lblRes.setText(QCoreApplication.translate("Widget", u"Pixel Res", None))
        self.lblXScan.setText(QCoreApplication.translate("Widget", u" X: ", None))
        self.leXStart.setText(QCoreApplication.translate("Widget", u"10000", None))
        self.leXEnd.setText(QCoreApplication.translate("Widget", u"50000", None))
        self.leXRes.setText(QCoreApplication.translate("Widget", u"256", None))
        self.lblYScan.setText(QCoreApplication.translate("Widget", u" Y: ", None))
        self.leYStart.setText(QCoreApplication.translate("Widget", u"10000", None))
        self.leYEnd.setText(QCoreApplication.translate("Widget", u"50000", None))
        self.leYRes.setText(QCoreApplication.translate("Widget", u"256", None))
        self.pushButton.setText(QCoreApplication.translate("Widget", u"Set PID", None))
        self.lblKp.setText(QCoreApplication.translate("Widget", u"Kp", None))
        self.leKp.setText(QCoreApplication.translate("Widget", u"0.0001", None))
        self.lblKi.setText(QCoreApplication.translate("Widget", u"Ki", None))
        self.leKi.setText(QCoreApplication.translate("Widget", u"0.0001", None))
        self.lblKd.setText(QCoreApplication.translate("Widget", u"Kd", None))
        self.leKd.setText(QCoreApplication.translate("Widget", u"0", None))
        self.chkConstCurrent.setText(QCoreApplication.translate("Widget", u"Constant Current", None))
        self.lblCCTarget.setText(QCoreApplication.translate("Widget", u"Target", None))
        self.leCCVal.setText(QCoreApplication.translate("Widget", u"10", None))
        self.cmdScan.setText(QCoreApplication.translate("Widget", u"Scan", None))
        self.lblscanSPP.setText(QCoreApplication.translate("Widget", u"Samples / Pix", None))
        self.leSamples.setText(QCoreApplication.translate("Widget", u"10", None))
        self.cmdScanMulti.setText(QCoreApplication.translate("Widget", u"Scan Multi ", None))
        self.lblRepeat.setText(QCoreApplication.translate("Widget", u"Repeat", None))
        self.leMultiScanTimes.setText(QCoreApplication.translate("Widget", u"10", None))
        self.cmdSaveScan.setText(QCoreApplication.translate("Widget", u"Save", None))
        self.leSave.setText(QCoreApplication.translate("Widget", u"./images/image", None))
        self.tbLeft.setTabText(self.tbLeft.indexOf(self.tbScanning), QCoreApplication.translate("Widget", u"Scanning", None))
        self.lblMotor.setText(QCoreApplication.translate("Widget", u"Motor", None))
        self.cmbMotDir.setItemText(0, QCoreApplication.translate("Widget", u"Forward", None))
        self.cmbMotDir.setItemText(1, QCoreApplication.translate("Widget", u"Reverse", None))

        self.cmdMotOff.setText(QCoreApplication.translate("Widget", u"Off", None))
#if QT_CONFIG(tooltip)
        self.cmdMotDown.setToolTip(QCoreApplication.translate("Widget", u"Move tip away from target", None))
#endif // QT_CONFIG(tooltip)
        self.cmdMotDown.setText(QCoreApplication.translate("Widget", u"Down", None))
#if QT_CONFIG(tooltip)
        self.cmdMotUp.setToolTip(QCoreApplication.translate("Widget", u"Move tip close to target", None))
#endif // QT_CONFIG(tooltip)
        self.cmdMotUp.setText(QCoreApplication.translate("Widget", u"Up", None))
        self.cmdSend.setText(QCoreApplication.translate("Widget", u"Send", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Color Palette : ", None))
        self.cmbColorPal.setItemText(0, QCoreApplication.translate("Widget", u"viridis", None))
        self.cmbColorPal.setItemText(1, QCoreApplication.translate("Widget", u"inferno", None))
        self.cmbColorPal.setItemText(2, QCoreApplication.translate("Widget", u"magma", None))
        self.cmbColorPal.setItemText(3, QCoreApplication.translate("Widget", u"plasma", None))
        self.cmbColorPal.setItemText(4, QCoreApplication.translate("Widget", u"turbo", None))
        self.cmbColorPal.setItemText(5, QCoreApplication.translate("Widget", u"gray", None))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tbMain), QCoreApplication.translate("Widget", u"Main", None))
        self.cmdScanIV.setText(QCoreApplication.translate("Widget", u"Plot IV", None))
        self.leIVStart.setText(QCoreApplication.translate("Widget", u"0", None))
        self.leIVEnd.setText(QCoreApplication.translate("Widget", u"65535", None))
        self.leIVStep.setText(QCoreApplication.translate("Widget", u"10", None))
        self.cmdSaveIV.setText(QCoreApplication.translate("Widget", u"Save", None))
        self.leIVFilename.setText(QCoreApplication.translate("Widget", u"./images/IVCurve", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tbIV), QCoreApplication.translate("Widget", u"dI/dV Curve", None))
        self.cmdScandIdZ.setText(QCoreApplication.translate("Widget", u"Plot dI/dZ", None))
        self.ledIdZStart.setText(QCoreApplication.translate("Widget", u"0", None))
        self.ledIdZEnd.setText(QCoreApplication.translate("Widget", u"65535", None))
        self.ledIdZStep.setText(QCoreApplication.translate("Widget", u"10", None))
        self.cmdSaveIV_2.setText(QCoreApplication.translate("Widget", u"Save", None))
        self.leIVFilename_2.setText(QCoreApplication.translate("Widget", u"./images/dIdVCurve", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tbdIdZ), QCoreApplication.translate("Widget", u"dI/dZ Curve", None))
        self.lblGridBias.setText(QCoreApplication.translate("Widget", u"Bias", None))
        self.cmdGridSpectro.setText(QCoreApplication.translate("Widget", u"Plot Bias", None))
        self.leGridBiasStart.setText(QCoreApplication.translate("Widget", u"0", None))
        self.leGridBiasEnd.setText(QCoreApplication.translate("Widget", u"65535", None))
        self.leGridBiasPoints.setText(QCoreApplication.translate("Widget", u"100", None))
        self.cmbGridSpectChoice.setItemText(0, QCoreApplication.translate("Widget", u"dI / dV", None))
        self.cmbGridSpectChoice.setItemText(1, QCoreApplication.translate("Widget", u"dI / dZ", None))

        self.lblColorPalGrid.setText(QCoreApplication.translate("Widget", u"Color Palette : ", None))
        self.cmbGridColorPal.setItemText(0, QCoreApplication.translate("Widget", u"viridis", None))
        self.cmbGridColorPal.setItemText(1, QCoreApplication.translate("Widget", u"inferno", None))
        self.cmbGridColorPal.setItemText(2, QCoreApplication.translate("Widget", u"magma", None))
        self.cmbGridColorPal.setItemText(3, QCoreApplication.translate("Widget", u"plasma", None))
        self.cmbGridColorPal.setItemText(4, QCoreApplication.translate("Widget", u"turbo", None))
        self.cmbGridColorPal.setItemText(5, QCoreApplication.translate("Widget", u"gray", None))

        self.cmdGridSave.setText(QCoreApplication.translate("Widget", u"Save", None))
        self.leGridFilename.setText(QCoreApplication.translate("Widget", u"./images/GridSpectroscopy", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tbGridSpectro), QCoreApplication.translate("Widget", u"grid spectroscopy", None))
        self.cmdNoiseScan.setText(QCoreApplication.translate("Widget", u"Noise Scan", None))
        self.lblXResNoise.setText(QCoreApplication.translate("Widget", u"X Res", None))
        self.lblYResNoise.setText(QCoreApplication.translate("Widget", u"Y Res", None))
        self.lblSamplesNoise.setText(QCoreApplication.translate("Widget", u"# Samples", None))
        self.lblNoiseDelay.setText(QCoreApplication.translate("Widget", u"Delay", None))
        self.spnNoiseDelay.setSuffix(QCoreApplication.translate("Widget", u" uS", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("Widget", u"Noise Scan", None))
    # retranslateUi

