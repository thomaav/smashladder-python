import builtins
import local
import sys
import smashladder
import smashladder_requests
import threading
import os.path
from PyQt5.QtWidgets import QApplication, QWidget, QToolTip, QPushButton, \
    QDesktopWidget, QLineEdit, QFormLayout, QMainWindow, QLabel
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QCoreApplication, QPoint, Qt
from PyQt5 import uic

BUTTON_SIZE_X = 100
BUTTON_SIZE_Y = 26
MAIN_UI_FILE = 'conf/mainwindow.ui'

def qt_print(text):
    main_window.matchmaking_info.append(text)

# import here after initialization to receive it in smashladder_sockets
import smashladder_sockets


def qt_change_match_status(match_id, in_match):
    if in_match:
        main_window.in_match_value.setText('True: ' + match_id)
    else:
        main_window.in_match_value.setText('False')


def move_widget(widget, x_center, y_center):
    qr = widget.frameGeometry()
    center = QPoint(x_center, y_center)
    qr.moveCenter(center)
    widget.move(qr.topLeft())


class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.initUI()


    def initUI(self):
        self.setWindowTitle("Login")
        form_layout = QFormLayout()
        self.form_layout = form_layout
        self.setLayout(form_layout)

        # center the widget on screen
        self.setFixedSize(350, 110)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton('Log in')
        self.login_button.clicked.connect(self.login)
        self.login_button.resize(BUTTON_SIZE_X, BUTTON_SIZE_Y)

        self.login_status = QLabel("Logging in...")
        self.login_status.setAlignment(Qt.AlignCenter)
        self.login_status.hide()

        form_layout.addRow('Username:', self.username_input)
        form_layout.addRow('Password:', self.password_input)
        form_layout.addRow(self.login_button)
        form_layout.addRow(self.login_status)


    def login(self):
        self.login_status.show()

        username = self.username_input.text()
        password = self.password_input.text()

        if not (username and password):
            self.login_status.setText('Enter username and password')
            return

        self.login_status.setText('Logging in...')
        QApplication.processEvents()
        self.repaint()

        try:
            if smashladder_requests.login_to_smashladder(username, password):
                self.close()
            else:
                self.login_status.setText('Wrong username and/or password')
        except smashladder_requests.FailingRequestException as e:
            self.login_status.setText('Error logging in, are you connected to the internet?')


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.initUI()


    def initUI(self):
        uic.loadUi(MAIN_UI_FILE, self)
        # QToolTip.setFont(QFont('SansSerif', 10))
        # self.setToolTip('This is a <b>QWidget</b> widget')

        self.center()
        self.setWindowTitle('smashladder-python')
        self.setWindowIcon(QIcon('conf/smashladder.png'))

        self.mm_button.clicked.connect(self.start_matchmaking)
        self.quit_mm_button.clicked.connect(smashladder.quit_all_matchmaking)

        self.login_window = LoginWindow()
        self.relog_button.clicked.connect(lambda: self.login_window.show())
        self.login()

        self.whitelist_country_button.clicked.connect(self.whitelist_country_wrapper)
        self.high_ping_button.clicked.connect(self.add_high_ping_player_wrapper)

        self.show()


    def login(self):
        if os.path.isfile(local.COOKIE_FILE):
            cookie_jar = local.load_cookies_from_file(local.COOKIE_FILE)
            self.relog_button.hide()
        else:
            self.relog_button.click()


    def start_matchmaking(self):
        builtins.idle = False
        matchmaking_thread = threading.Thread(target=smashladder.matchmaking_loop, args=(local.cookie_jar,))
        matchmaking_thread.daemon = True
        challenge_thread = threading.Thread(target=smashladder.challenge_loop, args=(local.cookie_jar,))
        challenge_thread.daemon = True
        main_socket_thread = threading.Thread(target=smashladder_sockets.connect_to_smashladder, args=(local.cookie_jar,))
        main_socket_thread.daemon = True

        matchmaking_thread.start()
        challenge_thread.start()
        main_socket_thread.start()


    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def whitelist_country_wrapper(self):
        country = self.whitelist_country.text()
        if country and country not in local.WHITELISTED_COUNTRIES:
            local.whitelist_country(country)
            self.config_info.append(country + ' added to whitelist.')
        self.whitelist_country.setText('')


    def add_high_ping_player_wrapper(self):
        username = self.high_ping_username.text()
        if username and username not in local.HIGH_PING_PLAYERS:
            local.add_high_ping_player(username)
            self.config_info.append(username + ' added to high_ping.')
        self.high_ping_username.setText('')


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
