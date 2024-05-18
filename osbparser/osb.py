from __future__ import annotations

import itertools as it
from dataclasses import dataclass
from typing import Any, Callable, Generator, Iterable, NoReturn, Self

from osbparser.enums import (Easing, Layer, Origin, Parameter, Trigger,
                             find_enum_by_name, find_enum_by_value)
from osbparser.exception import (InvalidObjectTypeError, InvalidSectionError,
                                 MultipleSectionError, SubCommandNotSupported,
                                 WrongArgumentCount)
from osbparser.tree import Tree, file2tree, str2tree
from osbparser.utils import get_default, get_first_part, split_parts

__all__ = [
    'OsuStoryboard',
    'Events',
    'Sprite',
    'Animation',
    'CmdFade',
    'CmdMove',
    'CmdScale',
    'CmdRotate',
    'CmdColour',
    'CmdLoop',
    'CmdEventTriggeredLoop',
    'CmdParameters'
]

EVENTS_SECTION_NAME = '[Events]'


@dataclass
class OsuStoryboard:
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
    objects: list[Object]

    @staticmethod
    def from_tree(tree: Tree):
        return Events([Object.from_tree(child) for child in tree[1]])


OBJECT_NAME_MAP: dict[str, type[Object]] = {}


class Object:
    @staticmethod
    def from_tree(tree: Tree) -> Object:
        lineno, text = tree[0]
        name = get_first_part(text)
        try:
            cls = OBJECT_NAME_MAP[name]
        except KeyError:
            raise InvalidObjectTypeError(f'Invalid object type "{name}" at line {lineno}.')

        return cls.from_tree(tree)


@dataclass
class Sprite(Object):
    layer: Layer
    origin: Origin
    file: str
    x: float
    y: float
    commands: list[Command]

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

        return Sprite(layer, origin, file, x, y, commands)


@dataclass
class Animation(Object):
    @staticmethod
    def from_tree(tree: Tree) -> Animation:
        raise NotImplementedError('"Animation" is not implemented.')


OBJECT_NAME_MAP['Sprite'] = Sprite
OBJECT_NAME_MAP['Animation'] = Animation

#
COMMAND_NAME_MAP: dict[str, type[Command]] = {}


class Command:
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

    @staticmethod
    def floatize(lst: Iterable[str]) -> Generator[float, None, None]:
        return


@dataclass
class SimpleCommand(Command):
    easing: Easing
    start: int
    end: int


class AttrsCommand(SimpleCommand):
    @classmethod
    def from_tree(cls, tree: Tree, one_arg_len: int, *, factory: Callable[[str], Any] = float) -> list[Self]:
        (lineno, text), children = tree
        cls.raise_if_has_children(children, lineno)

        args = split_parts(text)[1:]

        return [
            cls(easing, start, end, *[factory(a) for a in attrs])
            for easing, start, end, attrs
            in cls.parse_args(args, one_arg_len, lineno)
        ]


@dataclass
class CmdFade(AttrsCommand):
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
class CmdMove(AttrsCommand):
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
class CmdMoveX(AttrsCommand):
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
class CmdMoveY(AttrsCommand):
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
class CmdScale(AttrsCommand):
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
class CmdVectorScale(AttrsCommand):
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
class CmdRotate(AttrsCommand):
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
class CmdColour(AttrsCommand):
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

    @staticmethod
    def from_tree(tree: Tree) -> list[CmdLoop]:
        (lineno, text), children = tree

        args = split_parts(text)[1:]
        if len(args) != 2:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}, '
                                     f'expected 2, found {len(args)}')

        s_starttime, s_loopcount = args

        return [CmdLoop(int(s_starttime), int(s_loopcount), [Command.from_tree(child) for child in children])]


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

        return [CmdEventTriggeredLoop(trigger, start, end, [Command.from_tree(child) for child in children])]


@dataclass
class CmdParameters(SimpleCommand):
    parameter: Parameter

    @classmethod
    def from_tree(cls, tree: Tree) -> list[CmdParameters]:
        (lineno, text), children = tree
        cls.raise_if_has_children(children, lineno)

        args = split_parts(text)[1:]
        if len(args) != 4:
            raise WrongArgumentCount(f'Wrong argument count at line {lineno}.')

        easing, start, end = cls.parse_time_args(*args[:3], lineno)

        return [CmdParameters(easing, start, end, find_enum_by_name(Parameter, args[3]))]


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
COMMAND_NAME_MAP['P'] = CmdParameters
