import socket
import threading
import zono.colorlogger
import zono.zonocrypt
import secrets
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.asymmetric.padding
import data
import zono.cli
import time




DataManeger = data.DataManeger()

Crypt = zono.zonocrypt.zonocrypt()

objcrypt = zono.zonocrypt.objcrypt(
    hash_algorithm=zono.zonocrypt.objcrypt.SHA512)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 80))
ipaddr = s.getsockname()[0]
s.close()

IP = 'localhost'
PORT = 4245
HEADER = 512
FORMAT = 'utf-8'
IP_GLOBAL = IP
KEY_UPPERBOUND = 100000000


ALLOWED_VERSIONS = ('V1.0',)
LATEST_VERSION = 'V1.0'

ADDR_SEESION_KEY = {}
TYPING = {}


CONNECTED_ADDRS_TO_SESSION = {}
EVENT_SOCKETS = {}
CONN_ADDR = {}

PATHS_TO_FUNCS = {}


def log(msg, log_type=zono.colorlogger.log):
    log_type(msg)


def packet(**kwargs):
    pkt = {}
    for k, v in kwargs.items():
        pkt[k] = v

    return pkt


def send(pkt, conn, address):
    message = objcrypt.encrypt(pkt, ADDR_SEESION_KEY[address])

    msg_length = len(message)

    send_length = str(msg_length).encode(FORMAT)

    send_length += b' ' * (HEADER - len(send_length))

    conn.send(send_length)
    conn.send(message)


def recv(client, address):
    try:
        msg_len = int(client.recv(HEADER).decode(FORMAT))
    except ValueError:
        raise socket.error
    msg = client.recv(msg_len)
    obj = objcrypt.decrypt(msg, ADDR_SEESION_KEY[address])
    return obj


def send_raw(pkt, conn):
    message = objcrypt.encode(pkt)
    msg_length = len(message)

    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))

    conn.send(send_length)
    conn.send(message)


def recv_raw(client):
    msg_len = int(client.recv(HEADER).decode(FORMAT))
    msg = client.recv(msg_len)
    msg = objcrypt.decode(msg)
    return msg


if IP != ipaddr:
    log(
        f'mismatching ip private address correct ip: {ipaddr},Automaticaly switched to correct ip', log_type=zono.colorlogger.error)
    IP = ipaddr
    IP_GLOBAL = IP


def request(path):
    def wrapper(func):
        PATHS_TO_FUNCS[path] = func

    return wrapper


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((IP, PORT))
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.listen()


def recv_loop(conn, addr):
    while True:
        try:
            pkt = recv(conn, addr)
            path = pkt.get('path', None)
            if path in PATHS_TO_FUNCS:
                PATHS_TO_FUNCS[path](conn, addr, pkt)

            else:
                send(packet(status=404, info='Path not found',error=True), conn, addr)

        except socket.error as e:
            CONNECTED_ADDRS_TO_SESSION.pop(addr,None)
            log(f'{addr} disconnected {e}')
            break


def add_session_event(event, to):
    _recv_session = DataManeger.get_session_user(to)
    if not _recv_session:
        return

    if _recv_session in CONNECTED_ADDRS_TO_SESSION.values():
        print(event)
        DataManeger.add_session_event(_recv_session['session'], event)

def send_session_event(event,to):
    _recv_session = DataManeger.get_session_user(to)
    if not _recv_session:
        return

    if _recv_session in CONNECTED_ADDRS_TO_SESSION.values():
        _conn = EVENT_SOCKETS.get(_recv_session['session'],None)
        if not _conn:
            return
        send(event,_conn,CONN_ADDR[_conn])

def handle_client(conn, addr):
    log(f'{addr} Connected')
    echo_pkt = recv_raw(conn)
    num1 = echo_pkt['num']

    private_key = cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
        public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    pem = public_key.public_bytes(encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
                                  format=cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo)

    num2 = secrets.randbelow(KEY_UPPERBOUND)
    send_raw(packet(pem=pem, kdn=num2), conn)

    num_3_enc = recv_raw(conn)['num']

    _num3 = private_key.decrypt(
        num_3_enc,
        cryptography.hazmat.primitives.asymmetric.padding.OAEP(
            mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                algorithm=cryptography.hazmat.primitives.hashes.SHA384()),
            algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
            label=None
        )
    )
    num3 = int(_num3.decode('utf-8'))

    key_deriv = str(num1*num2*num3)

    key = Crypt.hashing_function(key_deriv)
    ADDR_SEESION_KEY[addr] = key
    send(packet(status=200, info='Initiated secure connection'), conn, addr)
    log(f'{addr} Initiated secure connection')
    recv_loop(conn, addr)


def accept_connections():
    server.listen()
    while True:
        conn, addr = server.accept()
        CONN_ADDR[conn]= addr
        threading.Thread(target=handle_client, args=(conn, addr,)).start()

# status:get_status
@request('status')
def get_status(conn, addr, pkt):
    USER = pkt.get('user', None)
    session = pkt.get('session', None)
    channel = pkt.get('channel', None)
    if USER and session and channel:
        pass
    else:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    connected_users = list(
        map(lambda x: CONNECTED_ADDRS_TO_SESSION[x]['user'], CONNECTED_ADDRS_TO_SESSION))
    if USER in TYPING and USER in connected_users:
        if TYPING[USER] == channel:
            return send(packet(status=200, user_status='Typing', succsess=True), conn, addr)
    else:
        TYPING.pop(USER,None)

    if USER in connected_users:
        send(packet(status=200, user_status='Online', succsess=True), conn, addr)

    else:
        send(packet(status=200, user_status='Offline', succsess=True), conn, addr)


@request('typing')
def typing(conn, addr, pkt):
    channel = pkt.get('channel', None)
    session = pkt.get('session', None)
    typing = pkt.get('typing', None)
    if channel and session:
        pass
    else:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    if typing:
        TYPING[session_status['user']] = channel
    else:
        TYPING.pop(session_status['user'],None)
    send(packet(status=200, info='Sucsess',
                succsess=True), conn, addr)


@request('login')
def login_request(conn, addr, pkt):
    USER = pkt.get('user', None)
    PASSWORD = pkt.get('password', None)
    if USER and PASSWORD:
        pass

    else:
        return send(packet(status=200, info='Incomplete form', succsess=False,error=True), conn, addr)
    if DataManeger.check_user(USER, PASSWORD):
        session = DataManeger.create_session(USER)
        if session in CONNECTED_ADDRS_TO_SESSION.values():
            return send(packet(status=200, info='Logged in from another location', succsess=False,error=True), conn, addr)

        send(packet(status=200, info='Logged In Succsesfully',
             succsess=True, session=session['session']), conn, addr)

        CONNECTED_ADDRS_TO_SESSION[addr] = session

    else:
        send(packet(status=200, info='incorrect Credentials',
             succsess=False,error=True), conn, addr)


@request('register')
def register_request(conn, addr, pkt):
    USER = pkt.get('user', None)
    PASSWORD = pkt.get('password', None)
    if USER and PASSWORD:
        pass

    else:
        return send(packet(status=200, info='Incomplete form', succsess=False,error=True), conn, addr)

    _r = DataManeger.register_user(USER, PASSWORD)
    if _r:
        session = DataManeger.create_session(USER)
        send(packet(status=200, info='Registered successfully',
             succsess=True, session=session['session']), conn, addr)
        CONNECTED_ADDRS_TO_SESSION[addr] = session

    else:
        send(packet(status=200, info='Username already taken',
             succsess=False,error=True), conn, addr)


@request('conversations')
def get_conversations(conn, addr, pkt):
    session = pkt.get('session', None)
    if not session:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    send(packet(status=200, conversations=DataManeger.get_conversations(
        session_status['user'])), conn, addr)


@request('events')
def get_events(conn, addr, pkt):
    session = pkt.get('session', None)
    if not session:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    send(packet(status=200, events=DataManeger.get_session_events(
        session_status['session'])), conn, addr)


@request('messages')
def get_messages(conn, addr, pkt):
    channel = pkt.get('channel', None)
    session = pkt.get('session', None)
    if channel and session:
        pass
    else:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True), conn, addr)

    messages = DataManeger.get_messages(channel)
    send(packet(status=200, info='Messages',
                succsess=True, messages=messages,session_error=True), conn, addr)


@request('session')
def auth_session(conn,addr,pkt):
    session = pkt.get('session', None)
    if not session:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    if session in CONNECTED_ADDRS_TO_SESSION.values():
        return send(packet(status=200, info='Logged in from another location', succsess=False,error=True), conn, addr)

    CONNECTED_ADDRS_TO_SESSION[addr] = session_status
    send(packet(status=200, info='Logged In Succsesfully',
             succsess=True, session=session,user=session_status['user']), conn, addr)


@request('send_message')
def send_message(conn, addr, pkt):
    channel = pkt.get('channel', None)
    session = pkt.get('session', None)
    message = pkt.get('message', None)
    if channel and session and message:
        pass
    else:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    conversation = DataManeger.get_conversation(channel)
    if not conversation:
        return send(packet(status=200, info='Conversation does not exist',
                    succsess=False,error=True), conn, addr)
    conversation['participants'].remove(session_status['user'])
    DataManeger.add_message(session_status['user'], message, channel)

    for participant in conversation['participants']:
        send_session_event({'type': 'new_message', 'from':
                           session_status['user'], 'channel': channel, 'message': message, 'time': time.time()}, participant)


@request('event_socket')
def register_message_socket(conn,addr,pkt):
    session = pkt.get('session', None)
    if not session:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    EVENT_SOCKETS[session] = conn
    send(packet(status=200,info='Registered socket',sucsess=True),conn,addr)
    

@request('open_private_conversation')
def open_private_conversation(conn, addr, pkt):
    USER = pkt.get('user', None)
    session = pkt.get('session', None)
    if USER and session:
        pass
    else:
        return send(packet(status=200, info='Incomplete form',
                           succsess=False,error=True), conn, addr)

    session_status = DataManeger.get_session(session)
    if session_status is None:
        return send(packet(status=200, info='Session does not exist',
                           succsess=False,error=True,session_error=True), conn, addr)
    elif session_status is False:
        return send(packet(status=200, info='Session expired relogin',
                    succsess=False,error=True,session_error=True), conn, addr)

    elif session_status['user'] == USER:
        return send(packet(status=200, info='Cant create conversation with your self',
                           succsess=False,error=True), conn, addr)

    elif not DataManeger.account_exists(USER):
        return send(packet(status=200, info='Account does not exist',
                           succsess=False,error=True), conn, addr)

    result = DataManeger.create_private_conversation(session_status['user'], USER)
    if result:
        send(packet(status=200, info='Created',
                    succsess=True,conv_id=str(result.inserted_id)), conn, addr)
        send_session_event({'type': 'new_conversation',
                          'conversation': session_status['user'],'conv_id':str(result.inserted_id)}, USER)

    else:
        send(packet(status=200, info='Conversation already exists',
                    succsess=False,error=True), conn, addr)


def command_line():
    app = zono.cli.Application()
    app.kill_on_exit = True

    app.run()


# threading.Thread(target=command_line).start()


accept_connections()
