from .types import Command, Store, NoMatchCompleter, MatchCompleter, Context, Module
from .exceptions import CommandError
from .basecommands import BaseCommands
import os
import readline
import collections.abc
import sys
import traceback


def command(name=None, description=''):
    def wrapper(func):
        if not callable(func):
            raise ValueError('Command function must be callable')
        cmd_name = name or func.__name__
        return Command(cmd_name, func, description)

    return wrapper


class Application:
    def __init__(self):
        self.modules = []
        self.events = {}
        self.indentation = []
        self.base_commands = []
        self.spacer = '::'
        self.lock_cli = False
        self.events_loaded = False
        self._input_stop = False
        self.store = Store()
        self._invoking = None
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.complete)
        self.kill_on_exit = False
        # self.ctrl_c_signal = signal.signal(
        #     signal.SIGINT, lambda x, y: self.run_event('ctrl_c_event'))
        if os.name == 'nt':
            self.windows = True
        else:
            self.windows = False

    def complete(self, text, state):
        l = []
        raw_l = []

        for i in readline.get_line_buffer().lstrip().split(' '):
            raw_l.append(i)
            if i != '' or i != ' ':
                l.append(i)

        if len(l) == 1:
            if not self.indentation:
                cmds = list(map(lambda x: x.name, self.modules))

            else:
                cmds = list(
                    map(lambda x: x.name, self.indentation[-1].commands))

            cmds.extend(list(map(lambda x: x.name, self.base_commands)))
            results = [x for x in cmds if x.startswith(text)] + [None]
            r = results[state]
            return r

        else:
            cmd = self.get_command(l[0])
            if cmd is None:
                return None
            if cmd.completer_func is None:
                return None
            l1 = l[:]
            l1.pop(0)

            args = ' '.join(l1)
            completions = cmd.completer_func(
                Context(args, self, completer=True))

            if isinstance(completions, collections.abc.Iterable):
                completions = list(completions)
                results = [
                    x for x in completions if x.startswith(text)] + [None]
                r = results[state]
                return r
            elif isinstance(completions, MatchCompleter):
                results = [
                    x for x in completions.list if x.startswith(text)] + [None]
                r = results[state]
                return r
            elif isinstance(completions, NoMatchCompleter):
                return completions.list[state]

            else:
                raise ValueError(
                    'Completion must be list, MatchCompleter or NoMatchCompleter')

    def exit_app(self):
        self._input_stop = True
        if self.kill_on_exit:
            self.kill_app()
        sys.exit()

    def kill_app(self, status=0):
        print()
        os._exit(status)

    def get_command(self, command):
        if not self.indentation:
            for i in self.base_commands:
                if i.name == command:
                    return i

        else:
            cmds = self.indentation[-1].commands[:]
            cmds.extend(self.base_commands)
            for i in cmds:
                if isinstance(i, Module):
                    continue
                if i.name == command:
                    return i

    def add_module(self, module):
        if not isinstance(module, Module):
            raise ValueError('Module must be an instance Module class')
        self.modules.append(module)

    def input_event(self, inp):
        inp = inp.lstrip()
        for base in self.base_commands:
            if base.name == inp.split(' ')[0]:
                try:
                    self._invoking = base
                    base(Context(inp.replace(base.name, '').strip(),
                         self, command=base))

                    self._invoking = None

                except CommandError as e:
                    if base.error_handler:
                        return base.error_handler(e.ctx, e.error)
                    if self.isevent('on_command_error'):
                        return self.run_event('on_command_error', e.ctx, e.error)

                    raise e

                return 0

        if self.indentation != []:
            indentation = self.indentation[-1].commands

        else:
            indentation = self.modules
        for command in indentation:
            if command.name == inp.split(' ')[0]:
                if isinstance(command, Command):
                    try:
                        self._invoking = command
                        command(
                            Context(inp.replace(command.name, '').strip(), self, command=command))

                        self._invoking = None

                    except CommandError as e:
                        if command.error_handler:
                            return command.error_handler(e.ctx, e.error)
                        if self.on_command_error:
                            return self.run_event('on_command_error', e.ctx, e.error)
                        raise e

                    return 0

                else:
                    if self.lock_cli:
                        return
                    self.indentation.append(command)
                    self.run_event('indentation_changed',
                                   Context('None', self))
                    return 0

        self.run_event('command_not_found', Context(
            '', self, command=inp.split(' ')[0]))

    def isevent(self, event):
        return event in self.events

    def event(self,  event_name=None):
        self.load_events()

        def wrapper(func):
            name = event_name
            if event_name is None:
                name = func.__name__

            if not callable(func):
                raise ValueError('Event must be callable')

            self.events[name] = func
        return wrapper

    def get_indentation(self):
        if not self.indentation:
            return ''

        indentation = list(map(lambda x: x.name, self.indentation))
        return ' '.join(indentation)

    def _run_event(self, event, *args, **kwargs):
        ev = self.events.get(event, False)
        if ev:
            ret = ev(*args, **kwargs)
            return ret
        return None

    def run_event(self, event, *args, **kwargs):
        try:
            ret = self._run_event(event, *args, **kwargs)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            self._run_event('on_event_error', e, event, sys.exc_info())
        return ret

    def quit_event(self):
        self.exit_app()

    def eof_event(self):
        print()
        self.exit_app()

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(
            exc_info[0], exc_info[1], exc_info[2])
        print(f'\nthis error occurred in {event}')
        sys.exit()

    def on_command_error(self, ctx, error):
        if isinstance(error, KeyboardInterrupt):
            return
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f'\nthis error occurred in {ctx.command.name}')
        sys.exit()

    def input_loop(self):
        self.run_event('on_ready')
        while True:
            if self._input_stop:
                return
            try:
                INP = input(f'{self.get_indentation()}>')
                self.run_event('on_input', INP)

            except KeyboardInterrupt:
                self.run_event('on_quit')
                continue
            except EOFError:
                self.run_event('eof')
                continue

    def deafault_indentation(self, *ind, lock=False):
        for i in ind:
            if not isinstance(i, Module):
                raise ValueError('Indentation list must contain only modules')
        self.lock_cli = lock
        self.indentation = list(ind)

    def main_menu(self):
        if self.indentation:
            return self.run_event('indentation_changed', Context('None', self))
        message = ''

        base_names = list(map(lambda x: x.name, self.base_commands))
        _spacer1 = max(len(s) for s in base_names)
        mod_names = list(map(lambda x: x.name, self.modules))
        if mod_names:
            _spacer = max(len(s) for s in mod_names)
            if _spacer > _spacer1:
                _spacer1 = _spacer
            else:
                _spacer = _spacer1
            spacer = ' ' * _spacer

        spacer1 = ' ' * _spacer1

        for module in self.modules:
            _s = _spacer-len(module.name)
            if _s == 0:

                s = ''
            s = ' '*_s
            if module.description:
                message += f'\n|-- {module.name}{s}{spacer}{self.spacer}  {module.description}'
            else:
                message += f'\n|-- {module.name}'

        m2 = ''
        for sub in self.base_commands:
            _s = _spacer1-len(sub.name)
            if _s == 0:
                s = ''

            s = ' '*_s
            if sub.description:
                m2 += f'\n|-- {sub.name}{s}{spacer1}{self.spacer}  {sub.description}'

            else:
                m2 += f'\n|-- {sub.name}'

        print('Base commands', end='')
        print(m2)
        print('\n')
        print('Modules', end='')
        print(message)
        print()

    def command_not_found(self, ctx):
        print('The command you entered does not exist.')

    def indentation_changed(self, ctx):
        self.basecmd.help(ctx)

    def module(self, name, description=''):
        module = Module(name, description=description)
        self.add_module(module)
        return module

    def load_events(self):
        if self.events_loaded:
            return
        self.events_loaded = True
        self.events['on_input'] = self.input_event
        self.events['on_quit'] = self.quit_event
        self.events['eof'] = self.eof_event
        self.events['command_not_found'] = self.command_not_found
        self.events['indentation_changed'] = self.indentation_changed
        self.events['on_command_error'] = self.on_command_error
        self.events['on_event_error'] = self.on_event_error
        self.events['kill_app'] = self.kill_app
        self.events['ctrl_c_event'] = self.ctrl_c_event

    def ctrl_c_event(self):
        if self._invoking:
            if self._invoking.error_handler:
                return self._invoking.error_handler(
                    Context('', self), KeyboardInterrupt())

        self.run_event('kill_app')

    def load_base_commands(self):

        basecmd = BaseCommands()
        self.basecmd = basecmd
        self.base_commands.append(
            Command('help', basecmd.help, 'Shows this help message'))

        self.base_commands.append(
            Command('..', basecmd.back, 'Goes back'))

        self.base_commands.append(
            Command('exit', basecmd.exit, 'Exits the application'))

        self.base_commands.append(
            Command('clear', basecmd.clear, 'Clears the screen'))
        shell = Command('$', basecmd.shell_command, 'Runs a shell command')
        self.base_commands.append(shell)
        thread_cmd = Command('thread', basecmd.run_in_thread,
                             'Runs command in thread')
        self.base_commands.append(thread_cmd)

        @shell.completer
        def shell_completer(ctx):
            if not getattr(ctx.app.store, '_shell_commands', None):
                shell_commands = []
                for i in os.getenv('path').split(';'):
                    if not os.path.exists(i):
                        continue
                    for j in os.listdir(i):
                        _type = os.path.splitext(f'{i}\\{j}')[1].lower()
                        if not _type == '.exe' or _type == '.bat':
                            continue
                        shell_commands.append(j)

                ctx.app.store._shell_commands = shell_commands
            return ctx.app.store._shell_commands

        @thread_cmd.completer
        def thread_completer(ctx):
            cmds = ctx.app.indentation[-1].commands[:]
            cmds.extend(ctx.app.base_commands)
            return list(map(lambda x: x.name, cmds))

    def run(self):
        self.load_events()
        self.load_base_commands()
        self.main_menu()
        self.input_loop()
