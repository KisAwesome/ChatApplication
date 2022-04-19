import pickle
import webbrowser
import windows.login
import windows.register
import windows.ui
import SocketTypes
import json
import time
import platform 
import subprocess
import re

def find_urls(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    return [x[0] for x in url]

CMD = '''
on run argv
  display notification (item 2 of argv) with title (item 1 of argv)
end run
'''

def _notify(title,text,f):
    global settings
    if settings['notifications']:
        f(title,text)

def message_box(title,message):
    global CURRENT_WINDOW
    windows.ui.message_box(title,message,CURRENT_WINDOW)

if platform.system() == 'Darwin':
    NOTIFY = lambda title,text :_notify(title,text,lambda title,text:subprocess.call(['osascript', '-e', CMD, title, text]))
else:
    import plyer
    NOTIFY =lambda title,text:_notify(title,text,lambda t,m : plyer.notification.notify(timeout=7,title=t,message=m))

# Connection Variables
IP = '192.168.1.246'
PORT = 4245
ADDR = (IP, PORT)
DEFAULT_SETTINGS = {'notifications':True, 'stay_logged_in':True,'ask_before_link_open':True}



try:
    with open('settings.json') as file:
        settings = json.load(file)

except FileNotFoundError:
    with open('settings.json','w') as file:
        json.dump(DEFAULT_SETTINGS,file)
    settings = DEFAULT_SETTINGS



mainSocket = SocketTypes.SecureSocket(ADDR)
statusSocket = SocketTypes.SecureSocket(ADDR)
eventSocket = SocketTypes.SecureSocket(ADDR)

def recv(socket):
    obj = socket.recv()
    if obj.get('error',None):
        message_box('Error',obj.get('info','An unknown error occured'))
    
    return obj



def packet(**kwargs):
    pkt = {}
    for k, v in kwargs.items():
        pkt[k] = v

    return pkt


def form_time(timestamp):
    return time.strftime('%I:%M%p',time.localtime(timestamp))


SESSION_TOKEN = None

# Ui variables 
CURRENT_WINDOW = None
MESSAGE_STORE = {}
APP = windows.login.get_app()
LOGIN_UI = None
MAIN_UI = None
REGISTER_UI = None
CONVERSATIONS = {}
CONV_ID_PARTICIPANTS = {}
CURRENT_USER = None
SELECTED = False
TYPING = False


def login():
    global SESSION_TOKEN
    global CURRENT_USER

    user = LOGIN_UI.lineEdit.text()
    password = LOGIN_UI.lineEdit_2.text()
    mainSocket.send(packet(path='login', user=user, password=password))

    resp = recv(mainSocket)
    if resp['succsess']:
        SESSION_TOKEN = resp['session']
        CURRENT_USER = user
        if settings['stay_logged_in']:
            with open('_session.pickle','wb') as file:
                pickle.dump(SESSION_TOKEN,file)
        main_window()

  


def open_private_conversation():
    user = MAIN_UI.lineEdit.text()
    mainSocket.send(packet(user=user, session=SESSION_TOKEN, path='open_private_conversation'))
    resp = recv(mainSocket)
    if resp['succsess']:
        MAIN_UI.listView.addItem(user)
        CONVERSATIONS[len(CONVERSATIONS)] = resp['conv_id']
        CONV_ID_PARTICIPANTS[resp['conv_id']] = [user]


def reload_stores():
    CONVERSATIONS.clear()
    CONV_ID_PARTICIPANTS.clear()
    MESSAGE_STORE.clear()
    MAIN_UI.listView.clear()
    load_conversations()

def load_conversations():
    mainSocket.send(packet(path='conversations', session=SESSION_TOKEN))
    conversations = recv(mainSocket)['conversations']
    for index, conversation in enumerate(conversations.items()):
        MAIN_UI.listView.addItem(conversation[0])
        CONVERSATIONS[index] = conversation[1][0]
        CONV_ID_PARTICIPANTS[conversation[1][0]] = conversation[1][1]

def wait_events():
    event = recv(eventSocket)
    if event['type'] == 'new_message':
        if not MAIN_UI.MainWindow.hasFocus():
            NOTIFY(event['from'],event['message'])
        row = MAIN_UI.listView.currentRow()
        conv_id = CONVERSATIONS[row]
        if conv_id == event['channel']:
            message = event['message']
            sender = event['from']
            formed_time = form_time(event['time'])
            MAIN_UI.listWidget.addItem(f'{formed_time} {sender}: {message}')
            MESSAGE_STORE[conv_id].append(
                    {'message': event['message'], 'sender': event['from'], 'time': event['time']})
            # MAIN_UI.scroll_to_bottom()

        else:
            NOTIFY(event['from'],event['message'])
            if conv_id in MESSAGE_STORE:
                MESSAGE_STORE[conv_id].append(
                    {'message': event['message'], 'sender': event['from'], 'time': event['time']})


    elif event['type'] == 'new_conversation':
            MAIN_UI.listView.addItem(event['conversation'])
            CONVERSATIONS[len(CONVERSATIONS)] = event['conv_id']
            CONV_ID_PARTICIPANTS[event['conv_id']] = [event['conversation']]
           

def refresh():
    if SELECTED:
        row = MAIN_UI.listView.currentRow()
        if row == -1:
            return
        conv_id = CONVERSATIONS[row]
        _part = CONV_ID_PARTICIPANTS[conv_id][0]
        statusSocket.send(packet(path='status', session=SESSION_TOKEN, user=_part, channel=conv_id))
        status = recv(statusSocket)
        state_ = status.get('succsess',False)


        if not state_:
            return
        if not 'user_status' in status:
            return
        MAIN_UI.label_2.setText(status['user_status'])


def send_message():
    message = MAIN_UI.textEdit.toPlainText().strip()
    if not message:
        return
    row = MAIN_UI.listView.currentRow()
    conv_id = CONVERSATIONS[row]
    TIME = time.time()
    MAIN_UI.textEdit.clear()
    MESSAGE_STORE[conv_id].append(
        {'message': message, 'sender': CURRENT_USER, 'time': TIME})

    MAIN_UI.listWidget.addItem(f'{form_time(TIME)} {CURRENT_USER}: {message}')
    # MAIN_UI.scroll_to_bottom()

    mainSocket.send(packet(channel=conv_id, message=message,
         session=SESSION_TOKEN, path='send_message'))
    # MAIN_UI.textEdit.setText('')


def register():
    global SESSION_TOKEN
    global CURRENT_USER
    user = REGISTER_UI.lineEdit.text()
    # email = REGISTER_UI.lineEdit_2.text()
    password = REGISTER_UI.lineEdit_2.text()

    mainSocket.send(packet(path='register', user=user, password=password))
    resp = recv(mainSocket)
    if resp['succsess']:
        SESSION_TOKEN = resp['session']
        CURRENT_USER = user
        if settings['stay_logged_in']:
            with open('_session.pickle','wb') as file:
                pickle.dump(SESSION_TOKEN,file)
                
        main_window()


def on_contact_click(selection):
    global SELECTED
    MAIN_UI.textEdit.setFocus()
    SELECTED = True
    row = MAIN_UI.listView.currentRow()
    conv_id = CONVERSATIONS[row]
    MAIN_UI.label.setText(selection.text())
    if conv_id in MESSAGE_STORE:
        MAIN_UI.listWidget.clear()
        for message in MESSAGE_STORE[conv_id]:
            sender = message['sender']
            message_text = message['message']
            formed_time = form_time(message['time'])
            MAIN_UI.listWidget.addItem(
                f'{formed_time} {sender}: {message_text}')
        # MAIN_UI.scroll_to_bottom()

    else:
        mainSocket.send(packet(path='messages', session=SESSION_TOKEN, channel=conv_id))
        messages = recv(mainSocket)['messages']
        MAIN_UI.listWidget.clear()
        MESSAGE_STORE[conv_id] = messages
        for message in messages:
            sender = message['sender']
            message_text = message['message']
            formed_time = form_time(message['time'])
            MAIN_UI.listWidget.addItem(
                f'{formed_time} {sender}: {message_text}')
        # MAIN_UI.scroll_to_bottom()

def register_window():
    global CURRENT_WINDOW, REGISTER_UI

    if CURRENT_WINDOW:
        CURRENT_WINDOW.hide()

    MainWindow, ui = windows.register.get_app()
    CURRENT_WINDOW = MainWindow
    REGISTER_UI = ui
    ui.submit_shortcut.activated.connect(register)
    ui.pushButton_4.clicked.connect(login_window)
    ui.pushButton.clicked.connect(lambda x: ui.show_hide())
    ui.pushButton_2.clicked.connect(register)
    ui.submit_shortcut.activated.connect(register)
    MainWindow.show()


def on_text_change():
    global TYPING
    row = MAIN_UI.listView.currentRow()
    conv_id = CONVERSATIONS[row]
    _text = MAIN_UI.textEdit.toPlainText()
    text = _text.strip()
    if '\n' in _text:
        return send_message()
    if text:
        state = True
    else:
        state = False


    if state != TYPING:
        TYPING = state
    else:
        return


    mainSocket.send(packet(path='typing', channel=conv_id,
         typing=state, session=SESSION_TOKEN))

    resp = recv(mainSocket)

def message_clicked(x):
    url = MAIN_UI.listWidget.item(x.row()).text()
    url = find_urls(url)
    if url:
        if settings['ask_before_link_open']:
            if not windows.ui.question_box('Question','Are you sure you want to open this link?',CURRENT_WINDOW):
                return
        webbrowser.open(url[0])

def main_window():
    global CURRENT_WINDOW, MAIN_UI

    if CURRENT_WINDOW:
        CURRENT_WINDOW.hide()
    eventSocket.send(packet(path='event_socket',session=SESSION_TOKEN))
    _status = recv(eventSocket)
    MainWindow, ui = windows.ui.get_window()
    ui.worker.func = refresh
    ui.eventworker.func = wait_events
    ui.thread2.start()
    ui.thread.start()
    ui.reloadshortcut.activated.connect(reload_stores)
    CURRENT_WINDOW = MainWindow
    MAIN_UI = ui
    ui.pushButton.clicked.connect(open_private_conversation)
    ui.listView.itemClicked.connect(on_contact_click)
    load_conversations()
    MAIN_UI.listWidget.activated.connect(message_clicked)
    # ui.timer.timeout.connect(refresh)
    # ui.timer.start()
    ui.pushButton_4.clicked.connect(send_message)
    ui.textEdit.textChanged.connect(on_text_change)
    MainWindow.show()


def login_window():
    global CURRENT_WINDOW, LOGIN_UI
    if CURRENT_WINDOW:
        CURRENT_WINDOW.hide()

    MainWindow, ui = windows.login.get_window()
    CURRENT_WINDOW = MainWindow
    ui.pushButton_4.clicked.connect(register_window)
    ui.pushButton.clicked.connect(lambda x: ui.show_hide())
    ui.pushButton_2.clicked.connect(login)
    ui.submit_shortcut.activated.connect(login)
    LOGIN_UI = ui
    MainWindow.show()


# def main():


try:
    with open('_session.pickle','rb') as file:
        token = pickle.load(file)
except FileNotFoundError:
    login_window()
else:
    mainSocket.send(packet(path='session',session=token))
    status = recv(mainSocket)
    if status.get('succsess',None):
        SESSION_TOKEN = token
        CURRENT_USER = status['user']
        main_window()
    else:
        login_window()
APP.exec()


# if __name__ == '__main__':
#     main()
