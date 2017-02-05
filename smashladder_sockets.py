import websocket
import json
from smashladder_requests import cookie_jar_to_string
from smashladder import *
from main import cookie_jar

def on_message(ws, message):
    if '\"authentication\":false' in message:
        print('Authentication: false. Exiting.')
        exit(1)
    elif 'private_chat' in message:
        handle_private_chat_message(message)
    elif 'current_matches' in message:
        handle_match_message(message)
    elif 'open_challenges' in message:
        handle_open_challenges(cookie_jar, message)


def on_error(ws, error):
    print(error)

def on_close(ws):
    print('WebSocket to smashladder closed.')

def connect_to_smashladder(cookie_jar):
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp('wss://www.smashladder.com/?type=1&version=9.11.4',
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                cookie = cookie_jar_to_string(cookie_jar))
    ws.run_forever()
