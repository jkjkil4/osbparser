from enum import Enum
from typing import TypeVar

from osbparser.exception import InvalidEnum

EnumT = TypeVar('EnumT', bound=Enum)


def find_enum_key(enum_cls: type[EnumT], key: str, lineno: int) -> EnumT:
    try:
        return enum_cls[key]
    except KeyError:
        raise InvalidEnum(f'Invalid enum "{key}" for "{enum_cls.__name__}" '
                          f'at line {lineno}, '
                          f'use one of {list(enum_cls.__members__.keys())} instead.')


def find_enum_value(enum_cls: type[EnumT], value: str, lineno: int) -> EnumT:
    try:
        return enum_cls(value)
    except ValueError:
        values = [value.value for value in enum_cls.__members__.values()]
        raise InvalidEnum(f'Invalid value "{value}" for "{enum_cls.__name__}" '
                          f'at line {lineno}, '
                          f'use one of {values} instead.')


class Layer(Enum):
    Background = 0
    Fail = 1
    Pass = 2
    Foreground = 3


class Origin(Enum):
    TopLeft = 0
    TopCentre = 1
    TopRight = 2
    CentreLeft = 3
    Centre = 4
    CentreRight = 5
    BottomLeft = 6
    BottomCentre = 7
    BottomRight = 8


class Easing(Enum):
    Linear = 0
    EasingOut = 1
    EasingIn = 2
    QuadIn = 3
    QuadOut = 4
    QuadInOut = 5
    CubicIn = 6
    CubicOut = 7
    CubicInOut = 8
    QuartIn = 9
    QuartOut = 10
    QuartInOut = 11
    QuintIn = 12
    QuintOut = 13
    QuintInOut = 14
    SineIn = 15
    SineOut = 16
    SineInOut = 17
    ExpoIn = 18
    ExpoOut = 19
    ExpoInOut = 20
    CircIn = 21
    CircOut = 22
    CircInOut = 23
    ElasticIn = 24
    ElasticOut = 25
    ElasticHalfOut = 26
    ElasticQuarterOut = 27
    ElasticInOut = 28
    BackIn = 29
    BackOut = 30
    BackInOut = 31
    BounceIn = 32
    BounceOut = 33
    BounceInOut = 34
