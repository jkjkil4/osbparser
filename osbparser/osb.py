from __future__ import annotations

import copy
import itertools as it
from dataclasses import dataclass
from logging import WARNING
from typing import (Any, Callable, Generator, Generic, NoReturn, Self, TypeVar,
                    overload)

from osbparser.enums import (Easing, Layer, LoopType, Origin, Parameter,
                             Trigger, find_enum_by_name, find_enum_by_value)
from osbparser.exception import (InvalidObjectTypeError, InvalidSectionError,
                                 MultipleSectionError, SubCommandNotSupported,
                                 WrongArgumentCount)
from osbparser.logger import log
from osbparser.tree import Tree, file2tree, str2tree
from osbparser.utils import get_default, get_first_part, split_parts

__all__ = [
    'OsuStoryboard',
    'Events',
    'Sprite',
    'Animation',
    'FlattenedCommands',
    'ClassifiedCommands',
    'Command',
    'SimpleCommand',
    'CmdFade',
    'CmdMove',
    'CmdMoveX',
    'CmdMoveY',
    'CmdScale',
    'CmdVectorScale',
    'CmdRotate',
    'CmdColour',
    'CmdLoop',
    'CmdEventTriggeredLoop',
    'CmdParameter'
]

EVENTS_SECTION_NAME = '[Events]'

ObjT = TypeVar('ObjT', bound='Object')
ObjU = TypeVar('ObjU', bound='Object')
CmdT = TypeVar('CmdT', bound='SimpleCommand')

ClassifiedCommandsDict = dict[type['SimpleCommand'], list['SimpleCommand']]


@dataclass
class OsuStoryboard:
    '''
    Use :meth:`from_file` to load from a ``.osb`` file.

    Use :meth:`from_str` to load from a string, which has the content like ``.osb`` file.
    '''
    name: str
    events: Events

    @staticmethod
    def from_tree(tree: Tree) -> OsuStoryboard:
        keys_to_be_taken = (EVENTS_SECTION_NAME,)
        taken: dict[str, Tree] = {}

        (_, name), children = tree
        for child in children:
            lineno, key = child[0]

            if key not in keys_to_be_taken:
                raise InvalidSectionError(f'Invalid section {key} at line {lineno}.')

            if key in taken:
                raise MultipleSectionError(f'Section {key} appeared more than once, at line {lineno}.')

            taken[key] = child

        events = Events.from_tree(taken[EVENTS_SECTION_NAME])

        return OsuStoryboard(name, events)

    @staticmethod
    def from_file(file_path: str, root_name: str | None = None) -> OsuStoryboard:
        return OsuStoryboard.from_tree(file2tree(file_path, root_name))

    @staticmethod
    def from_str(text: str, root_name: str = '') -> OsuStoryboard:
        return OsuStoryboard.from_tree(str2tree(text, root_name))


@dataclass
class Events:
    '''
    The ``[Events]`` section of ``.osb`` file.
    '''
    objects: list[Object]

    @staticmethod
    def from_tree(tree: Tree):
        return Events([Object.from_tree(child) for child in tree[1]])


OBJECT_NAME_MAP: dict[str, type[Object]] = {}


@dataclass
class Object:
    '''
    The base class of :class:`Sprite` and :class:`Animation`
    '''
    lineno: int

    commands: list[Command]
    layer: Layer
    origin: Origin
    file: str
    x: float
    y: float

    @staticmethod
    def from_tree(tree: Tree) -> Object:
        lineno, text = tree[0]
        name = get_first_part(text)
        try:
            cls = OBJECT_NAME_MAP[name]
        except KeyError:
            raise InvalidObjectTypeError(f'Invalid object type "{name}" at line {lineno}.')

        return cls.from_tree(tree)

    def flatten(self) -> FlattenedCommands[Self]:
        return FlattenedCommands.from_object(self)


class Sprite(Object):
    @staticmethod
    def from_tree(tree: Tree) -> Sprite:
        (lineno, text), children = tree

        args = split_parts(text)[1:]
        if len(args) != 5:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}, '
                                     f'expected 5, found {len(args)}')

        s_layer, s_origin, file, s_x, s_y = args
        layer = find_enum_by_name(Layer, s_layer, lineno)
        origin = find_enum_by_name(Origin, s_origin, lineno)
        x = float(s_x)
        y = float(s_y)

        command_groups = (Command.from_tree(child) for child in children)
        commands = list(it.chain.from_iterable(command_groups))

        return Sprite(lineno, commands, layer, origin, file, x, y)


@dataclass
class Animation(Object):
    frame_count: int
    frame_delay: float
    looptype: LoopType

    @staticmethod
    def from_tree(tree: Tree) -> Animation:
        (lineno, text), children = tree

        args = split_parts(text)[1:]
        if len(args) != 8:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}, '
                                     f'expected 8, found {len(args)}')

        s_layer, s_origin, file, s_x, s_y, s_frame_count, s_frame_delay, s_looptype = args
        layer = find_enum_by_name(Layer, s_layer, lineno)
        origin = find_enum_by_name(Origin, s_origin, lineno)
        x = float(s_x)
        y = float(s_y)
        frame_count = int(s_frame_count)
        frame_delay = float(s_frame_delay)
        looptype = find_enum_by_name(LoopType, s_looptype, lineno)

        command_groups = (Command.from_tree(child) for child in children)
        commands = list(it.chain.from_iterable(command_groups))

        return Animation(lineno, commands, layer, origin, file, x, y, frame_count, frame_delay, looptype)


OBJECT_NAME_MAP['Sprite'] = Sprite
OBJECT_NAME_MAP['Animation'] = Animation


@dataclass
class FlattenedCommands(Generic[ObjT]):
    '''
    Flatten commands

    The ``commands`` list includes only :class:`SimpleCommand`,
    which means contents of :class:`CmdLoop` have been parsed into :class:`SimpleCommand` objects,
    and the contents of :class:`CmdEventTriggeredLoop` are ignored.
    '''
    obj: ObjT
    commands: list[SimpleCommand]

    @staticmethod
    def from_object(obj: ObjU) -> FlattenedCommands[ObjU]:
        return FlattenedCommands(obj, FlattenedCommands.parse(obj.commands))

    @overload
    def __getitem__(self, i: int) -> SimpleCommand: ...
    @overload
    def __getitem__(self, s: slice) -> list[SimpleCommand]: ...

    def __getitem__(self, v):
        return self.commands[v]

    def __len__(self) -> int:
        return len(self.commands)

    def classify(self) -> ClassifiedCommands[ObjT]:
        return ClassifiedCommands.from_flatten(self)

    @staticmethod
    def parse(commands: list[Command]) -> list[SimpleCommand]:
        result: list[SimpleCommand] = []

        for cmd in commands:
            if isinstance(cmd, SimpleCommand):
                result.append(copy.copy(cmd))

            elif isinstance(cmd, CmdLoop):
                subcommands = FlattenedCommands.parse(cmd.children)
                duration = 0

                for subcmd in subcommands:
                    duration = max(duration, subcmd.end)
                    # Because subcmd here is copied through the flatten function
                    # so we can modify the value directly without side effects
                    subcmd.start += cmd.starttime
                    subcmd.end += cmd.starttime

                result.extend(subcommands)
                for i in range(1, cmd.loopcount):
                    for subcmd in subcommands:
                        subcmd_copy = copy.copy(subcmd)
                        offset = i * duration
                        subcmd_copy.start += offset
                        subcmd_copy.end += offset
                        result.append(subcmd_copy)

        return result

    def get_start(self) -> int:
        '''
        Get the start of available range.
        '''
        return min(cmd.start for cmd in self.commands)

    def get_end(self) -> int:
        '''
        Get the end of available range.
        '''
        return max(cmd.end for cmd in self.commands)


@dataclass
class ClassifiedCommands(Generic[ObjT]):
    '''
    Commands classified into different types
    '''
    obj: ObjT
    flatten: FlattenedCommands[ObjT]
    commands: ClassifiedCommandsDict

    @staticmethod
    def from_flatten(flatten: FlattenedCommands[ObjU]) -> ClassifiedCommands[ObjU]:
        return ClassifiedCommands(flatten.obj, flatten, ClassifiedCommands.parse(flatten.commands))

    def __getitem__(self, key: type[CmdT]) -> list[CmdT]:
        return self.commands[key]

    def visible_ranges(self) -> Generator[tuple[int, int], None, None]:
        '''
        Iterates the visible time-ranges of the object.

        It is determined by the available range and :class:`CmdFade` command.
        '''
        if not self.flatten:
            return

        fade_cmds = self[CmdFade]
        start = self.flatten.get_start()
        for cmd in fade_cmds:
            if start is None and (cmd.start_opacity != 0 or cmd.end_opacity != 0):
                start = cmd.start
            if start is not None and cmd.end_opacity == 0:
                yield (start, cmd.end)
                start = None

        if start is not None:
            yield (start, self.flatten.get_end())

    @staticmethod
    def parse(commands: list[SimpleCommand]) -> ClassifiedCommandsDict:
        result: ClassifiedCommandsDict = {
            key: []
            for key in (CmdFade,
                        CmdMove, CmdMoveX, CmdMoveY,
                        CmdScale, CmdVectorScale,
                        CmdRotate,
                        CmdColour,
                        CmdParameter)
        }
        for cmd in commands:
            lst = result.get(cmd.__class__, None)
            if lst is not None:
                lst.append(cmd)
        return result


COMMAND_NAME_MAP: dict[str, type[Command]] = {}


@dataclass
class Command:
    '''
    The base class of commands
    '''
    lineno: int

    @staticmethod
    def from_tree(tree: Tree) -> list[Command]:
        lineno, text = tree[0]
        name = get_first_part(text)
        try:
            cls = COMMAND_NAME_MAP[name]
        except KeyError:
            raise InvalidObjectTypeError(f'Invalid command type "{name}" at line {lineno}.')

        return cls.from_tree(tree)

    @staticmethod
    def get_cmd_name(cls: type[Command]) -> str:
        for key, value in COMMAND_NAME_MAP.items():
            if value is cls:
                return key
        assert False

    @classmethod
    def raise_if_has_children(
        cls,
        children: list[Tree],
        lineno: int
    ) -> None | NoReturn:
        if children:
            cmd_name = Command.get_cmd_name(cls)
            raise SubCommandNotSupported(f'Command "{cmd_name}" at line {lineno} does not support subcommand.')

    @classmethod
    def raise_if_wrong_count(
        cls,
        args: list[str],
        one_arg_len: int,
        lineno: int
    ) -> None | NoReturn:
        length = len(args) - 3
        if length < one_arg_len or length % one_arg_len != 0:
            cmd_name = Command.get_cmd_name(cls)
            raise WrongArgumentCount(f'Wrong argument count of "{cmd_name}" at line {lineno}.')

    @classmethod
    def parse_args(
        cls,
        args: list[str],
        one_arg_len: int,
        lineno: int
    ) -> Generator[tuple[Easing, int, int, tuple[str, ...]], None, None]:
        cls.raise_if_wrong_count(args, one_arg_len, lineno)

        easing, start, end = cls.parse_time_args(*args[:3], lineno)
        duration = end - start

        for attrs in cls.parse_attr_args(args[3:], one_arg_len):
            yield (easing, start, end, attrs)
            start += duration
            end += duration

    @staticmethod
    def parse_time_args(s_easing: str, s_start: str, s_end: str, lineno: int) -> tuple[Easing, int, int]:
        # parse shorthand2
        if not s_end:
            s_end = s_start
        return (
            find_enum_by_value(Easing, int(s_easing), lineno),
            int(s_start),
            int(s_end)
        )

    @staticmethod
    def parse_attr_args(args: list[str], one_arg_len: int) -> Generator[tuple[str, ...]]:
        # parse shorthand & shorthand3
        length = len(args)
        if length != one_arg_len:
            length -= one_arg_len
        for i in range(0, length, one_arg_len):
            part1 = args[i: i + one_arg_len]
            part2 = [
                get_default(args, i + one_arg_len + j) or part1[j]     # parse shorthand3
                for j in range(one_arg_len)
            ]
            yield (*part1, *part2)


@dataclass
class SimpleCommand(Command):
    '''
    The base class of commands that have ``easing`` method and ``start`` ``end`` timestamps.
    '''
    easing: Easing
    start: int
    end: int

    def is_instant(self) -> bool:
        return self.start == self.end


class AnimCommand(SimpleCommand):
    '''
    The base class of commands that have animation process.
    '''
    @classmethod
    def from_tree(cls, tree: Tree, one_arg_len: int, *, factory: Callable[[str], Any] = float) -> list[Self]:
        (lineno, text), children = tree
        cls.raise_if_has_children(children, lineno)

        args = split_parts(text)[1:]

        return [
            cls(lineno, easing, start, end, *[factory(a) for a in attrs])
            for easing, start, end, attrs
            in cls.parse_args(args, one_arg_len, lineno)
        ]


@dataclass
class CmdFade(AnimCommand):
    '''
    ``startopacity``: the opacity at the beginning of the animation
    ``endopacity``: the opacity at the end of the animation

    ``0`` - invisible, ``1`` - fully visible
    '''
    start_opacity: float
    end_opacity: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 1)


@dataclass
class CmdMove(AnimCommand):
    '''
    ``startx, starty``: the position at the beginning of the animation
    ``endx, endy``: the position at the end of the animation

    Note: the size of the play field is ``(640,480)``, with ``(0,0)`` being top left corner.
    '''
    startx: float
    starty: float
    endx: float
    endy: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 2)


@dataclass
class CmdMoveX(AnimCommand):
    '''
    ``startx``: the x position at the beginning of the animation
    ``endx``: the x position at the end of the animation
    '''
    startx: float
    endx: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 1)


@dataclass
class CmdMoveY(AnimCommand):
    '''
    ``starty``: the y position at the beginning of the animation
    ``endy``: the y position at the end of the animation
    '''
    starty: float
    endy: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 1)


@dataclass
class CmdScale(AnimCommand):
    '''
    ``startscale``: the scale factor at the beginning of the animation
    ``endscale``: the scale factor at the end of the animation

    ``1 = 100%``, ``2 = 200%`` etc. decimals are allowed.
    '''
    startscale: float
    endscale: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 1)


@dataclass
class CmdVectorScale(AnimCommand):
    '''
    ``startx, starty``: the scale factor at the beginning of the animation
    ``endx, endy``: the scale factor at the end of the animation

    ``1 = 100%``, ``2 = 200%`` etc. decimals are allowed.
    '''
    startx: float
    starty: float
    endx: float
    endy: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 2)


@dataclass
class CmdRotate(AnimCommand):
    '''
    ``startangle``: the angle to rotate by in radians at the beginning of the animation
    ``endangle``: the angle to rotate by in radians at the end of the animation

    positive angle is clockwise rotation
    '''
    startangle: float
    endangle: float

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 1)


@dataclass
class CmdColour(AnimCommand):
    '''
    ``r1, g1, b1``: the starting component-wise colour
    ``r2, g2, b2``: the finishing component-wise colour

    - sprites with ``(255,255,255)`` will be their original colour.
    - sprites with ``(0,0,0)`` will be totally black.
    - anywhere in between will result in subtractive colouring.
    - to make full use of this, brighter greyscale sprites work very well.
    '''
    r1: int
    g1: int
    b1: int
    r2: int
    g2: int
    b2: int

    @classmethod
    def from_tree(cls, tree: Tree) -> list[Self]:
        return super().from_tree(tree, 3, factory=int)


@dataclass
class CmdLoop(Command):
    '''
    ``starttime``: the time of the first loop's start.
    ``loopcount``: number of times to repeat the loop.

    Note that events inside a loop should be timed with a zero-base.
    This means that you should start from 0ms for the inner event's timing and work up from there.
    The loop event's start time will be added to this value at game runtime.
    '''
    starttime: int
    loopcount: int
    children: list[Command]

    def __post_init__(self) -> None:
        if not log.isEnabledFor(WARNING):
            return

        for cmd in self.children:
            if not isinstance(cmd, SimpleCommand):
                log.warning(f'Nested loop at line {cmd.lineno} '
                            'may not be displayed in osu! correctly.')

    @staticmethod
    def from_tree(tree: Tree) -> list[CmdLoop]:
        (lineno, text), children = tree

        args = split_parts(text)[1:]
        if len(args) != 2:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}, '
                                     f'expected 2, found {len(args)}')

        s_starttime, s_loopcount = args
        command_groups = (Command.from_tree(child) for child in children)
        commands = list(it.chain.from_iterable(command_groups))

        return [CmdLoop(lineno, int(s_starttime), int(s_loopcount), commands)]


@dataclass
class CmdEventTriggeredLoop(Command):
    '''
    Trigger loops can be used to trigger animations based on play-time events.
    Although called loops, trigger loops only execute once when triggered.

    ``start``: When the trigger is valid
    ``end``: When the trigger stops being valid

    Trigger loops are zero-based similar to normal loops.
    If two overlap, the first will be halted and replaced by a new loop from the beginning.
    If they overlap any existing storyboarded events,
    they will not trigger until those transformations are no in effect.
    '''
    trigger: Trigger
    start: int
    end: int
    children: list[Command]

    @staticmethod
    def from_tree(tree: Tree) -> list[CmdEventTriggeredLoop]:
        (lineno, text), children = tree

        args = split_parts(text)[1:]
        if len(args) != 3:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}, '
                                     f'expected 3, found {len(args)}')

        s_trigger, s_start, s_end = args
        trigger = find_enum_by_name(s_trigger)
        start = int(s_start)
        end = int(s_end)

        return [CmdEventTriggeredLoop(lineno, trigger, start, end, [Command.from_tree(child) for child in children])]


@dataclass
class CmdParameter(SimpleCommand):
    '''
    Unlike the other commands, which can be seen as setting endpoints
    along continually-tracked values, the Parameter command apply
    ONLY while they are active, i.e.,you can't put a command
    from timestamps 1000 to 2000 and expect the value to apply at time 3000,
    even if the object's other commands aren't finished by that point.

    - ``H``: flip the image horizontally.
    - ``V``: flip the image vertically.
    - ``A``: use additive-colour blending instead of alpha-blending.
    '''
    parameter: Parameter

    @classmethod
    def from_tree(cls, tree: Tree) -> list[CmdParameter]:
        (lineno, text), children = tree
        cls.raise_if_has_children(children, lineno)

        args = split_parts(text)[1:]
        if len(args) != 4:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}.')

        easing, start, end = cls.parse_time_args(*args[:3], lineno)

        return [CmdParameter(lineno, easing, start, end, find_enum_by_name(Parameter, args[3], lineno))]


COMMAND_NAME_MAP['F'] = CmdFade
COMMAND_NAME_MAP['M'] = CmdMove
COMMAND_NAME_MAP['MX'] = CmdMoveX
COMMAND_NAME_MAP['MY'] = CmdMoveY
COMMAND_NAME_MAP['S'] = CmdScale
COMMAND_NAME_MAP['V'] = CmdVectorScale
COMMAND_NAME_MAP['R'] = CmdRotate
COMMAND_NAME_MAP['C'] = CmdColour
COMMAND_NAME_MAP['L'] = CmdLoop
COMMAND_NAME_MAP['T'] = CmdEventTriggeredLoop
COMMAND_NAME_MAP['P'] = CmdParameter
