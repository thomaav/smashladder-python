import builtins
import sys
import smashladder.local as local
import smashladder.sl as sl
import smashladder.slrequests as slrequests
import smashladder.slexceptions as slexceptions
import smashladder.slthreads as slthreads
import os.path
import time
import enum
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QToolTip, QPushButton, \
    QDesktopWidget, QLineEdit, QFormLayout, QMainWindow, QLabel, QTextEdit
from PyQt5.QtGui import QIcon, QFont, QTextCharFormat, QBrush, QColor, QTextCursor, \
    QTextFormat, QCursor
from PyQt5.QtCore import QCoreApplication, QPoint, Qt, QThread, pyqtSignal
from PyQt5 import uic


MAINWINDOW_UI_FILE = 'static/mainwindow.ui'
MAINWINDOW_CSS_FILE = 'static/mainwindow.css'
QDOCUMENT_CSS_FILE = 'static/qdocument.css'
MATCH_UI_FILE = 'static/match.ui'
PRIV_CHAT_UI_FILE = 'static/private_chat.ui'


def qt_print(text):
    main_window.matchmaking_info.append('| ' + text)
    QApplication.processEvents()
    main_window.repaint()


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


class MovableQWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mpressed = False
        self.mousePressEvent = (self.mouse_press)
        self.mouseReleaseEvent = (self.mouse_release)
        self.mouseMoveEvent = (self.mouse_move)

    def mouse_press(self, evt):
        cursor = QCursor()
        pos = cursor.pos()
        geometry = self.geometry()

        self.mpress_cur_x = pos.x()
        self.mpress_cur_y = pos.y()
        self.mpress_x = geometry.x()
        self.mpress_y = geometry.y()
        self.mpressed = True


    def mouse_release(self, evt):
        self.mpressed = False


    def mouse_move(self, evt):
        if self.mpressed:
            cursor = QCursor()
            pos = cursor.pos()

            diff_x = pos.x() - self.mpress_cur_x
            diff_y = pos.y() - self.mpress_cur_y

            self.move(self.mpress_x + diff_x, self.mpress_y + diff_y)


class PrivateChatWindow(MovableQWidget):
    async_print = pyqtSignal(str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.username = None
        self.main_window = main_window
        self.async_print.connect(self.print)
        self.initUI()


    def initUI(self):
        uic.loadUi(PRIV_CHAT_UI_FILE, self)

        self.setWindowTitle('Private chat')
        self.setFixedSize(self.width(), self.height())
        self.setObjectName('PrivateChatWidget')
        self.setWindowFlags(Qt.FramelessWindowHint)

        with open(MAINWINDOW_CSS_FILE) as f:
            self.setStyleSheet(f.read())


    def print(self, text):
        self.priv_chat_info.append('| ' + text)


    def clear(self):
        self.priv_chat_info.clear()


    def change_user(self, username):
        self.clear()
        self.username = username
        self.username_label.setText(username)

        def async_fetch_messages():
            latest_messages = sl.fetch_private_messages(main_window.cookie_jar, self.username)
            for message in latest_messages:
                self.async_print.emit(message['username'] + ': ' + message['message'])
        thr = threading.Thread(target=async_fetch_messages, args=(), kwargs={})
        thr.start()


    def send_message(self):
        message = self.priv_chat_input.text()
        if message:
            if message[0] == '/':
                if 'change_user' in message:
                    smsg = message.strip().split()
                    try:
                        username = smsg[1]
                        self.change_user(username)
                    except:
                        print('[DEBUG]: Error changing privmsg user, no username found')
            else:
                def async_message():
                    sl.send_private_chat_message(main_window.cookie_jar, self.username, message)
                thr = threading.Thread(target=async_message, args=(), kwargs={})
                thr.start()
            self.priv_chat_input.setText('')


class MatchWindow(MovableQWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.initUI()


    def initUI(self):
        uic.loadUi(MATCH_UI_FILE, self)

        self.setWindowTitle('Match chat')
        self.setFixedSize(self.width(), self.height())
        self.setObjectName('MatchWidget')
        self.setWindowFlags(Qt.FramelessWindowHint)

        with open(MAINWINDOW_CSS_FILE) as f:
            self.setStyleSheet(f.read())

        self.hideEvent = self.hide_event


    def print(self, text):
        self.match_info.append('| ' + text)


    def clear(self):
        self.match_info.clear()


    def send_message(self):
        message = self.match_input.text()
        if message and builtins.in_match:
            def async_message():
                sl.send_match_chat_message(main_window.cookie_jar, builtins.current_match_id, message)
            thr = threading.Thread(target=async_message, args=(), kwargs={})
            thr.start()
            self.match_input.setText('')


    def hide_event(self, evt):
        self.clear()
        main_window.quit_matchmaking()


class LoginWindow(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.initUI()


    def initUI(self):
        self.setWindowTitle("Login")
        form_layout = QFormLayout()
        self.form_layout = form_layout
        self.setLayout(form_layout)
        self.setObjectName('LoginWidget')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        with open(MAINWINDOW_CSS_FILE) as f:
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
            if slrequests.login_to_smashladder(username, password):
                self.main_window.login()
                self.main_window.username = username
                self.login_status.hide()
                self.close()
            else:
                self.login_status.setText('Wrong username and/or password')
        except slexceptions.RequestTimeoutException as e:
            qt_print(str(e))
            self.login_status.setText('Login to server timed out, try again later')


class MainWindow(MovableQWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_threads()
        self.initUI()


    def initUI(self):
        uic.loadUi(MAINWINDOW_UI_FILE, self)

        self.center()
        self.setFixedSize(self.width(), self.height())
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle('smashladder-python')

        with open(MAINWINDOW_CSS_FILE) as f:
            self.setStyleSheet(f.read())

        self.minimize_button.clicked.connect(lambda: self.showMinimized())
        self.exit_button.clicked.connect(lambda: self.close())

        self.mm_button.clicked.connect(self.start_matchmaking)
        self.quit_mm_button.clicked.connect(self.quit_matchmaking)

        self.whitelist_country_button.clicked.connect(self.whitelist_country_wrapper)
        self.whitelist_country.returnPressed.connect(self.whitelist_country_wrapper)
        self.blacklist_player_button.clicked.connect(self.blacklist_player_wrapper)
        self.blacklist_player_username.returnPressed.connect(self.blacklist_player_wrapper)

        self.list_blacklisted_players_button.setIcon(QIcon('static/list.ico'))
        self.list_whitelisted_countries_button.setIcon(QIcon('static/list.ico'))
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

        self.matchmaking_info.mousePressEvent = (self.click_username)
        with open(QDOCUMENT_CSS_FILE) as f:
            self.matchmaking_info.document().setDefaultStyleSheet(f.read())

        self.friendlies_checkbox.setChecked(True)
        self.friendlies_checkbox.toggled.connect(self.change_checkbox_config)
        sl.friendlies_enabled = self.friendlies_checkbox.isChecked()
        self.ranked_checkbox.setChecked(False)
        self.ranked_checkbox.toggled.connect(self.change_checkbox_config)
        sl.ranked_enabled = self.ranked_checkbox.isChecked()
        self.doubles_checkbox.setChecked(False)
        self.doubles_checkbox.toggled.connect(self.change_checkbox_config)
        sl.doubles_enabled = self.doubles_checkbox.isChecked()
        self.priv_chat_checkbox.setChecked(True)
        self.priv_chat_checkbox.toggled.connect(self.change_checkbox_config)

        self.show()

        # we want the creation of the main window to be _done_ before
        # we create the login window and match window
        self.login_window = LoginWindow(self)
        self.relog_button.clicked.connect(lambda: self.login_window.show())
        self.logout_button.clicked.connect(self.logout)
        self.login()

        self.match_window = MatchWindow(self)
        self.match_window.match_input.returnPressed.connect(self.match_window.send_message)
        self.socket_thread.match_message.connect(self.match_window.print)
        self.match_window.quit_match_button.clicked.connect(self.match_window.hide)

        self.priv_chat_window = PrivateChatWindow(self)
        self.priv_chat_window.priv_chat_input.returnPressed.connect(self.priv_chat_window.send_message)
        self.socket_thread.private_message.connect(self.priv_chat_window.print)
        self.priv_chat_window.close_button.clicked.connect(lambda: self.priv_chat_window.hide())
        self.priv_chat_label.mousePressEvent = (lambda _: self.priv_chat_window.show())


    def init_threads(self):
        self.matchmaking_thread = slthreads.MMThread()
        self.socket_thread = slthreads.SlSocketThread()
        self.challenge_thread = slthreads.ChallengeThread()

        self.matchmaking_thread.qt_print.connect(qt_print)
        self.socket_thread.qt_print.connect(qt_print)
        self.socket_thread.entered_match.connect(self.entered_match)
        self.challenge_thread.qt_print.connect(qt_print)


    def login(self):
        if os.path.isfile(local.COOKIE_FILE):
            local.cookie_jar = local.load_cookies_from_file(local.COOKIE_FILE)
            self.cookie_jar = local.load_cookies_from_file(local.COOKIE_FILE)
            self.username = self.cookie_jar['username']

            self.socket_thread.set_login(self.cookie_jar)
            self.matchmaking_thread.set_login(self.cookie_jar)
            self.challenge_thread.set_login(self.cookie_jar)

            self.socket_thread.start()

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

            self.socket_thread.logout()
            self.matchmaking_thread.logout()
            self.challenge_thread.logout()

            self.relog_button.show()
            self.logged_in_label.hide()
            self.logout_button.hide()
        except Exception as e:
            qt_print('Could not delete cookie file: {}'.format(e))


    def start_matchmaking(self):
        if not hasattr(self, 'cookie_jar') or not self.cookie_jar:
            qt_print('Log in to matchmake')
            return

        if not builtins.idle:
            qt_print('Already matchmaking, can\'t start matchmaking')
            return

        builtins.idle = False
        self.matchmaking_thread.start()
        self.challenge_thread.start()
        if not self.socket_thread.isRunning():
            self.socket_thread.start()

        qt_change_status(MMStatus.IN_QUEUE)
        qt_print('Successfully started matchmaking')


    def quit_matchmaking(self):
        if builtins.idle and not builtins.in_match:
            qt_print('Already idle, can\'t quit matcmaking')
            return

        qt_print('Quitting matchmaking..')

        builtins.idle = True
        self.matchmaking_thread.wait()
        if self.challenge_thread.isRunning():
            self.challenge_thread.terminate()

        if builtins.search_match_id:
            quit_queue = sl.quit_matchmaking(self.cookie_jar, builtins.search_match_id)
            if quit_queue:
                qt_print('Successfully unqueued match with id: ' + builtins.search_match_id)
        elif builtins.in_match:
            sl.report_friendly_done(self.cookie_jar, builtins.current_match_id)
            sl.finished_chatting_with_match(self.cookie_jar, builtins.current_match_id)

        builtins.in_queue = False
        builtins.search_match_id = None
        builtins.current_match_id = None
        builtins.in_match = False
        builtins.idle = True
        qt_change_status(MMStatus.IDLE)
        qt_print('Successfully quit matchmaking')


    def entered_match(self, match_id, opponent_username, opponent_country):
        if builtins.in_match:
            return

        builtins.current_match_id = match_id
        builtins.in_match = True
        builtins.in_queue = False
        builtins.search_match_id = None

        # quit threads that look for matches
        builtins.idle = True
        self.matchmaking_thread.wait()
        if self.challenge_thread.isRunning():
            self.challenge_thread.terminate()

        qt_print('Entered match: ' + match_id)
        qt_change_status(MMStatus.IN_MATCH)
        self.match_window.show()
        self.match_window.print('Match with ' + opponent_username + ' from ' + opponent_country)
        self.match_window.setFocus()


    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


    def change_checkbox_config(self):
        sl.friendlies_enabled = self.friendlies_checkbox.isChecked()
        sl.ranked_enabled = self.ranked_checkbox.isChecked()
        sl.doubles_enabled = self.doubles_checkbox.isChecked()
        self.socket_thread.priv_chat_enabled = self.priv_chat_checkbox.isChecked()


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


    def click_username(self, evt):
        cur = self.matchmaking_info.cursorForPosition(evt.pos())
        cur.select(QTextCursor.BlockUnderCursor)
        selected_line = cur.selectedText()

        if '| [private chat]' in selected_line:
            username = selected_line.strip().split(' ')[3].replace(':', '')
            self.priv_chat_window.change_user(username)
            self.priv_chat_window.show()


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
