from .exceptions import CommandError, CommandAlreadyRegistered
import sys


class MatchCompleter:
    def __init__(self, l):
        l = list(l)
        self.list = l[:]
        self.list.append(None)


class NoMatchCompleter:
    def __init__(self, l):
        l = list(l)
        self.list = l[:]
        self.list.append(None)


class Store:
    def __init__(self, ref={}):
        for i in ref:
            if isinstance(ref[i], dict):
                ref[i] = Store(ref[i])
            setattr(self, i, ref[i])

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = Store(value)
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key, None)


class Context:
    def __init__(self, args, app, **kwargs):
        _args = args.split(' ')
        args_ = []
        for _arg in _args:
            if _arg == ' ' or _arg == '':
                continue
            args_.append(_arg)

        self.args = args_
        self.argnum = len(self.args)
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])

        self.store = app.store
        comp = kwargs.get('completer', None)
        if comp:
            self.MatchCompleter = MatchCompleter
            self.NoMatchCompleter = NoMatchCompleter

    def __repr__(self) -> str:
        string = ''
        for p, value in vars(self).items():
            string += f'{p} : {value}\n'

        return string


class Command:
    def __init__(self, name, callback, description='', threadable=True, hidden=False):
        self.description = description
        self.name = name
        self.callback = callback
        self.completer_func = None
        self.error_handler = None
        self.threadable = threadable
        self.hidden = hidden
        self.instance = getattr(callback, 'instance', None)

    def __call__(self, ctx):
        try:
            if self.instance:
                self.callback(self.instance, ctx)
            else:
                self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            raise CommandError(
                ctx, e, info)

    def completer(self, func):
        if not callable(func):
            raise ValueError('Completer function must be callable')

        self.completer_func = func
        return func

    def error(self, func):
        if not callable(func):
            raise ValueError('Error handler function must be callable')

        self.error_handler = func
        return func


class Module:
    def __init__(self, name, description=''):
        self.name = name
        self.description = description
        self.commands = []

    def add_command_(self, command):
        if not isinstance(command, Command):
            raise ValueError('Command must be an instance of command')

        self.command_check(command.name)
        self.commands.append(command)

    def command_check(self, name):
        for command in self.commands:
            if command.name == name:
                raise CommandAlreadyRegistered(
                    f'{name} is already registered as a command')

    def command(self, name=None, description='', aliases=[]):
        def wrapper(func):
            if not callable(func):
                raise ValueError('Command function must be callable')

            cmd_name = name or func.__name__
            if aliases:
                for alias in aliases:
                    cmd = Command(alias, func, description)
                    self.add_command_(cmd)

            cmd = Command(cmd_name, func, description)
            self.add_command_(cmd)
            return cmd

        return wrapper

    def add_submodule(self, module):
        if not isinstance(module, __class__):
            raise ValueError('Module must be an instance Module class')

        self.commands.append(module)
