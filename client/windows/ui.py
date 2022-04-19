from PyQt6 import QtCore, QtGui, QtWidgets
import time


class Worker(QtCore.QObject):
    def __init__(self):
        self.func = None
        super().__init__()
    def run(self):
        while True:
            self.func()
            time.sleep(0.4)
    
class EventLoop(QtCore.QObject):
    def __init__(self):
        self.func = None
        super().__init__()
    def run(self):
        while True:
            self.func()


class ListView(QtWidgets.QListWidget):
    def addItem(self, elm) -> None:
        super().addItem(elm)
        super().verticalScrollBar().setValue(super().verticalScrollBar().maximum())
        # item = super().item(super().count())
        # scroll_hint = QtWidgets.QAbstractItemView.ScrollHint.PositionAtTop
        # super().scrollToItem(item,scroll_hint)
        # print('dd')
        # super().scrollToItem(item,scroll_hint)
    
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(924, 741)
        self.MainWindow = MainWindow
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.listView = QtWidgets.QListWidget(self.centralwidget)
        self.listView.setGeometry(QtCore.QRect(40, 110, 311, 461))
        self.listView.setObjectName("listView")
        # self.listWidget = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget = ListView(self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(370, 110, 501, 471))
        self.listWidget.setObjectName("listWidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(370, 10, 501, 61))
        font = QtGui.QFont()
        font.setFamily("MS Shell Dlg 2")
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.label.setObjectName("label")
        self.textEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.textEdit.setGeometry(QtCore.QRect(370, 596, 411, 87))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.textEdit.setFont(font)
        self.textEdit.setObjectName("textEdit")
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(60, 70, 191, 22))
        self.lineEdit.setObjectName("lineEdit")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(260, 70, 93, 28))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(50, 650, 93, 28))
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_3.setGeometry(QtCore.QRect(370, 80, 93, 28))
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_4.setGeometry(QtCore.QRect(780, 593, 93, 91))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.listView.setFont(font)
        self.listWidget.setFont(font)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName("pushButton_4")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(600, 70, 271, 31))
        font = QtGui.QFont()
        font.setPointSize(13)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 924, 26))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def scroll_to_bottom(self):
        lastIndex = self.listWidget.count()
        item = self.listWidget.item(lastIndex-1)
        self.listWidget.scrollToItem(item)
        # self.listWidget.scrollToItem(item, QtGui.QAbstractItemView.PositionAtTop)
        # self.listWidget.selectRow(lastIndex)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label.setText(_translate(
            "MainWindow", ""))
        self.pushButton.setText(_translate("MainWindow", "Add Contact"))
        self.pushButton_2.setText(_translate("MainWindow", "Settings"))
        self.pushButton_3.setText(_translate("MainWindow", "block"))
        self.pushButton_4.setText(_translate("MainWindow", "Send"))
        self.label_2.setText(_translate("MainWindow", ""))
        self.reloadshortcut = QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+r'), MainWindow)
    
        self.listWidget.setWordWrap(True)
        self.listWidget.setAutoScroll(True)
        self.listWidget.setAutoScrollMargin(1) 
        self.thread = QtCore.QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)


        self.thread2 = QtCore.QThread()
        self.eventworker = EventLoop()
        self.eventworker.moveToThread(self.thread2)
        self.thread2.started.connect(self.eventworker.run)

       
        self.label.setAlignment( QtCore.Qt.AlignmentFlag.AlignCenter)


def get_window():
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()

    
    ui.setupUi(MainWindow)
    return MainWindow, ui


def message_box(title,message,mainwindow):
    msg = QtWidgets.QMessageBox(mainwindow)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec()


def question_box(title,message,mainwindow):
    msgbox = QtWidgets.QMessageBox(mainwindow)
    msgbox.windowTitle = title
    msgbox.setText(message)

    msgbox.addButton(QtWidgets.QMessageBox.StandardButton.Yes)
    msgbox.addButton(QtWidgets.QMessageBox.StandardButton.No)
    msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)

    ans = msgbox.exec()
    if ans == QtWidgets.QMessageBox.StandardButton.Yes:
        return True
    return False