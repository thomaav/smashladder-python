import builtins
import threading
import websocket
import smashladder.sl as sl
import smashladder.slexceptions as slexceptions
from smashladder.local import cookie_jar_to_string
from PyQt5.QtCore import QThread, pyqtSignal

class SlSocketThread(QThread):
    qt_print = pyqtSignal(str)
    entered_match = pyqtSignal(str)

    def __init__(self, cookie_jar=None, parent=None):
        super(SlSocketThread, self).__init__(parent)
        self.lock = threading.Lock()

        if cookie_jar:
            self.cookie_jar = cookie_jar
            self.username = cookie_jar['username']
        else:
            self.cookie_jar = None


    def set_login(self, cookie_jar):
        self.cookie_jar = cookie_jar
        self.username = cookie_jar['username']


    def on_message(self, ws, raw_message):
        with self.lock:
            if '\"authentication\":false' in raw_message:
                self.qt_print.emit('Authentication false, exiting')
                self.ws.close()

            elif 'private_chat' in raw_message:
                processed_message = sl.process_private_chat_message(raw_message)
                self.qt_print.emit(processed_message['info'])

            elif 'current_matches' in raw_message:
                processed_message = sl.process_match_message(raw_message)

                if 'Entered match' in processed_message['info']:
                    self.entered_match.emit(processed_message['match_id'])
                    return

                if not processed_message['typing']:
                    self.qt_print.emit(processed_message['info'])

            elif 'open_challenges' in raw_message:
                try:
                    processed_message = sl.process_open_challenges(self.cookie_jar, raw_message)
                except slexceptions.RequestTimeoutException as e:
                    self.qt_print.emit(str(e))
                    return

                if processed_message['match_id']:
                    self.qt_print.emit(processed_message['info'])

                if 'Accepted challenge' in processed_message['info']:
                    self.entered_match.emit(processed_message['match_id'])

            elif 'searches' in raw_message:
                if builtins.in_match:
                    return

                try:
                    player = sl.process_new_search(self.cookie_jar, raw_message, self.username)
                except slexceptions.RequestTimeoutException as e:
                    self.qt_print.emit(str(e))
                    return

                if player:
                    self.qt_print.emit('Challenging ' + player['username'] + ' from ' + player['country'])


    def on_error(self, ws, error):
        print('[WS ERROR]: ' + str(error))
        print('[DEBUG]: Error in WebSocket, likely tried to close before setup done')


    def on_close(self, ws):
        pass


    def run(self):
        if not self.cookie_jar:
            print('[DEBUG]: WebSocket: can\'t run without login')

        self.ws = websocket.WebSocketApp('wss://www.smashladder.com/?type=1&version=9.11.4',
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close,
                                         cookie = cookie_jar_to_string(self.cookie_jar))
        self.ws.run_forever()
