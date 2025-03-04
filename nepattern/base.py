from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
import re
import sys
from types import MethodType
from typing import Any, Callable, Final, ForwardRef, Generic, Match, TypeVar, Union, final, overload, cast

from tarina import DateParser, lang

from .core import Pattern, _RegexPattern
from .exception import MatchFailed
from .util import TPattern

TOrigin = TypeVar("TOrigin")
TDefault = TypeVar("TDefault")
_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_T5 = TypeVar("_T5")
_T6 = TypeVar("_T6")
_T7 = TypeVar("_T7")
_T8 = TypeVar("_T8")
_T9 = TypeVar("_T9")

_TP = TypeVar("_TP", bound=Pattern)


def _SpecialPattern(cls: type[_TP]) -> type[_TP]:
    old_init = cls.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)

        @self.pre_validate
        def _(x):  # pragma: no cover
            try:
                self.match(x)
                return True
            except MatchFailed:
                return False

        @self.convert
        def _(s, x):  # pragma: no cover
            return s.match(x)

    cls.__init__ = __init__
    return cls


@_SpecialPattern
class DirectPattern(Pattern[TOrigin]):
    """直接判断"""

    def __init__(self, target: TOrigin, alias: str | None = None):
        self.target = target
        super().__init__(type(target), alias)

    def match(self, input_: Any):
        if input_ != self.target:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected=self.target)
            )
        return input_

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, DirectPattern) and self.target == other.target

    def copy(self):  # pragma: no cover
        return DirectPattern(self.target, self.alias)


@_SpecialPattern
class DirectTypePattern(Pattern[TOrigin]):
    """直接类型判断"""

    def __init__(self, origin: type[TOrigin], alias: str | None = None):
        self.origin = origin
        super().__init__(origin, alias)

    def match(self, input_: Any):
        if not isinstance(input_, self.origin):
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected=self.origin
                )
            )
        return input_

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, DirectTypePattern) and self.origin is other.origin

    def copy(self):  # pragma: no cover
        return DirectTypePattern(self.origin, self.alias)


@_SpecialPattern
class RegexPattern(_RegexPattern[Match[str]]):
    """针对正则的特化匹配，支持正则组"""

    def __init__(self, pattern: str | TPattern, alias: str | None = None):
        super().__init__(pattern, Match[str], alias=alias or "regex[:group]")

    def match(self, input_: Any) -> Match[str]:
        if not isinstance(input_, str):
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected="str"
                )
            )
        if mat := (re.match(self.pattern, input_) or re.search(self.pattern, input_)):
            return mat
        raise MatchFailed(
            lang.require("nepattern", "error.content").format(target=input_, expected=self.pattern)
        )

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, RegexPattern) and self.pattern == other.pattern

    def copy(self):  # pragma: no cover
        return RegexPattern(self.pattern, self.alias)


@_SpecialPattern
class UnionPattern(Pattern[_T]):
    """多类型参数的匹配"""

    # optional: bool
    # for_validate: list[BasePattern]
    # for_equal: list[str | object]

    __slots__ = ("base", "optional", "for_validate", "for_equal")

    def __init__(self, *base: Any):
        self.base = list(base)
        self.optional = False
        self.for_validate = []
        self.for_equal = []

        for arg in self.base:
            if arg == NONE:
                self.optional = True
                self.for_equal.append(None)
            elif isinstance(arg, Pattern):
                if isinstance(arg, DirectPattern):
                    self.for_equal.append(arg.target)
                else:
                    self.for_validate.append(arg)
            else:
                self.for_equal.append(arg)
        alias_content = "|".join([str(a) for a in self.for_validate] + [repr(a) for a in self.for_equal])  # pragma: no cover
        types = [i.origin for i in self.for_validate] + [type(i) for i in self.for_equal]  # pragma: no cover
        super().__init__(Union.__getitem__(tuple(types)), alias=alias_content)  # type: ignore

    def match(self, input_: Any):
        if not input_:
            input_ = None
        if input_ not in self.for_equal:
            for pat in self.for_validate:
                if (res := pat.execute(input_)).success:
                    return res.value()
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected=self.alias)
            )
        return input_

    @classmethod
    def of(cls, *types: type[_T1]) -> UnionPattern[_T1]:
        from .main import parser

        return cls(*[parser(i) for i in types])  # type: ignore  # pragma: no cover

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], /) -> UnionPattern[_T1 | _T2]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], /) -> UnionPattern[_T1 | _T2 | _T3]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], pat5: Pattern[_T5], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4 | _T5]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], pat5: Pattern[_T5], pat6: Pattern[_T6], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4 | _T5 | _T6]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], pat5: Pattern[_T5], pat6: Pattern[_T6], pat7: Pattern[_T7], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4 | _T5 | _T6 | _T7]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], pat5: Pattern[_T5], pat6: Pattern[_T6], pat7: Pattern[_T7], pat8: Pattern[_T8], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4 | _T5 | _T6 | _T7 | _T8]: ...

    @classmethod
    @overload
    def with_(cls, pat1: Pattern[_T1], pat2: Pattern[_T2], pat3: Pattern[_T3], pat4: Pattern[_T4], pat5: Pattern[_T5], pat6: Pattern[_T6], pat7: Pattern[_T7], pat8: Pattern[_T8], pat9: Pattern[_T9], /) -> UnionPattern[_T1 | _T2 | _T3 | _T4 | _T5 | _T6 | _T7 | _T8 | _T9]: ...

    @classmethod
    @overload
    def with_(cls, *patterns: Pattern[_T]) -> UnionPattern[_T]: ...

    @classmethod
    def with_(cls, *patterns: Pattern) -> UnionPattern:
        return cls(*patterns)

    def __repr__(self):
        return "|".join(repr(a) for a in (*self.for_validate, *self.for_equal))

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, UnionPattern) and self.base == other.base


_TCase = TypeVar("_TCase")
_TSwtich = TypeVar("_TSwtich")


@_SpecialPattern
class SwitchPattern(Pattern[_TCase], Generic[_TCase, _TSwtich]):
    """匹配多种情况的表达式"""

    switch: dict[_TSwtich | ellipsis, _TCase]

    __slots__ = ("switch",)

    def __init__(self, data: dict[_TSwtich, _TCase] | dict[_TSwtich | ellipsis, _TCase]):
        self.switch = data  # type: ignore
        super().__init__(type(list(data.values())[0]))

    def __repr__(self):
        return "|".join(f"{k}" for k in self.switch if k != Ellipsis)

    def match(self, input_: Any) -> _TCase:
        try:
            return self.switch[input_]
        except KeyError as e:
            if Ellipsis in self.switch:
                return self.switch[...]
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected=self.__repr__())
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, SwitchPattern) and self.switch == other.switch


@_SpecialPattern
class ForwardRefPattern(Pattern[Any]):
    def __init__(self, ref: ForwardRef):
        self.ref = ref
        super().__init__(alias=ref.__forward_arg__)

    def match(self, input_: Any):
        if isinstance(input_, str) and input_ == self.ref.__forward_arg__:
            return input_
        _main = sys.modules["__main__"]
        if sys.version_info < (3, 9):  # pragma: no cover
            origin = self.ref._evaluate(_main.__dict__, _main.__dict__)  # type: ignore
        else:  # pragma: no cover
            origin = self.ref._evaluate(_main.__dict__, _main.__dict__, recursive_guard=frozenset())  # type: ignore
        if not isinstance(input_, origin):  # type: ignore
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected=self.ref.__forward_arg__
                )
            )
        return input_

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, ForwardRefPattern) and self.ref == other.ref


@_SpecialPattern
class AntiPattern(Pattern[TOrigin]):
    def __init__(self, pattern: Pattern[TOrigin]):
        self.base: Pattern[TOrigin] = pattern
        super().__init__(origin=pattern.origin, alias=f"!{pattern}")

    def match(self, input_: Any):
        try:
            self.base.match(input_)
        except MatchFailed:
            return input_
        raise MatchFailed(
            lang.require("nepattern", "error.content").format(target=input_, expected=self.alias)
        )

    def __eq__(self, other):  # pragma: no cover
        return isinstance(other, AntiPattern) and self.base == other.base


NONE: Final[Pattern[None]] = Pattern(type(None), alias="none").convert(lambda _, __: None)  # pragma: no cover
ANY: Final[Pattern[Any]] = Pattern(alias="any")
"""匹配任意内容的表达式"""


@final
@_SpecialPattern
class AnyStrPattern(Pattern[str]):
    def __init__(self):
        super().__init__(origin=str, alias="any_str")

    def match(self, input_: Any) -> str:
        return str(input_)

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is AnyStrPattern


AnyString: Final = AnyStrPattern()
"""匹配任意内容并转为字符串的表达式"""


@final
@_SpecialPattern
class StrPattern(Pattern[str]):
    def __init__(self):
        super().__init__(origin=str, alias="str")

    def match(self, input_: Any) -> str:
        if isinstance(input_, str):
            return input_.value if isinstance(input_, Enum) else input_
        elif isinstance(input_, (bytes, bytearray)):
            return input_.decode()
        raise MatchFailed(
            lang.require("nepattern", "error.type").format(
                type=input_.__class__, target=input_, expected="str | bytes | bytearray"
            )
        )

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is StrPattern


STRING: Final = StrPattern()


@final
@_SpecialPattern
class BytesPattern(Pattern[bytes]):
    def __init__(self):
        super().__init__(origin=bytes, alias="bytes")

    def match(self, input_: Any) -> bytes:
        if isinstance(input_, bytes):
            return input_
        elif isinstance(input_, bytearray):  # pragma: no cover
            return bytes(input_)
        elif isinstance(input_, str):
            return input_.encode()
        raise MatchFailed(
            lang.require("nepattern", "error.type").format(
                type=input_.__class__, target=input_, expected="bytes | str"
            )
        )

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is BytesPattern


BYTES: Final = BytesPattern()


@final
@_SpecialPattern
class IntPattern(Pattern[int]):
    def __init__(self):
        super().__init__(origin=int, alias="int")

    def match(self, input_: Any) -> int:
        if isinstance(input_, int) and input_ is not True and input_ is not False:
            return input_
        if isinstance(input_, (str, bytes, bytearray)) and len(input_) > 4300:  # pragma: no cover
            raise ValueError("int too large to convert")
        try:
            return int(input_)
        except (ValueError, TypeError, OverflowError) as e:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="int")
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is IntPattern


INTEGER: Final = IntPattern()
"""整形数表达式，只能接受整数样式的量"""


@final
@_SpecialPattern
class FloatPattern(Pattern[float]):
    def __init__(self):
        super().__init__(origin=float, alias="float")

    def match(self, input_: Any) -> float:
        if isinstance(input_, float):
            return input_
        try:
            return float(input_)
        except (TypeError, ValueError) as e:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="float")
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is FloatPattern


FLOAT: Final = FloatPattern()
"""浮点数表达式"""


@final
@_SpecialPattern
class NumberPattern(Pattern[Union[int, float]]):
    def __init__(self):
        super().__init__(origin=Union[int, float], alias="number")  # type: ignore

    def match(self, input_: Any) -> int | float:
        if isinstance(input_, (float, int)):
            return input_
        try:
            res = float(input_)
            return int(res) if res.is_integer() else res
        except (ValueError, TypeError) as e:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="int | float")
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is NumberPattern


NUMBER: Final = NumberPattern()
"""一般数表达式，既可以浮点数也可以整数 """


@final
@_SpecialPattern
class BoolPattern(Pattern[bool]):
    def __init__(self):
        super().__init__(origin=bool, alias="bool")

    def match(self, input_: Any) -> bool:
        if input_ is True or input_ is False:
            return input_
        if isinstance(input_, bytes):  # pragma: no cover
            input_ = input_.decode()
        if isinstance(input_, str):  # pragma: no cover
            input_ = input_.lower()
        if input_ == "true":
            return True
        if input_ == "false":
            return False
        raise MatchFailed(lang.require("nepattern", "error.content").format(target=input_, expected="bool"))

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is BoolPattern


BOOLEAN: Final = BoolPattern()
"""布尔表达式，只能接受true或false样式的量"""


@final
@_SpecialPattern
class WideBoolPattern(Pattern[bool]):
    def __init__(self):
        super().__init__(origin=bool, alias="bool")

    BOOL_FALSE = {0, "0", "off", "f", "false", "n", "no"}
    BOOL_TRUE = {1, "1", "on", "t", "true", "y", "yes"}

    def match(self, input_: Any) -> bool:
        if input_ is True or input_ is False:
            return input_
        if isinstance(input_, bytes):  # pragma: no cover
            input_ = input_.decode()
        if isinstance(input_, str):
            input_ = input_.lower()
        try:
            if input_ in self.BOOL_TRUE:
                return True
            if input_ in self.BOOL_FALSE:
                return False
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="bool")
            )
        except (ValueError, TypeError) as e:
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected="bool"
                )
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is BoolPattern


WIDE_BOOLEAN = WideBoolPattern()
"""宽松布尔表达式，可以接受更多的布尔样式的量"""

LIST: Final[Pattern[list]] = Pattern.regex_convert(r"(\[.+?\])", list, lambda m: eval(m[1]), alias="list", allow_origin=True)
TUPLE: Final[Pattern[tuple]] = Pattern.regex_convert(r"(\(.+?\))", tuple, lambda m: eval(m[1]), alias="tuple", allow_origin=True)
SET: Final[Pattern[set]] = Pattern.regex_convert(r"(\{.+?\})", set, lambda m: eval(m[1]), alias="set", allow_origin=True)
DICT: Final[Pattern[dict]] = Pattern.regex_convert(r"(\{.+?\})", dict, lambda m: eval(m[1]), alias="dict", allow_origin=True)

EMAIL: Final = Pattern.regex_match(r"(?:[\w\.+-]+)@(?:[\w\.-]+)\.(?:[\w\.-]+)", alias="email")
"""匹配邮箱地址的表达式"""

IP: Final = Pattern.regex_match(
    r"(?:(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])\.){3}(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5]):?(?:\d+)?",
    alias="ip",
)
"""匹配Ip地址的表达式"""

URL: Final = Pattern.regex_match(
    r"(?:\w+://)?[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(?:\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(?::[0-9]{1,5})?[-a-zA-Z0-9()@:%_\\\+\.~#?&//=]*",
    alias="url",
)
"""匹配网页链接的表达式"""


@final
@_SpecialPattern
class HexPattern(Pattern[int]):
    def __init__(self):
        super().__init__(origin=int, alias="hex")

    def match(self, input_: Any) -> int:
        if not isinstance(input_, str):
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected="str"
                )
            )
        try:
            return int(input_, 16)
        except ValueError as e:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="hex")
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is HexPattern


HEX: Final = HexPattern()
"""匹配16进制数的表达式"""

HEX_COLOR = Pattern.regex_convert(r"(#[0-9a-fA-F]{6})", str, lambda m: m[1][1:], "color")
"""匹配16进制颜色代码的表达式"""


@final
@_SpecialPattern
class DateTimePattern(Pattern[datetime]):
    def __init__(self):
        super().__init__(origin=datetime, alias="datetime")

    def match(self, input_: Any) -> datetime:
        if isinstance(input_, (int, float)):
            return datetime.fromtimestamp(input_)
        if not isinstance(input_, str):
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(
                    type=input_.__class__, target=input_, expected="str | int | float"
                )
            )
        return DateParser.parse(input_)

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is DateTimePattern


DATETIME: Final = DateTimePattern()
"""匹配时间的表达式"""


@final
@_SpecialPattern
class PathPattern(Pattern[Path]):
    def __init__(self):
        super().__init__(origin=Path, alias="path")

    def match(self, input_: Any) -> Path:
        if isinstance(input_, Path):
            return input_

        try:
            return Path(input_)
        except (ValueError, TypeError) as e:
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected="PathLike")
            ) from e

    def __eq__(self, other):  # pragma: no cover
        return other.__class__ is PathPattern


PATH: Final = PathPattern()

PathFile: Final = (
    Pattern(bytes)
    .accept(Union[str, Path, bytes])
    .pre_validate(lambda x: isinstance(x, bytes) or (isinstance(x, (str, Path)) and Path(x).is_file()))
    .convert(lambda _, x: x if isinstance(x, bytes) else Path(x).read_bytes())
)


def combine(
    current: Pattern[_T],
    previous: Pattern[Any] | None = None,
    alias: str | None = None,
    validator: Callable[[_T], bool] | None = None,
) -> Pattern[_T]:
    _new = current.copy()
    if previous:
        _match = cast(MethodType, _new.match).__func__

        def match(self, input_):
            return _match(self, previous.match(input_))

        _new.match = match.__get__(_new)
    if alias:
        _new.alias = alias
    if validator:
        _match = cast(MethodType, _new.match).__func__

        def match(self, input_):
            res = _match(self, input_)
            if not validator(res):
                raise MatchFailed(
                    lang.require("nepattern", "error.content").format(target=input_, expected=alias)
                )
            return res

        _new.match = match.__get__(_new)
    return _new


DelimiterInt = combine(
    INTEGER,
    Pattern(str).accept(str).convert(lambda _, x: x.replace(",", "_")),
    "DelimInt",
)
