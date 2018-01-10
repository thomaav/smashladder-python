import builtins
import threading
import time
import websocket
import smashladder.sl as sl
import smashladder.slexceptions as slexceptions
from smashladder.local import cookie_jar_to_string
from PyQt5.QtCore import QThread, pyqtSignal

class SlBaseThread(QThread):
    qt_print = pyqtSignal(str)

    def __init__(self, cookie_jar=None, parent=None):
        super().__init__(parent)
        if cookie_jar:
            self.cookie_jar = cookie_jar
            self.username = cookie_jar['username']
        else:
            self.cookie_jar = None


    def set_login(self, cookie_jar):
        self.cookie_jar = cookie_jar
        self.username = cookie_jar['username']


    def logout(self):
        self.cookie_jar = None
        self.username = None


class SlSocketThread(SlBaseThread):
    entered_match = pyqtSignal(str)
    match_message = pyqtSignal(str)
    private_message = pyqtSignal(str)

    def __init__(self, cookie_jar=None, parent=None):
        super().__init__(cookie_jar, parent)
        self.lock = threading.Lock()
        self.priv_chat_enabled = True


    def auth_false(self):
        self.qt_print.emit('Authentication false, exiting')
        self.ws.close()


    def process_private_chat_message(self, raw_message):
        processed_message = sl.process_private_chat_message(raw_message)
        self.qt_print.emit(processed_message['info'])
        self.private_message.emit(processed_message['info'].replace('[private chat] ', ''))


    def process_match_message(self, raw_message):
        processed_message = sl.process_match_message(raw_message)
        if 'Entered match' in processed_message['info']:
            self.entered_match.emit(processed_message['match_id'])
            return

        if not processed_message['typing']:
            self.qt_print.emit(processed_message['info'])
            self.match_message.emit(processed_message['info'].replace('[match chat] ', ''))


    def process_open_challenges(self, raw_message):
        try:
            processed_message = sl.process_open_challenges(self.cookie_jar, raw_message)
        except slexceptions.RequestTimeoutException as e:
            self.qt_print.emit(str(e))
            return

        if processed_message['match_id']:
            self.qt_print.emit(processed_message['info'])

        if 'Accepted challenge' in processed_message['info']:
            self.entered_match.emit(processed_message['match_id'])


    def process_new_search(self, raw_message):
        if builtins.in_match:
            return

        try:
            player = sl.process_new_search(self.cookie_jar, raw_message, self.username)
        except slexceptions.RequestTimeoutException as e:
            self.qt_print.emit(str(e))
            return

        if player:
            self.qt_print.emit('Challenging ' + player['username'] + ' from ' + player['country'])

    def on_message(self, ws, raw_message):
        with self.lock:
            if '\"authentication\":false' in raw_message:
                self.auth_false()
                return

            if builtins.in_queue:
                if 'current_matches' in raw_message:
                    self.process_match_message(raw_message)

                elif 'open_challenges' in raw_message:
                    self.process_open_challenges(raw_message)

                elif 'searches' in raw_message:
                    self.process_new_search(raw_message)

            # we need to redo current_matches here, as it appears both
            # when entering match, and when receiving a match message
            if builtins.in_match and 'current_matches' in raw_message:
                self.process_match_message(raw_message)

            if 'private_chat' in raw_message and self.priv_chat_enabled:
                self.process_private_chat_message(raw_message)


    def on_error(self, ws, error):
        print('[WS ERROR]: ' + str(error))
        print('[DEBUG]: Error in WebSocket, likely tried to close before setup done')


    def on_close(self, ws):
        pass


    def run(self):
        if not self.cookie_jar:
            print('[DEBUG]: SocketThread: can\'t run without login')
            return

        self.ws = websocket.WebSocketApp('wss://www.smashladder.com/?type=1&version=9.11.4',
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close,
                                         cookie = cookie_jar_to_string(self.cookie_jar))
        self.ws.run_forever()


class MMThread(SlBaseThread):
    secs_queued = 0

    def __init__(self, cookie_jar=None, parent=None):
        super().__init__(parent)


    def run(self):
        if not self.cookie_jar:
            print('[DEBUG]: MMThread: can\'t run without login')
            return

        while True:
            if builtins.debug_smashladder:
                print('[DEBUG]: Would start matchmaking search')
                break

            if builtins.in_match or builtins.idle:
                break

            if builtins.in_queue:
                self.secs_queued += 1
                if self.secs_queued > 305:
                    self.secs_queued = 0
                    builtins.in_queue = False
                    builtins.search_match_id = None
                time.sleep(1)
                continue
            else:
                try:
                    mm_status = sl.begin_matchmaking(self.cookie_jar, 1, 2, 0, '', 0, '')
                except slexceptions.RequestTimeoutException as e:
                    self.qt_print.emit(str(e))
                    break

                if 'Already in queue' in mm_status['info']:
                    builtins.in_queue = True
                    continue

                self.qt_print.emit(mm_status['info'])

                if mm_status['match_id']:
                    builtins.in_queue = True
                    builtins.search_match_id = mm_status['match_id']

                time.sleep(1)


class ChallengeThread(SlBaseThread):
    def __init__(self, cookie_jar=None, parent=None):
        super().__init__(parent)

    def run(self):
        if not self.cookie_jar:
            print('[DEBUG]: ChallengeThread: can\'t run without login')
            return

        try:
            challenged_players = sl.challenge_relevant_friendlies(self.cookie_jar, self.username)
        except slexceptions.RequestTimeoutException as e:
            self.qt_print.emit(str(e))
            return

        for player in challenged_players:
            self.qt_print.emit('Challenging ' + player['username'] + ' from ' + player['country'])
