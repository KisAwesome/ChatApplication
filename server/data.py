import pymongo
import time
import zono.zonocrypt
import secrets
import bson


class DataManeger:
    def __init__(self):
        cluster = pymongo.MongoClient('mongodb://localhost:27017')
        self.db = cluster['chatapp']
        self.crypt = zono.zonocrypt.zonocrypt()

    def register_user(self, user,  password):
        user_obj = self.db['auth'].find_one(
            {'user': user})
        if user_obj:
            return False
        salt = self.crypt.hashing_function(
            self.crypt.gen_hash().decode('utf-8'), length=32, valid_key=False)
        _password = f'{password}'
        hashed_pass = self.crypt.hashing_function(
            _password, length=128, valid_key=False,salt=salt)
        self.db['auth'].insert_one(
            {'user': user, 'salt': salt, 'password': hashed_pass})

        return True

    def check_user(self, user, password):
        user_obj = self.db['auth'].find_one({'user': user})

        if user_obj is None:
            hashed = self.crypt.hashing_function(password, length=128)
            secrets.compare_digest(hashed, user.encode('utf-8'))
            return False

        salt = user_obj['salt']
        _password = f'{password}'
        hashed_pass = self.crypt.hashing_function(
            _password, length=128, valid_key=False,salt=salt)
        if secrets.compare_digest(hashed_pass, user_obj['password']):
            return True
        return False

    def get_session(self, session):
        session_obj = self.db['sessions'].find_one({'session': session})
        if not session_obj:
            return None
        if session_obj['expireTime'] < time.time():
            self.db['sessions'].delete_many({'session': session})
            return False

        return session_obj

    def get_session_user(self, user):
        session_obj = self.db['sessions'].find_one({'user': user})
        if not session_obj:
            return None
        if session_obj['expireTime'] < time.time():
            self.db['sessions'].delete_many({'user': user})
            return False

        return session_obj

    def create_session(self, user):
        _s = self.get_session_user(user)
        if _s:
            return _s

        session_token = self.crypt.hashing_function(
            f'{user}{time.time()}', iterations=100000)

        _destroy_time = time.time()+(60*60*24*3)

        session = {'expireTime': _destroy_time,
                   'session': session_token, 'user': user, 'events': []}

        self.db['sessions'].insert_one(session)
        return session

    def account_exists(self, user):
        return self.db['auth'].find_one({'user': user}) != None

    def create_private_conversation(self, u1, u2):
        _conv = self.db['conversations'].find_one(
            {'u1': u1, 'u2': u2}) or self.db['conversations'].find_one({'u1': u2, 'u2': u1})
        if _conv:
            return False

        return self.db['conversations'].insert_one({'u1': u1, 'u2': u2})

    def get_conversations(self, user):
        conversations = {}
        for _coversation in self.db['conversations'].find({'u1': user}):
            conversations[_coversation['u2']] = [
                str(_coversation['_id']), [_coversation['u2']]]

        for _coversation in self.db['conversations'].find({'u2': user}):
            conversations[_coversation['u1']] = [
                str(_coversation['_id']), [_coversation['u1']]]

        return conversations

    def add_session_event(self, session, event):
        self.db['sessions'].update_one(
            {'session': session}, {'$push': {'events': event}})

    def get_session_events(self, session):
        events = self.db['sessions'].find_one({'session': session})['events']
        self.db['sessions'].update_one(
            {'session': session}, {'$set': {'events': []}})

        return events

    def get_conversation(self, _id):
        conversation = self.db['conversations'].find_one(
            {'_id': bson.ObjectId(_id)})
        if conversation:
            conversation['participants'] = [
                conversation['u1'], conversation['u2']]
            return conversation

    def add_message(self, sender, message, channel):
        self.db['messages'].insert_one(
            {'sender': sender, 'channel': channel, 'message': message, 'time': time.time()})

    def get_messages(self, channel):
        messages = []
        for message in self.db['messages'].find({'channel': channel}):
            message.pop('_id', None)
            messages.append(message)

        return messages



