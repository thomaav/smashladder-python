import builtins
import local
import sys
import smashladder
import smashladder_requests
import threading
import os.path
import time
import enum
from PyQt5.QtWidgets import QApplication, QWidget, QToolTip, QPushButton, \
    QDesktopWidget, QLineEdit, QFormLayout, QMainWindow, QLabel, QTextEdit
from PyQt5.QtGui import QIcon, QFont, QTextCharFormat, QBrush, QColor, QTextCursor, \
    QTextFormat
from PyQt5.QtCore import QCoreApplication, QPoint, Qt, QThread, pyqtSignal
from PyQt5 import uic


BUTTON_SIZE_X = 100
BUTTON_SIZE_Y = 26
MAIN_UI_FILE = 'conf/mainwindow.ui'

def qt_print(text):
    main_window.matchmaking_info.append(text)

# import here after initialization to receive it in smashladder_sockets
import smashladder_sockets


def qt_change_status(status):
    if status == MMStatus.IDLE:
        main_window.mm_status.setText('Idle')
    elif status == MMStatus.IN_QUEUE:
        main_window.mm_status.setText('In queue')
    elif status == MMStatus.IN_MATCH:
        main_window.mm_status.setText('In match')


def move_widget(widget, x_center, y_center):
    qr = widget.frameGeometry()
    center = QPoint(x_center, y_center)
    qr.moveCenter(center)
    widget.move(qr.topLeft())


class MMStatus(enum.Enum):
    IDLE = 1
    IN_QUEUE = 2
    IN_MATCH = 3


class MMThread(QThread):
    qt_print = pyqtSignal(str)
    secs_queued = 0

    def run(self):
        while True:
            self.secs_queued += 5
            if self.secs_queued > 305:
                self.secs_queued = 0
                builtins.in_queue = False

            if builtins.in_match or builtins.idle:
                break
            elif builtins.in_queue:
                time.sleep(5)
                continue
            else:
                mm_status = smashladder.begin_matchmaking(main_window.cookie_jar, 1, 2, 0, '', 0, '')
                builtins.search_match_id = mm_status['match_id']
                self.qt_print.emit(mm_status['info'])
                time.sleep(5)

        self.finished.emit()


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
        self.setMinimumSize(200, 100)
        self.setMaximumSize(350, 110)
        self.resize(300, 100)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.username_input.returnPressed.connect(self.login)
        self.password_input.returnPressed.connect(self.login)

        self.login_button = QPushButton('Log in')
        self.login_button.clicked.connect(self.login)

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
                main_window.login()
                self.login_status.hide()
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
        self.setFixedSize(self.width(), self.height())
        self.setWindowTitle('smashladder-python')
        self.setWindowIcon(QIcon('conf/smashladder.png'))

        self.mm_button.clicked.connect(self.start_matchmaking)
        self.quit_mm_button.clicked.connect(lambda: smashladder.quit_all_matchmaking(self.cookie_jar))

        self.login_window = LoginWindow()
        self.relog_button.clicked.connect(lambda: self.login_window.show())
        self.logout_button.clicked.connect(self.logout)
        self.login()

        self.whitelist_country_button.clicked.connect(self.whitelist_country_wrapper)
        self.whitelist_country.returnPressed.connect(self.whitelist_country_wrapper)
        self.high_ping_button.clicked.connect(self.add_high_ping_player_wrapper)
        self.high_ping_username.returnPressed.connect(self.add_high_ping_player_wrapper)

        self.list_high_ping_button.setIcon(QIcon('conf/list.ico'))
        self.list_whitelisted_countries_button.setIcon(QIcon('conf/list.ico'))
        self.list_high_ping_button.clicked.connect(self.list_high_ping)
        self.list_whitelisted_countries_button.clicked.connect(self.list_whitelisted_countries)

        whitelist_country_tooltip = \
        """
  Used to whitelist specific countries that you want the script
  to allow matches with. Especially useful in Europe where
  distance is less important than the country your opponent is
  residing in.
        """
        high_ping_tooltip = \
        """
  Used to blacklist players that you have a bad connection
  to. Blacklisted players will not be challenged. Can also be used
  cleverly to avoid noobs, jerks and salts without ignoring them
  forever.
        """
        self.whitelist_country_tooltip.setAlignment(Qt.AlignCenter)
        self.high_ping_tooltip.setAlignment(Qt.AlignCenter)
        self.whitelist_country_tooltip.setToolTip(whitelist_country_tooltip)
        self.high_ping_tooltip.setToolTip(high_ping_tooltip)

        self.config_info.mouseMoveEvent = (self.highlight_config_line)
        self.config_info.mousePressEvent = (self.delete_config)
        self.config_info.setLineWrapMode(QTextEdit.NoWrap)

        self.show()


    def login(self):
        if os.path.isfile(local.COOKIE_FILE):
            local.cookie_jar = local.load_cookies_from_file(local.COOKIE_FILE)
            self.cookie_jar = local.load_cookies_from_file(local.COOKIE_FILE)

            self.relog_button.hide()
            self.logged_in_label.show()
            self.logout_button.show()
        else:
            self.logged_in_label.hide()
            self.logout_button.hide()
            self.relog_button.click()


    def logout(self):
        try:
            os.remove(local.COOKIE_FILE)
            self.relog_button.show()
            self.logged_in_label.hide()
            self.logout_button.hide()
        except Exception as e:
            qt_print('Could not delete cookie file: {}'.format(e))


    def start_matchmaking(self):
        if not hasattr(self, 'cookie_jar'):
            qt_print('Log in to matchmake.')
            return False

        builtins.idle = False

        # matchmaking_thread = threading.Thread(target=smashladder.matchmaking_loop, args=(self.cookie_jar,))
        self.matchmaking_thread = MMThread()
        # challenge_thread = threading.Thread(target=smashladder.challenge_loop, args=(self.cookie_jar,))
        # main_socket_thread = threading.Thread(target=smashladder_sockets.connect_to_smashladder, args=(self.cookie_jar,))
        # self.matchmaking_thread.daemon = True
        # challenge_thread.daemon = True
        # main_socket_thread.daemon = True
        self.matchmaking_thread.qt_print.connect(qt_print)
        self.matchmaking_thread.start()
        # challenge_thread.start()
        # main_socket_thread.start()

        return True


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


    def reset_config_info_highlighting(self):
        reset_cursor = self.config_info.textCursor()
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor('white')))
        reset_cursor.setPosition(0)
        reset_cursor.movePosition(QTextCursor.End, 1)
        reset_cursor.mergeCharFormat(format)


    def highlight_config_line(self, evt):
        self.reset_config_info_highlighting()
        cur = self.config_info.cursorForPosition(evt.pos())
        cur_line_no = cur.blockNumber()

        if cur_line_no <= 1:
            return

        cur.select(QTextCursor.LineUnderCursor)
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor('red')))
        cur.mergeCharFormat(format)


    def delete_config(self, evt):
        self.reset_config_info_highlighting()
        cur = self.config_info.cursorForPosition(evt.pos())
        cur.select(QTextCursor.LineUnderCursor)
        selected_text = cur.selectedText()

        config_info_title = self.config_info.toPlainText()[:9]
        if config_info_title == 'High ping':
            local.remove_high_ping_player(selected_text)
            self.list_high_ping_button.click()
        elif config_info_title == 'Whitelist':
            local.remove_whitelisted_country(selected_text)
            self.list_whitelisted_countries_button.click()


    def list_high_ping(self):
        self.config_info.clear()
        self.config_info.append('High ping players')
        self.config_info.append('----------------------')

        for player in sorted(local.HIGH_PING_PLAYERS):
            self.config_info.append(player)

        self.config_info.verticalScrollBar().setValue(0)


    def list_whitelisted_countries(self):
        self.config_info.clear()
        self.config_info.append('Whitelisted countries')
        self.config_info.append('---------------------------')

        for country in sorted(local.WHITELISTED_COUNTRIES):
            self.config_info.append(country)

        self.config_info.verticalScrollBar().setValue(0)


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
