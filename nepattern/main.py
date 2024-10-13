from __future__ import annotations

from collections.abc import Mapping as ABCMap
from collections.abc import MutableMapping as ABCMuMap
from collections.abc import MutableSequence as ABCMuSeq
from collections.abc import MutableSet as ABCMuSet
from collections.abc import Sequence as ABCSeq
from collections.abc import Set as ABCSet
from contextlib import suppress
from copy import deepcopy
import inspect
from types import FunctionType, LambdaType, MethodType
from typing import Any, ForwardRef, Literal, TypeVar, Union, runtime_checkable
from typing_extensions import Annotated, get_args, get_origin

from tarina.lang import lang

from .base import (
    ANY,
    NONE,
    DirectPattern,
    DirectTypePattern,
    ForwardRefPattern,
    RegexPattern,
    SwitchPattern,
    UnionPattern,
)
from .context import all_patterns
from .core import Pattern
from .util import CGenericAlias, CUnionType, GenericAlias, RawStr, TPattern

_Contents = (Union, CUnionType, Literal)


def _generic_parser(item: GenericAlias, extra: str) -> Pattern:  # type: ignore
    origin = get_origin(item)
    if origin is Annotated:
        org, *meta = get_args(item)
        if not isinstance(_o := parser(org, extra), Pattern):  # type: ignore  # pragma: no cover
            raise TypeError(_o)
        _arg = deepcopy(_o)
        _arg.alias = al[-1] if (al := [i for i in meta if isinstance(i, str)]) else _arg.alias
        validators = [i for i in meta if callable(i)]
        if validators:
            _arg.post_validate(lambda x: all(i(x) for i in validators))
        return _arg
    if origin in _Contents:
        _args = {parser(t, extra) for t in get_args(item)}
        return (_args.pop() if len(_args) == 1 else UnionPattern(*_args)) if _args else ANY
    return Pattern(origin=origin, alias=f"{repr(item).split('.')[-1]}").accept(origin)


def _typevar_parser(item: TypeVar):
    return Pattern(alias=f"{item}"[1:]).accept(item)


def _protocol_parser(item: type):
    if not getattr(item, "_is_runtime_protocol", True):  # pragma: no cover
        item = runtime_checkable(deepcopy(item))  # type: ignore
    return Pattern(alias=f"{item}").accept(item)


def parser(item: Any, extra: str = "allow") -> Pattern:
    """对数类型的检查， 将一般数据类型转为 Pattern 或者特殊类型"""
    if isinstance(item, Pattern):
        return item
    with suppress(TypeError):
        if item and (pat := all_patterns().get(item, None)):
            return pat
    if isinstance(item, (GenericAlias, CGenericAlias, CUnionType)):
        return _generic_parser(item, extra)
    if isinstance(item, TypeVar):
        return _typevar_parser(item)
    if getattr(item, "_is_protocol", False):
        return _protocol_parser(item)
    if isinstance(item, (FunctionType, MethodType, LambdaType)):
        if len((sig := inspect.signature(item)).parameters) not in (1, 2):  # pragma: no cover
            raise TypeError(f"{item} can only accept 1 or 2 argument")
        anno = list(sig.parameters.values())[-1].annotation
        return (
            Pattern((Any if sig.return_annotation == inspect.Signature.empty else sig.return_annotation))  # type: ignore
            .accept(Any if anno == inspect.Signature.empty else anno)
            .convert(item if len(sig.parameters) == 2 else lambda _, x: item(x))
        )
    if isinstance(item, TPattern):  # type: ignore
        return RegexPattern(item.pattern, alias=f"'{item.pattern}'")
    if isinstance(item, str):
        if item.startswith("re:"):
            pat = item[3:]
            return Pattern.regex_match(pat, alias=f"'{pat}'")
        if item.startswith("rep:"):
            pat = item[4:]
            return RegexPattern(pat, alias=f"'{pat}'")
        if "|" in item:
            names = item.split("|")
            return UnionPattern(*(all_patterns().get(i, i) for i in names if i))
        return DirectPattern(item, alias=f"'{item}'")
    if isinstance(item, RawStr):
        return DirectPattern(item.value, alias=f"'{item.value}'")
    if isinstance(item, (list, tuple, set, ABCSeq, ABCMuSeq, ABCSet, ABCMuSet)):  # Args[foo, [123, int]]
        return UnionPattern(*map(lambda x: parser(x) if inspect.isclass(x) else x, item))
    if isinstance(item, (dict, ABCMap, ABCMuMap)):
        return SwitchPattern(dict(item))
    if isinstance(item, ForwardRef):
        return ForwardRefPattern(item)
    if item is None or type(None) == item:
        return NONE
    if extra == "ignore":
        return ANY
    elif extra == "reject":
        raise TypeError(lang.require("nepattern", "parse_reject").format(target=item))
    if inspect.isclass(item):
        return DirectTypePattern(origin=item)  # type: ignore
    return DirectPattern(item)


__all__ = ["parser"]
