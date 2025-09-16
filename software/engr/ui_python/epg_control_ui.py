# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'epg_control.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PyQt6.QtGui import (
    QAction
)
from PyQt6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSlider, QStatusBar,
    QVBoxLayout, QWidget)

    
class Ui_EPGControl(object):
    def setupUi(self, EPGControl):
        if not EPGControl.objectName():
            EPGControl.setObjectName(u"EPGControl")
        screen = QApplication.primaryScreen()
        size = screen.size()
        w = size.width()
        h = size.height()
        EPGControl.resize(800, 400)
        self.centralWidget = QWidget(EPGControl)
        self.centralWidget.setObjectName(u"centralWidget")
        self.verticalLayoutWidget = QWidget(self.centralWidget)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(0, 20, int(0.18*w), int(0.5*h)))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        # MUX

        self.inputResistance = QHBoxLayout()
        self.inputResistance.setObjectName(u"inputResistance")
        self.inputResistance.setContentsMargins(-1, -1, 0, -1)
        self.inputResistanceTitle = QLabel(self.verticalLayoutWidget)
        self.inputResistanceTitle.setObjectName(u"inputResistanceTitle")

        self.inputResistance.addWidget(self.inputResistanceTitle)

        self.inputResistanceInput = QComboBox(self.verticalLayoutWidget)
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.addItem("")
        self.inputResistanceInput.setObjectName(u"inputResistanceInput")

        self.inputResistance.addWidget(self.inputResistanceInput)

        self.inputResistanceUnit = QLabel(self.verticalLayoutWidget)
        self.inputResistanceUnit.setObjectName(u"inputResistanceUnit")

        self.inputResistance.addWidget(self.inputResistanceUnit)


        self.verticalLayout.addLayout(self.inputResistance)

        # PGA 1 Slider:
        self.pga1 = QHBoxLayout()
        self.pga1.setObjectName(u"PGA 1")
        self.pga1.setContentsMargins(-1, -1, 0, -1)
        self.pga1Title = QLabel(self.verticalLayoutWidget)
        self.pga1Title.setObjectName(u"PGA1Title")

        self.pga1.addWidget(self.pga1Title)

        self.pga1Slider = QSlider(self.verticalLayoutWidget)
        self.pga1Slider.setObjectName(u"PGA1Slider")
        self.pga1Slider.setMinimum(0)
        self.pga1Slider.setMaximum(7)
        self.pga1Slider.setOrientation(Qt.Orientation.Horizontal)

        self.pga1.addWidget(self.pga1Slider)

        self.pga1Input = QLineEdit(self.verticalLayoutWidget)
        self.pga1Input.setObjectName(u"PGA1Input")
        self.pga1Input.setEnabled(True)
        self.pga1Input.setMaximumSize(QSize(50, 16777215))
        self.pga1Input.setMouseTracking(False)
        self.pga1Input.setMaxLength(32767)

        self.pga1.addWidget(self.pga1Input)

        self.pga1Unit = QLabel(self.verticalLayoutWidget)
        self.pga1Unit.setObjectName(u"PGA1Unit")

        self.pga1.addWidget(self.pga1Unit)


        self.verticalLayout.addLayout(self.pga1)

        # PGA 2 Slider:

        self.pga2 = QHBoxLayout()
        self.pga2.setObjectName(u"PGA 2")
        self.pga2.setContentsMargins(-1, -1, 0, -1)
        self.pga2Title = QLabel(self.verticalLayoutWidget)
        self.pga2Title.setObjectName(u"PGA2Title")

        self.pga2.addWidget(self.pga2Title)

        self.pga2Slider = QSlider(self.verticalLayoutWidget)
        self.pga2Slider.setObjectName(u"PGA2Slider")
        self.pga2Slider.setMinimum(0)
        self.pga2Slider.setMaximum(7)
        self.pga2Slider.setOrientation(Qt.Orientation.Horizontal)

        self.pga2.addWidget(self.pga2Slider)

        self.pga2Input = QLineEdit(self.verticalLayoutWidget)
        self.pga2Input.setObjectName(u"PGA2Input")
        self.pga2Input.setEnabled(True)
        self.pga2Input.setMaximumSize(QSize(50, 16777215))
        self.pga2Input.setMouseTracking(False)
        self.pga2Input.setMaxLength(32767)

        self.pga2.addWidget(self.pga2Input)

        self.pga2Unit = QLabel(self.verticalLayoutWidget)
        self.pga2Unit.setObjectName(u"PGA2Unit")

        self.pga2.addWidget(self.pga2Unit)


        self.verticalLayout.addLayout(self.pga2)
    

        # SCA Slider:

        self.sca = QHBoxLayout()
        self.sca.setObjectName(u"SCA")
        self.sca.setContentsMargins(-1, -1, 0, -1)
        self.scaTitle = QLabel(self.verticalLayoutWidget)
        self.scaTitle.setObjectName(u"SCATitle")

        self.sca.addWidget(self.scaTitle)

        self.scaSlider = QSlider(self.verticalLayoutWidget)
        self.scaSlider.setObjectName(u"SCASlider")
        self.scaSlider.setMinimum(2)
        self.scaSlider.setMaximum(7000)
        self.scaSlider.setOrientation(Qt.Orientation.Horizontal)

        self.sca.addWidget(self.scaSlider)

        self.scaInput = QLineEdit(self.verticalLayoutWidget)
        self.scaInput.setObjectName(u"SCAInput")
        self.scaInput.setEnabled(True)
        self.scaInput.setMaximumSize(QSize(50, 16777215))
        self.scaInput.setMouseTracking(False)
        self.scaInput.setMaxLength(32767)

        self.sca.addWidget(self.scaInput)

        self.scaUnit = QLabel(self.verticalLayoutWidget)
        self.scaUnit.setObjectName(u"scaUnit")

        self.sca.addWidget(self.scaUnit)


        self.verticalLayout.addLayout(self.sca)

        # SCO Slider:

        self.sco = QHBoxLayout()
        self.sco.setObjectName(u"SCO")
        self.scoTitle = QLabel(self.verticalLayoutWidget)
        self.scoTitle.setObjectName(u"SCOTitle")

        self.sco.addWidget(self.scoTitle)

        self.scoSlider = QSlider(self.verticalLayoutWidget)
        self.scoSlider.setObjectName(u"SCOSlider")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scoSlider.sizePolicy().hasHeightForWidth())
        self.scoSlider.setSizePolicy(sizePolicy)
        self.scoSlider.setMinimum(-33)
        self.scoSlider.setMaximum(33)
        self.scoSlider.setSingleStep(0)
        self.scoSlider.setOrientation(Qt.Orientation.Horizontal)

        self.sco.addWidget(self.scoSlider)

        self.scoInput = QLineEdit(self.verticalLayoutWidget)
        self.scoInput.setObjectName(u"SCOInput")
        self.scoInput.setEnabled(True)
        self.scoInput.setMaximumSize(QSize(50, 16777215))
        self.scoInput.setMouseTracking(False)
        self.scoInput.setMaxLength(32767)

        self.sco.addWidget(self.scoInput)

        self.scoUnit = QLabel(self.verticalLayoutWidget)
        self.scoUnit.setObjectName(u"SCOUnit")

        self.sco.addWidget(self.scoUnit)


        self.verticalLayout.addLayout(self.sco)

        # DDSO Slider:

        self.ddso = QHBoxLayout()
        self.ddso.setObjectName(u"DDSO")
        self.ddsoTitle = QLabel(self.verticalLayoutWidget)
        self.ddsoTitle.setObjectName(u"DDSOTitle")

        self.ddso.addWidget(self.ddsoTitle)

        self.ddsoSlider = QSlider(self.verticalLayoutWidget)
        self.ddsoSlider.setObjectName(u"DDSOSlider")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ddsoSlider.sizePolicy().hasHeightForWidth())
        self.ddsoSlider.setSizePolicy(sizePolicy)
        self.ddsoSlider.setMinimum(-100)
        self.ddsoSlider.setMaximum(100)
        self.ddsoSlider.setSingleStep(0)
        self.ddsoSlider.setOrientation(Qt.Orientation.Horizontal)

        self.ddso.addWidget(self.ddsoSlider)

        self.ddsoInput = QLineEdit(self.verticalLayoutWidget)
        self.ddsoInput.setObjectName(u"DDSOInput")
        self.ddsoInput.setEnabled(True)
        self.ddsoInput.setMaximumSize(QSize(50, 16777215))
        self.ddsoInput.setMouseTracking(False)
        self.ddsoInput.setMaxLength(32767)

        self.ddso.addWidget(self.ddsoInput)

        self.ddsoUnit = QLabel(self.verticalLayoutWidget)
        self.ddsoUnit.setObjectName(u"DDSOUnit")

        self.ddso.addWidget(self.ddsoUnit)


        self.verticalLayout.addLayout(self.ddso)

        # DDSA SLider:


        self.ddsa = QHBoxLayout()
        self.ddsa.setObjectName(u"DDSA")
        self.ddsaTitle = QLabel(self.verticalLayoutWidget)
        self.ddsaTitle.setObjectName(u"DDSATitle")

        self.ddsa.addWidget(self.ddsaTitle)

        self.ddsaSlider = QSlider(self.verticalLayoutWidget)
        self.ddsaSlider.setObjectName(u"DDSASlider")
        self.ddsaSlider.setMinimum(-500)
        self.ddsaSlider.setMaximum(-1)
        self.ddsaSlider.setOrientation(Qt.Orientation.Horizontal)

        self.ddsa.addWidget(self.ddsaSlider)

        self.ddsaInput = QLineEdit(self.verticalLayoutWidget)
        self.ddsaInput.setObjectName(u"DDSAInput")
        self.ddsaInput.setEnabled(True)
        self.ddsaInput.setMaximumSize(QSize(50, 16777215))
        self.ddsaInput.setMouseTracking(False)
        self.ddsaInput.setMaxLength(32767)

        self.ddsa.addWidget(self.ddsaInput)

        self.ddsaUnit = QLabel(self.verticalLayoutWidget)
        self.ddsaUnit.setObjectName(u"DDSAUnit")

        self.ddsa.addWidget(self.ddsaUnit)


        self.verticalLayout.addLayout(self.ddsa)

        # Digipot 1 Slider:

        self.d0 = QHBoxLayout()
        self.d0.setObjectName(u"D0")
        self.d0Title = QLabel(self.verticalLayoutWidget)
        self.d0Title.setObjectName(u"D0Title")

        self.d0.addWidget(self.d0Title)

        self.d0Slider = QSlider(self.verticalLayoutWidget)
        self.d0Slider.setObjectName(u"D0Slider")
        self.d0Slider.setMinimum(0)
        self.d0Slider.setMaximum(255)
        self.d0Slider.setOrientation(Qt.Orientation.Horizontal)

        self.d0.addWidget(self.d0Slider)

        self.d0Input = QLineEdit(self.verticalLayoutWidget)
        self.d0Input.setObjectName(u"D0Input")
        self.d0Input.setEnabled(True)
        self.d0Input.setMaximumSize(QSize(50, 16777215))
        self.d0Input.setMouseTracking(False)
        self.d0Input.setMaxLength(32767)

        self.d0.addWidget(self.d0Input)

        self.d0Unit = QLabel(self.verticalLayoutWidget)
        self.d0Unit.setObjectName(u"D0Unit")

        self.d0.addWidget(self.d0Unit)


        self.verticalLayout.addLayout(self.d0)

        # Digipot 2 Slider:

        self.d1 = QHBoxLayout()
        self.d1.setObjectName(u"D1")
        self.d1Title = QLabel(self.verticalLayoutWidget)
        self.d1Title.setObjectName(u"D1Title")

        self.d1.addWidget(self.d1Title)

        self.d1Slider = QSlider(self.verticalLayoutWidget)
        self.d1Slider.setObjectName(u"D1Slider")
        self.d1Slider.setMinimum(1)
        self.d1Slider.setMaximum(125)
        self.d1Slider.setOrientation(Qt.Orientation.Horizontal)

        self.d1.addWidget(self.d1Slider)

        self.d1Input = QLineEdit(self.verticalLayoutWidget)
        self.d1Input.setObjectName(u"D1Input")
        self.d1Input.setEnabled(True)
        self.d1Input.setMaximumSize(QSize(50, 16777215))
        self.d1Input.setMouseTracking(False)
        self.d1Input.setMaxLength(32767)

        self.d1.addWidget(self.d1Input)

        self.d1Unit = QLabel(self.verticalLayoutWidget)
        self.d1Unit.setObjectName(u"D1Unit")

        self.d1.addWidget(self.d1Unit)


        self.verticalLayout.addLayout(self.d1)

        # Digipot 3 Slider:

        self.d2 = QHBoxLayout()
        self.d2.setObjectName(u"D2")
        self.d2Title = QLabel(self.verticalLayoutWidget)
        self.d2Title.setObjectName(u"D2Title")

        self.d2.addWidget(self.d2Title)

        self.d2Slider = QSlider(self.verticalLayoutWidget)
        self.d2Slider.setObjectName(u"D2Slider")
        self.d2Slider.setMinimum(0)
        self.d2Slider.setMaximum(255)
        self.d2Slider.setOrientation(Qt.Orientation.Horizontal)

        self.d2.addWidget(self.d2Slider)

        self.d2Input = QLineEdit(self.verticalLayoutWidget)
        self.d2Input.setObjectName(u"D2Input")
        self.d2Input.setEnabled(True)
        self.d2Input.setMaximumSize(QSize(50, 16777215))
        self.d2Input.setMouseTracking(False)
        self.d2Input.setMaxLength(32767)

        self.d2.addWidget(self.d2Input)

        self.d2Unit = QLabel(self.verticalLayoutWidget)
        self.d2Unit.setObjectName(u"D2Unit")

        self.d2.addWidget(self.d2Unit)


        self.verticalLayout.addLayout(self.d2)

        # Digipot 4 Slider:

        self.d3 = QHBoxLayout()
        self.d3.setObjectName(u"D3")
        self.d3Title = QLabel(self.verticalLayoutWidget)
        self.d3Title.setObjectName(u"D3Title")

        self.d3.addWidget(self.d3Title)

        self.d3Slider = QSlider(self.verticalLayoutWidget)
        self.d3Slider.setObjectName(u"D3Slider")
        self.d3Slider.setMinimum(0)
        self.d3Slider.setMaximum(255)
        self.d3Slider.setOrientation(Qt.Orientation.Horizontal)

        self.d3.addWidget(self.d3Slider)

        self.d3Input = QLineEdit(self.verticalLayoutWidget)
        self.d3Input.setObjectName(u"D3Input")
        self.d3Input.setEnabled(True)
        self.d3Input.setMaximumSize(QSize(50, 16777215))
        self.d3Input.setMouseTracking(False)
        self.d3Input.setMaxLength(32767)

        self.d3.addWidget(self.d3Input)

        self.d3Unit = QLabel(self.verticalLayoutWidget)
        self.d3Unit.setObjectName(u"D3Unit")

        self.d3.addWidget(self.d3Unit)


        self.verticalLayout.addLayout(self.d3)

        # Frequency:

        self.excitationFrequency = QHBoxLayout()
        self.excitationFrequency.setObjectName(u"excitationFrequency")
        self.excitationFrequencyTitle = QLabel(self.verticalLayoutWidget)
        self.excitationFrequencyTitle.setObjectName(u"excitationFrequencyTitle")

        self.excitationFrequency.addWidget(self.excitationFrequencyTitle)

        self.excitationFrequencyInput = QComboBox(self.verticalLayoutWidget)
        self.excitationFrequencyInput.addItem("")
        self.excitationFrequencyInput.addItem("")
        self.excitationFrequencyInput.addItem("")
        self.excitationFrequencyInput.setObjectName(u"excitationFrequencyInput")

        self.excitationFrequency.addWidget(self.excitationFrequencyInput)

        self.excitationFrequencyUnit = QLabel(self.verticalLayoutWidget)
        self.excitationFrequencyUnit.setObjectName(u"excitationFrequencyUnit")

        self.excitationFrequency.addWidget(self.excitationFrequencyUnit)


        self.verticalLayout.addLayout(self.excitationFrequency)


        # ON Button:
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.onBtn = QPushButton(self.verticalLayoutWidget)
        self.onBtn.setObjectName(u"ONBtn")

        self.horizontalLayout_4.addWidget(self.onBtn)

        # START Button:
        self.startBtn = QPushButton(self.verticalLayoutWidget)
        self.startBtn.setObjectName(u"STARTBtn")

        self.horizontalLayout_4.addWidget(self.startBtn)

        # OFF Button:
        self.offBtn = QPushButton(self.verticalLayoutWidget)
        self.offBtn.setObjectName(u"OFFBtn")

        self.horizontalLayout_4.addWidget(self.offBtn)
        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")

        self.revertToDefaultsBtn = QPushButton(self.verticalLayoutWidget)
        self.revertToDefaultsBtn.setObjectName(u"revertToDefaultsBtn")
       # self.revertToDefaultsBtn.setFixedWidth(200)

        self.horizontalLayout_5.addWidget(self.revertToDefaultsBtn)

        self.verticalLayout.addLayout(self.horizontalLayout_5)

        EPGControl.setCentralWidget(self.centralWidget)
        self.statusbar = QStatusBar(EPGControl)
        self.statusbar.setObjectName(u"statusbar")
        EPGControl.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(EPGControl)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 716, 21))
        self.menuChannel_1 = QMenu(self.menubar)
        self.menuChannel_1.setObjectName(u"menuChannel_1")
        EPGControl.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuChannel_1.menuAction())

        self.retranslateUi(EPGControl)

        QMetaObject.connectSlotsByName(EPGControl)
    # setupUi

    def retranslateUi(self, EPGControl):
        EPGControl.setWindowTitle(QCoreApplication.translate("EPGControl", u"MainWindow", None))
        self.inputResistanceTitle.setText(QCoreApplication.translate("EPGControl", u"Input Resistance      ", None))
        self.inputResistanceInput.setItemText(0, QCoreApplication.translate("EPGControl", u"100K", None))
        self.inputResistanceInput.setItemText(1, QCoreApplication.translate("EPGControl", u"1M", None))
        self.inputResistanceInput.setItemText(2, QCoreApplication.translate("EPGControl", u"10M", None))
        self.inputResistanceInput.setItemText(3, QCoreApplication.translate("EPGControl", u"100M", None))
        self.inputResistanceInput.setItemText(4, QCoreApplication.translate("EPGControl", u"1G", None))
        self.inputResistanceInput.setItemText(5, QCoreApplication.translate("EPGControl", u"10G", None))
        self.inputResistanceInput.setItemText(6, QCoreApplication.translate("EPGControl", u"SR", None))
        self.inputResistanceInput.setItemText(7, QCoreApplication.translate("EPGControl", u"1G Loopback", None))

        self.inputResistanceUnit.setText(QCoreApplication.translate("EPGControl", u"\u03a9", None))
        self.pga1Title.setText(QCoreApplication.translate("EPGControl", u"PGA 1          ", None))
        self.pga1Input.setText(QCoreApplication.translate("EPGControl", u"1", None))
        self.pga1Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.pga2Title.setText(QCoreApplication.translate("EPGControl", u"PGA 2          ", None))
        self.pga2Input.setText(QCoreApplication.translate("EPGControl", u"1", None))
        self.pga2Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.scaTitle.setText(QCoreApplication.translate("EPGControl", u"Signal Chain Amplification         ", None))
        self.scaInput.setText(QCoreApplication.translate("EPGControl", u"2", None))
        self.scaUnit.setText(QCoreApplication.translate("EPGControl", u"X", None))
        self.scoTitle.setText(QCoreApplication.translate("EPGControl", u"Signal Chain Offset         ", None))
        self.scoInput.setText(QCoreApplication.translate("EPGControl", u"6", None))
        self.scoUnit.setText(QCoreApplication.translate("EPGControl", u"0.1V", None))
        self.ddsoTitle.setText(QCoreApplication.translate("EPGControl", u"DDS Offset                     ", None))
        self.ddsoInput.setText(QCoreApplication.translate("EPGControl", u"-34", None))
        self.ddsoUnit.setText(QCoreApplication.translate("EPGControl", u"0.01V", None))
        self.ddsaTitle.setText(QCoreApplication.translate("EPGControl", u"DDS Amplification", None))
        self.ddsaInput.setText(QCoreApplication.translate("EPGControl", u"-100", None))
        self.ddsaUnit.setText(QCoreApplication.translate("EPGControl", u"0.01X", None))
        self.d0Title.setText(QCoreApplication.translate("EPGControl", u"Digipot Channel 0", None))
        self.d0Input.setText(QCoreApplication.translate("EPGControl", u"127", None))
        self.d0Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.d1Title.setText(QCoreApplication.translate("EPGControl", u"Digipot Channel 1", None))
        self.d1Input.setText(QCoreApplication.translate("EPGControl", u"127", None))
        self.d1Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.d2Title.setText(QCoreApplication.translate("EPGControl", u"Digipot Channel 2", None))
        self.d2Input.setText(QCoreApplication.translate("EPGControl", u"0", None))
        self.d2Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.d3Title.setText(QCoreApplication.translate("EPGControl", u"Digipot Channel 3", None))
        self.d3Input.setText(QCoreApplication.translate("EPGControl", u"0", None))
        self.d3Unit.setText(QCoreApplication.translate("EPGControl", u"", None))
        self.excitationFrequencyTitle.setText(QCoreApplication.translate("EPGControl", u"Excitation Frequency", None))
        self.excitationFrequencyInput.setItemText(0, QCoreApplication.translate("EPGControl", u"1000", None))
        self.excitationFrequencyInput.setItemText(1, QCoreApplication.translate("EPGControl", u"0", None))
        self.excitationFrequencyInput.setItemText(2, QCoreApplication.translate("EPGControl", u"1", None))

        self.excitationFrequencyUnit.setText(QCoreApplication.translate("EPGControl", u"Hz", None))
        self.onBtn.setText(QCoreApplication.translate("EPGControl", u"ON", None))
        self.startBtn.setText(QCoreApplication.translate("EPGControl", u"START", None))
        self.offBtn.setText(QCoreApplication.translate("EPGControl", u"OFF", None))
        self.revertToDefaultsBtn.setText(QCoreApplication.translate("EPGControl", u"Revert to Defaults", None))
        self.menuChannel_1.setTitle(QCoreApplication.translate("EPGControl", u"Channel 1", None))
    # retranslateUi

