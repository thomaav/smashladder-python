import sys
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QToolTip, QPushButton, QDesktopWidget, QLineEdit, QFormLayout
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QCoreApplication, QPoint, Qt
from smashladder import matchmaking_loop, challenge_loop
from smashladder_sockets import connect_to_smashladder
from smashladder_requests import login_to_smashladder
from local import *


BUTTON_SIZE_X = 100
BUTTON_SIZE_Y = 26


def move_widget(widget, x_center, y_center):
    qr = widget.frameGeometry()
    center = QPoint(x_center, y_center)
    qr.moveCenter(center)
    widget.move(qr.topLeft())


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()


    def initUI(self):
        self.setWindowTitle("Login")
        form_layout = QFormLayout()
        self.setLayout(form_layout)

        # center the widget on screen
        self.resize(200, 100)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # add username and password fields
        self.username_input = QLineEdit(self)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton('Log in')
        self.login_button.clicked.connect(self.login)
        self.login_button.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)

        form_layout.addRow('Username:', self.username_input)
        form_layout.addRow('Password:', self.password_input)
        form_layout.addRow(self.login_button)

        self.show()


    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not(username and password):
            # do nothing if no username or password supplied
            return

        login_to_smashladder(username, password)
        self.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()


    def initUI(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        self.setToolTip('This is a <b>QWidget</b> widget')

        # set-up window
        self.resize(500, 300)
        self.center()
        self.setWindowTitle('smashladder-python')
        self.setWindowIcon(QIcon('conf/smashladder.png'))

        # button to start all loops and matchmake
        mmbtn = QPushButton('Start matchmaking', self)
        mmbtn.clicked.connect(self.start_matchmaking)
        mmbtn.resize(mmbtn.sizeHint())
        x_center = 50 * (self.width() // 100)
        y_center = 5 * (self.height() // 100)
        mmbtn.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)
        move_widget(mmbtn, x_center, y_center)

        # log in button
        relog_button = QPushButton('Log in', self)
        x_center = 88 * (self.width() // 100)
        y_center = 30 * (self.height() // 100)
        relog_button.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)
        move_widget(relog_button, x_center, y_center)
        relog_button.clicked.connect(lambda: login_to_smashladder)

        # add high ping user
        high_ping_username = QLineEdit(self)
        x_center = 60 * (self.width() // 100)
        y_center = 50 * (self.height() // 100)
        move_widget(high_ping_username, x_center, y_center)

        high_ping_button = QPushButton('Add high ping user', self)
        x_center = 88 * (self.width() // 100)
        y_center = 50 * (self.height() // 100)
        high_ping_button.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)
        move_widget(high_ping_button, x_center, y_center - 5)

        # whitelist country
        whitelist_country = QLineEdit(self)
        x_center = 60 * (self.width() // 100)
        y_center = 70 * (self.height() // 100)
        move_widget(whitelist_country, x_center, y_center)

        whitelist_country_button = QPushButton('Whitelist country', self)
        x_center = 88 * (self.width() // 100)
        y_center = 70 * (self.height() // 100)
        whitelist_country_button.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)
        move_widget(whitelist_country_button, x_center, y_center - 5)

        # button to quit everything
        qbtn = QPushButton('Quit', self)
        qbtn.clicked.connect(QCoreApplication.instance().quit)
        qbtn.resize(qbtn.sizeHint())
        x_center = 50 * (self.width() // 100)
        y_center = 95 * (self.height() // 100)
        move_widget(qbtn, x_center, y_center)

        self.show()


    def start_matchmaking(self):
        matchmaking_thread = threading.Thread(target=matchmaking_loop, args=(cookie_jar,))
        matchmaking_thread.daemon = True
        challenge_thread = threading.Thread(target=challenge_loop, args=(cookie_jar,))
        challenge_thread.daemon = True
        main_socket_thread = threading.Thread(target=connect_to_smashladder, args=(cookie_jar,))
        main_socket_thread.daemon = True

        matchmaking_thread.start()
        challenge_thread.start()
        main_socket_thread.start()


    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


app = QApplication(sys.argv)
main_window = MainWindow()
login_window = LoginWindow()
