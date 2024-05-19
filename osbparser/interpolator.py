from __future__ import annotations

from bisect import bisect
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from osbparser.enums import Parameter
from osbparser.osb import (ClassifiedCommands, CmdColour, CmdFade, CmdMove,
                           CmdMoveX, CmdMoveY, CmdParameter, CmdRotate,
                           CmdScale, CmdVectorScale, Object, SimpleCommand)

T = TypeVar('T', bound=SimpleCommand)
U = TypeVar('U')
ObjT = TypeVar('ObjT', bound=Object)


class ObjectInterpolator(Generic[ObjT]):
    obj: ObjT

    def __init__(self, classified: ClassifiedCommands[ObjT]):
        self.fade = self.create_fade_interpolator(classified[CmdFade])
        self.move = self.create_move_interpolator(classified[CmdMove])
        self.movex = self.create_movex_interpolator(classified[CmdMoveX])
        self.movey = self.create_movey_interpolator(classified[CmdMoveY])
        self.scale = self.create_scale_interpolator(classified[CmdScale])
        self.vector_scale = self.create_vector_scale_interpolator(classified[CmdVectorScale])
        self.rotate = self.create_rotate_interpolator(classified[CmdRotate])
        self.colour = self.create_colour_interpolator(classified[CmdColour])

        params = classified[CmdParameter]
        self.h_flag = self.create_param_checker(params, Parameter.H)
        self.v_flag = self.create_param_checker(params, Parameter.V)
        self.a_flag = self.create_param_checker(params, Parameter.A)

    @staticmethod
    def create_fade_interpolator(commands: list[CmdFade]):
        return AnimInterpolator(1., commands, key=lambda c: (c.start_opacity, c.end_opacity))

    @staticmethod
    def create_move_interpolator(commands: list[CmdMove]):
        x_interpolator = AnimInterpolator(None, commands, key=lambda c: (c.startx, c.endx))
        y_interpolator = AnimInterpolator(None, commands, key=lambda c: (c.starty, c.endy))

        def interpolator(t: float) -> tuple[float, float]:
            return (
                x_interpolator(t),
                y_interpolator(t)
            )

        return interpolator

    @staticmethod
    def create_movex_interpolator(commands: list[CmdMoveX]):
        return AnimInterpolator(None, commands, key=lambda c: (c.startx, c.endx))

    @staticmethod
    def create_movey_interpolator(commands: list[CmdMoveY]):
        return AnimInterpolator(None, commands, key=lambda c: (c.starty, c.endy))

    @staticmethod
    def create_scale_interpolator(commands: list[CmdScale]):
        return AnimInterpolator(1., commands, key=lambda c: (c.startscale, c.endscale))

    @staticmethod
    def create_vector_scale_interpolator(commands: list[CmdVectorScale]):
        x_interpolator = AnimInterpolator(1., commands, key=lambda c: (c.startx, c.endx))
        y_interpolator = AnimInterpolator(1., commands, key=lambda c: (c.starty, c.endy))

        def interpolator(t: float) -> tuple[float, float]:
            return (
                x_interpolator(t),
                y_interpolator(t)
            )

        return interpolator

    @staticmethod
    def create_rotate_interpolator(commands: list[CmdRotate]):
        return AnimInterpolator(0., commands, key=lambda c: (c.startangle, c.endangle))

    @staticmethod
    def create_colour_interpolator(commands: list[CmdColour]):
        r_interpolator = AnimInterpolator(1., commands, key=lambda c: (c.r1, c.r2))
        g_interpolator = AnimInterpolator(1., commands, key=lambda c: (c.g1, c.g2))
        b_interpolator = AnimInterpolator(1., commands, key=lambda c: (c.b1, c.b2))

        def interpolator(t: float) -> float:
            return (
                r_interpolator(t),
                g_interpolator(t),
                b_interpolator(t)
            )

        return interpolator

    @staticmethod
    def create_param_checker(commands: list[CmdParameter], param: Parameter):
        commands = [cmd for cmd in commands if cmd.parameter == param]

        def checker(t: float) -> bool:
            if not commands:
                return False

            idx = bisect(commands, t, key=lambda x: x.start)
            if idx == 0:
                return False
            cmd = commands[idx - 1]
            return cmd.is_instant() or t <= cmd.end

        return checker


@dataclass
class AnimInterpolator(Generic[T, U]):
    default: U
    commands: list[T]
    key: Callable[[T], tuple[float, float]]

    def __call__(self, t: float) -> float | U:
        if not self.commands:
            return self.default

        idx = bisect(self.commands, t, key=lambda x: x.start)
        if idx == 0:
            return self.key(self.commands[0])[0]
        cmd = self.commands[idx - 1]
        startv, endv = self.key(cmd)
        if t >= cmd.end:
            return endv
        alpha = cmd.easing.get_function()((t - cmd.start) / (cmd.end - cmd.start))
        return (1 - alpha) * startv + alpha * endv
