import math
from enum import Enum
from typing import Callable, TypeVar

from osbparser.exception import InvalidEnum

EnumT = TypeVar('EnumT', bound=Enum)

__all__ = [
    'Layer',
    'Origin',
    'Trigger',
    'Parameter',
    'Easing'
]


def find_enum_by_name(enum_cls: type[EnumT], name: str, lineno: int) -> EnumT:
    try:
        return enum_cls[name]
    except KeyError:
        raise InvalidEnum(f'Invalid enum "{name}" for "{enum_cls.__name__}" '
                          f'at line {lineno}, '
                          f'use one of {list(enum_cls.__members__.keys())} instead.')


def find_enum_by_value(enum_cls: type[EnumT], value: str, lineno: int) -> EnumT:
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


class Trigger(Enum):
    HitSoundClap = 0
    HitSoundFinish = 1
    HitSoundWhistle = 2
    Passing = 3
    Failing = 4


class Parameter(Enum):
    H = 0
    V = 1
    A = 2


ELASTIC_CONST = 2 * math.pi / .3
ELASTIC_CONST2 = .3 / 4

BACK_CONST = 1.70158
BACK_CONST2 = BACK_CONST * 1.525

BOUNCE_CONST = 1 / 2.75

# constants used to fix expo and elastic curves to start/end at 0/1
EXPO_OFFSET = 2**(-10)
ELASTIC_OFFSET_FULL = 2**(-11)
ELASTIC_OFFSET_HALF = 2**(-10) * math.sin((.5 - ELASTIC_CONST2) * ELASTIC_CONST)
ELASTIC_OFFSET_QUARTER = 2**(-10) * math.sin((.25 - ELASTIC_CONST2) * ELASTIC_CONST)
IN_OUT_ELASTIC_OFFSET = 2**(-10) * math.sin((1 - ELASTIC_CONST2 * 1.5) * ELASTIC_CONST / 1.5)


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
    # OutPow10?

    def get_function(self) -> Callable[[float], float]:
        # https://github.com/ppy/osu-framework/blob/master/osu.Framework/Graphics/Transforms/DefaultEasingFunction.cs
        match self:
            case Easing.Linear:
                return lambda t: t

            case Easing.EasingIn | Easing.QuadIn:
                return lambda t: t**2
            case Easing.EasingOut | Easing.QuadOut:
                return lambda t: t * (2 - t)
            case Easing.QuadInOut:
                return lambda t: (
                    t**2 * 2
                    if t < .5
                    else (t - 1)**2 * -2 + 1
                )

            case Easing.CubicIn:
                return lambda t: t**3
            case Easing.CubicOut:
                return lambda t: (t - 1)**3 + 1
            case Easing.CubicInOut:
                return lambda t: (
                    t**3 * 4
                    if t < .5
                    else (t - 1)**3 * 4 + 1
                )

            case Easing.QuartIn:
                return lambda t: t**4
            case Easing.QuartOut:
                return lambda t: 1 - (t - 1)**4
            case Easing.QuartInOut:
                return lambda t: (
                    t**4 * 8
                    if t < .5
                    else (t - 1)**4 * -8 + 1
                )

            case Easing.QuintIn:
                return lambda t: t**5
            case Easing.QuintOut:
                return lambda t: (t - 1)**5 + 1
            case Easing.QuintInOut:
                return lambda t: (
                    t**5 * 16
                    if t < .5
                    else (t - 1)**5 * 16 + 1
                )

            case Easing.SineIn:
                return lambda t: 1 - math.cos(t * math.pi * .5)
            case Easing.SineOut:
                return lambda t: math.sin(t * math.pi * .5)
            case Easing.SineInOut:
                return lambda t: .5 - .5 * math.cos(math.pi * t)

            case Easing.ExpoIn:
                return lambda t: 2**(10 * (t - 1)) + EXPO_OFFSET * (t - 1)
            case Easing.ExpoOut:
                return lambda t: -(2**(-10 * t)) + 1 + EXPO_OFFSET * t
            case Easing.ExpoInOut:
                return lambda t: (
                    .5 * 2**(20 * t - 10) + EXPO_OFFSET * (2 * t - 1)
                    if t < .5
                    else 1 - .5 * 2**(-20 * t + 10) + EXPO_OFFSET * (-2 * t + 1)
                )

            case Easing.CircIn:
                return lambda t: 1 - math.sqrt(1 - t**2)
            case Easing.CircOut:
                return lambda t: math.sqrt(1 - (t - 1)**2)
            case Easing.CircInOut:
                def circ_inout(t: float) -> float:
                    t *= 2
                    return (
                        .5 - .5 * math.sqrt(1 - t**2)
                        if t < 1
                        else .5 * math.sqrt(1 - (t - 2)**2) + .5
                    )
                return circ_inout

            case Easing.ElasticIn:
                return lambda t: -(2**(-10 + 10 * t)) * math.sin((1 - ELASTIC_CONST2 - t) * ELASTIC_CONST) \
                    + ELASTIC_OFFSET_FULL * (1 - t)
            case Easing.ElasticOut:
                return lambda t: 2**(-10 * t) * math.sin((t - ELASTIC_CONST2) * ELASTIC_CONST) \
                    + 1 - ELASTIC_OFFSET_FULL * t
            case Easing.ElasticHalfOut:
                return lambda t: 2**(-10 * t) * math.sin((.5 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
                    + 1 - ELASTIC_OFFSET_HALF * t
            case Easing.ElasticQuarterOut:
                return lambda t: 2**(-10 * t) * math.sin((.25 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
                    + 1 - ELASTIC_OFFSET_QUARTER * t
            case Easing.ElasticInOut:
                def elastic_inout(t: float) -> float:
                    t *= 2
                    if t < 1:
                        return -.5 * (
                            2**(-10 + 10 * t) * math.sin((1 - ELASTIC_CONST2 * 1.5 - t) * ELASTIC_CONST / 1.5)
                            - IN_OUT_ELASTIC_OFFSET * (1 - t)
                        )
                    t -= 1
                    return .5 * (
                        2**(-10 * t) * math.sin((t - ELASTIC_CONST2 * 1.5) * ELASTIC_CONST / 1.5)
                        - IN_OUT_ELASTIC_OFFSET * t
                    ) + 1
                return elastic_inout

            case Easing.BackIn:
                return lambda t: t**2 * ((BACK_CONST + 1) * t - BACK_CONST)
            case Easing.BackOut:
                return lambda t: (t - 1)**2 * ((BACK_CONST + 1) * (t - 1) + BACK_CONST) + 1
            case Easing.BackInOut:
                def back_inout(t: float) -> float:
                    t *= 2
                    if t < 1:
                        return .5 * t**2 * ((BACK_CONST2 + 1) * t - BACK_CONST2)
                    t -= 2
                    return .5 * (t**2 * ((BACK_CONST2 + 1) * t + BACK_CONST2) + 2)
                return back_inout

            case Easing.BounceIn:
                def bounce_in(t: float) -> float:
                    t = 1 - t
                    if t < BOUNCE_CONST:
                        return 1 - 7.5625 * t**2
                    if t < 2 * BOUNCE_CONST:
                        t -= 1.5 * BOUNCE_CONST
                        return 1 - (7.5625 * t**2 + .75)
                    if t < 2.5 * BOUNCE_CONST:
                        t -= 2.25 * BOUNCE_CONST
                        return 1 - (7.5625 * t**2 + .9375)
                    t -= 2.625 * BOUNCE_CONST
                    return 1 - (7.5625 * t**2 + .984375)
                return bounce_in

            case Easing.BounceOut:
                def bounce_out(t: float) -> float:
                    if t < BOUNCE_CONST:
                        return 7.5625 * t**2
                    if t < 2 * BOUNCE_CONST:
                        t -= 1.5 * BOUNCE_CONST
                        return 7.5625 * t**2 + .75
                    if t < 2.5 * BOUNCE_CONST:
                        t -= 2.25 * BOUNCE_CONST
                        return 7.5625 * t**2 + .9375
                    t -= 2.625 * BOUNCE_CONST
                    return 7.5625 * t**2 + .984375
                return bounce_out

            case Easing.BounceInOut:
                bounce_out = Easing.BounceOut.get_function()
                return lambda t: (
                    .5 - .5 * bounce_out(1 - t * 2)
                    if t < .5
                    else bounce_out((t - .5) * 2) * .5 + .5
                )
