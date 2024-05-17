from __future__ import annotations

import itertools as it
from dataclasses import dataclass
from typing import NoReturn

from osbparser.enums import (Easing, Layer, Origin, find_enum_key,
                             find_enum_value)
from osbparser.exception import (InvalidObjectTypeError, InvalidSectionError,
                                 MultipleSectionError, SubCommandNotSupported,
                                 WrongArgumentCount)
from osbparser.tree import Tree, file2tree, str2tree
from osbparser.utils import cover, get_first_part, safe_get, split_parts

__all__ = [
    'OsuStoryboard',
    'Events'
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
        layer = find_enum_key(Layer, s_layer, lineno)
        origin = find_enum_key(Origin, s_origin, lineno)
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


@dataclass
class Command:
    easing: Easing
    start: int
    end: int

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

    @staticmethod
    def raise_if_has_children(
        cls: type[Command],
        children: list[Tree],
        lineno: int
    ) -> None | NoReturn:
        if children:
            cmd_name = Command.get_cmd_name(cls)
            raise SubCommandNotSupported(f'Command "{cmd_name}" at line {lineno} does not support subcommand.')

    @staticmethod
    def raise_if_wrong_count(
        cls: type[Command],
        args: list[str],
        args_once: int,
        lineno: int
    ) -> None | NoReturn:
        length = len(args) - 3
        if length < args_once or length % args_once != 0:
            cmd_name = Command.get_cmd_name(cls)
            raise WrongArgumentCount(f'Wrong argument count of "{cmd_name}" at line {lineno}.')

    @staticmethod
    def parse_time_args(s_easing: str, s_start: str, s_end: str, lineno: int) -> tuple[Easing, int, int]:
        if not s_end:
            s_end = s_start
        return (
            find_enum_value(Easing, int(s_easing), lineno),
            int(s_start),
            int(s_end)
        )


@dataclass
class CmdFade(Command):
    start_opacity: float
    end_opacity: float

    @staticmethod
    def from_tree(tree: Tree) -> list[CmdFade]:
        (lineno, text), children = tree
        Command.raise_if_has_children(__class__, children, lineno)

        args = split_parts(text)[1:]
        Command.raise_if_wrong_count(__class__, args, 1, lineno)

        easing, start, end = Command.parse_time_args(*args[:3], lineno)

        args = args[3:]
        result: list[CmdFade] = []
        for i in range(0, cover(len(args), 2) * 2, 2):
            a1 = args[i]
            a2 = safe_get(args, i + 1)
            if not a2:
                a2 = a1
            result.append(CmdFade(easing, start, end, a1, a2))

        return result


@dataclass
class CmdMove(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdMove]:
        raise NotImplementedError()


@dataclass
class CmdScale(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdScale]:
        raise NotImplementedError()


@dataclass
class CmdRotate(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdRotate]:
        raise NotImplementedError()


@dataclass
class CmdColour(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdColour]:
        raise NotImplementedError()


@dataclass
class CmdLoop(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdLoop]:
        raise NotImplementedError()


@dataclass
class CmdEventTriggeredLoop(Command):
    @staticmethod
    def from_tree(tree: Tree) -> list[CmdEventTriggeredLoop]:
        raise NotImplementedError()


@dataclass
class CmdParameters(Command):
    @staticmethod
    def from_tree(tree: Tree) -> CmdParameters:
        raise NotImplementedError()


COMMAND_NAME_MAP['F'] = CmdFade
COMMAND_NAME_MAP['M'] = CmdMove
COMMAND_NAME_MAP['MX'] = CmdMove
COMMAND_NAME_MAP['MY'] = CmdMove
COMMAND_NAME_MAP['S'] = CmdScale
COMMAND_NAME_MAP['V'] = CmdScale
COMMAND_NAME_MAP['R'] = CmdRotate
COMMAND_NAME_MAP['C'] = CmdColour
COMMAND_NAME_MAP['L'] = CmdLoop
COMMAND_NAME_MAP['T'] = CmdEventTriggeredLoop
COMMAND_NAME_MAP['P'] = CmdParameters
