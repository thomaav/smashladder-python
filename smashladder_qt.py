import builtins
import local
import sys
import smashladder
import smashladder_requests
import threading
import os.path
import time
import enum
import websocket
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


class SocketThread(QThread):
    qt_print = pyqtSignal(str)

    def on_message(self, ws, raw_message):
        if '\"authentication\":false' in raw_message:
            self.qt_print.emit('Authentication false, exiting')
            exit(1)
        elif 'private_chat' in raw_message:
            processed_message = smashladder.process_private_chat_message(raw_message)
            self.qt_print.emit(processed_message['info'])
        elif 'current_matches' in raw_message:
            processed_message = smashladder.process_match_message(raw_message)
            if not processed_message['typing']:
                self.qt_print.emit(processed_message['info'])
        elif 'open_challenges' in raw_message:
            processed_message = smashladder.process_open_challenges(local.cookie_jar, raw_message)
            if processed_message['match_id']:
                self.qt_print.emit(processed_message['info'])


    def on_error(self, ws, error):
        print(error)


    def on_close(self, ws):
        print('WebSocket to smashladder closed')


    def run(self):
        ws = websocket.WebSocketApp('wss://www.smashladder.com/?type=1&version=9.11.4',
                                    on_message = self.on_message,
                                    on_error = self.on_error,
                                    on_close = self.on_close,
                                    cookie = local.cookie_jar_to_string(local.cookie_jar))
        ws.run_forever()


class LoginWindow(QWidget):
    def __init__(self, main_window, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.main_window = main_window
        self.initUI()


    def initUI(self):
        self.setWindowTitle("Login")
        form_layout = QFormLayout()
        self.form_layout = form_layout
        self.setLayout(form_layout)
        self.setObjectName('LoginWidget')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        with open('conf/mainwindow.css') as f:
            self.setStyleSheet(f.read())

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

        self.showEvent = self.show_event
        self.closeEvent = self.close_event


    def show_event(self, evt):
        self.main_window.setEnabled(False)


    def close_event(self, evt):
        self.main_window.setEnabled(True)


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
                self.main_window.login()
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
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle('smashladder-python')
        self.setWindowIcon(QIcon('conf/smashladder.png'))

        with open('conf/mainwindow.css') as f:
            self.setStyleSheet(f.read())

        self.minimize_button.clicked.connect(lambda: self.showMinimized())
        self.exit_button.clicked.connect(lambda: self.close())

        self.mm_button.clicked.connect(self.start_matchmaking)
        self.quit_mm_button.clicked.connect(lambda: smashladder.quit_all_matchmaking(self.cookie_jar))

        self.whitelist_country_button.clicked.connect(self.whitelist_country_wrapper)
        self.whitelist_country.returnPressed.connect(self.whitelist_country_wrapper)
        self.blacklist_player_button.clicked.connect(self.blacklist_player_wrapper)
        self.blacklist_player_username.returnPressed.connect(self.blacklist_player_wrapper)

        self.list_blacklisted_players_button.setIcon(QIcon('conf/list.ico'))
        self.list_whitelisted_countries_button.setIcon(QIcon('conf/list.ico'))
        self.list_blacklisted_players_button.clicked.connect(self.list_blacklisted_players)
        self.list_whitelisted_countries_button.clicked.connect(self.list_whitelisted_countries)

        whitelist_country_tooltip = \
        """
  Used to whitelist specific countries that you want the script
  to allow matches with. Especially useful in Europe where
  distance is less important than the country your opponent is
  residing in.
        """
        blacklist_player_tooltip = \
        """
  Used to blacklist players that you have a bad connection
  to. Blacklisted players will not be challenged. Can be used cleverly
  to avoid noobs, jerks and salts without ignoring them forever.
        """
        self.whitelist_country_tooltip.setAlignment(Qt.AlignCenter)
        self.blacklist_player_tooltip.setAlignment(Qt.AlignCenter)
        self.whitelist_country_tooltip.setToolTip(whitelist_country_tooltip)
        self.blacklist_player_tooltip.setToolTip(blacklist_player_tooltip)

        self.config_info.mouseMoveEvent = (self.highlight_config_line)
        self.config_info.mousePressEvent = (self.delete_config)
        self.config_info.setLineWrapMode(QTextEdit.NoWrap)

        self.show()

        # we want the creation of the main window to be _done_ before
        # we create the login window
        self.login_window = LoginWindow(self)
        self.relog_button.clicked.connect(lambda: self.login_window.show())
        self.logout_button.clicked.connect(self.logout)
        self.login()


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
            local.cookie_jar = None
            self.cookie_jar = None
            os.remove(local.COOKIE_FILE)

            self.relog_button.show()
            self.logged_in_label.hide()
            self.logout_button.hide()
        except Exception as e:
            qt_print('Could not delete cookie file: {}'.format(e))


    def start_matchmaking(self):
        if not hasattr(self, 'cookie_jar') or not self.cookie_jar:
            qt_print('Log in to matchmake')
            return False

        builtins.idle = False

        # self.matchmaking_thread = MMThread()
        # challenge_thread = threading.Thread(target=smashladder.challenge_loop, args=(self.cookie_jar,))
        self.socket_thread = SocketThread()

        # self.matchmaking_thread.qt_print.connect(qt_print)
        # self.matchmaking_thread.start()
        self.socket_thread.qt_print.connect(qt_print)
        self.socket_thread.start()

        return True


    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def whitelist_country_wrapper(self):
        country = self.whitelist_country.text()

        if country:
            self.config_info.clear()
            if country not in local.WHITELISTED_COUNTRIES:
                local.whitelist_country(country)
                self.config_info.append(country + ' added to whitelist')
            else:
                self.config_info.append(country + ' already whitelisted')
            self.whitelist_country.setText('')


    def blacklist_player_wrapper(self):
        username = self.blacklist_player_username.text()

        if username:
            self.config_info.clear()
            if username not in local.BLACKLISTED_PLAYERS:
                local.blacklist_player(username)
                self.config_info.append(username + ' added to blacklisted players')
            else:
                self.config_info.append(username + ' already blacklisted')
            self.blacklist_player_username.setText('')


    def reset_config_info_highlighting(self):
        reset_cursor = self.config_info.textCursor()
        format = QTextCharFormat()
        format.setBackground(QBrush(QColor(18, 20, 28)))
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
        if config_info_title == 'Blacklist':
            local.remove_blacklisted_player(selected_text)
            self.list_blacklisted_players_button.click()
        elif config_info_title == 'Whitelist':
            local.remove_whitelisted_country(selected_text)
            self.list_whitelisted_countries_button.click()


    def list_blacklisted_players(self):
        self.config_info.clear()
        self.config_info.append('Blacklisted players')
        self.config_info.append('------------------------')

        for player in sorted(local.BLACKLISTED_PLAYERS):
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
