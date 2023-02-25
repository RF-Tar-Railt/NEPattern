from __future__ import annotations

from collections import UserDict
from contextvars import ContextVar, Token
from typing import Any, Iterable, final

from .base import UnionPattern
from .core import BasePattern
from .util import AllParam, Empty


@final
class Patterns(UserDict):
    def __init__(self, name: str):
        self.name = name
        super().__init__({"": Empty, "*": AllParam})

    def set(
        self,
        target: BasePattern,
        alias: str | None = None,
        cover: bool = True,
    ):
        """
        增加可使用的类型转换器

        Args:
            target: 设置的表达式
            alias: 目标类型的别名
            cover: 是否覆盖已有的转换器
        """
        for k in {alias, target.alias, target.origin}:
            if not k:
                continue
            if k not in self.data or cover:
                self.data[k] = target
            else:
                al_pat = self.data[k]
                self.data[k] = (
                    UnionPattern([*al_pat.base, target])
                    if isinstance(al_pat, UnionPattern)
                    else (UnionPattern([al_pat, target]))
                )

    def sets(self, patterns: Iterable[BasePattern], cover: bool = True):
        for pat in patterns:
            self.set(pat, cover=cover)

    def merge(self, patterns: dict[str, BasePattern]):
        for k in patterns:
            self.set(patterns[k], alias=k)

    def remove(self, origin_type: type, alias: str | None = None):
        if alias and (al_pat := self.data.get(alias)):
            if isinstance(al_pat, UnionPattern):
                self.data[alias] = UnionPattern(filter(lambda x: x.alias != alias, al_pat.base))  # type: ignore
                if not self.data[alias].base:  # type: ignore # pragma: no cover
                    del self.data[alias]
            else:
                del self.data[alias]
        elif al_pat := self.data.get(origin_type):
            if isinstance(al_pat, UnionPattern):
                self.data[origin_type] = UnionPattern(
                    filter(lambda x: x.origin != origin_type, al_pat.for_validate)
                )
                if not self.data[origin_type].base:  # type: ignore # pragma: no cover
                    del self.data[origin_type]
            else:
                del self.data[origin_type]


_ctx: dict[str, Patterns] = {"$global": Patterns("$global")}
_ctx_token: Token

pattern_ctx: ContextVar[Patterns] = ContextVar("nepatterns")
_ctx_token = pattern_ctx.set(_ctx["$global"])


def create_local_patterns(
    name: str,
    data: dict[Any, BasePattern | type[Empty]] | None = None,
    set_current: bool = True,
) -> Patterns:
    """
    新建一个本地表达式组

    Args:
        name: 组名
        data: 可选的初始内容
        set_current: 是否设置为 current
    """
    global _ctx_token
    if name.startswith("$"):
        raise ValueError(name)
    new = Patterns(name)
    new.update(data or {})
    _ctx[name] = new
    if set_current:
        pattern_ctx.reset(_ctx_token)
        _ctx_token = pattern_ctx.set(new)
    return new


def switch_local_patterns(name: str):
    global _ctx_token
    if name.startswith("$"):
        raise ValueError(name)
    target = _ctx[name]
    pattern_ctx.reset(_ctx_token)
    _ctx_token = pattern_ctx.set(target)


def reset_local_patterns():
    global _ctx_token

    target = _ctx["$global"]
    pattern_ctx.reset(_ctx_token)
    _ctx_token = pattern_ctx.set(target)


def local_patterns():
    local = pattern_ctx.get()
    return local if local.name != "$global" else Patterns("$temp")


def global_patterns():
    return _ctx["$global"]


def all_patterns():
    """获取 global 与 local 的合并表达式组"""
    new = Patterns("$temp")
    local = local_patterns()
    if not local.name.startswith("$"):
        new.update(local_patterns().data)
    new.update(global_patterns().data)
    return new


__all__ = [
    "Patterns",
    "local_patterns",
    "global_patterns",
    "all_patterns",
    "switch_local_patterns",
    "create_local_patterns",
    "reset_local_patterns",
]
