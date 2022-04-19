from .types import Module as _Module
from .types import Command
import inspect


class Module():
    def __new__(cls):
        CLASS = super().__new__(cls)
        commands = []
        for i in dir(CLASS):
            kv = getattr(CLASS, i)
            if isinstance(kv, Command) or isinstance(kv, _Module):
                commands.append(kv)
        name = getattr(cls, 'name', None) or cls.__name__
        description = getattr(cls, 'description', '')
        module = _Module(name, description)
        module.commands = commands
        cls.__init__(CLASS)
        return module

    def __init__(self):
        for k, v in inspect.getmembers(self):
            if isinstance(v, Command):
                v.instance = self
                setattr(self, k, v)
