"""Tool registry: @tool(name, desc) -> async fn. Single source of truth for MCP+CLI+dashboard."""
from __future__ import annotations
REG: dict = {}

def tool(name, desc):
    def deco(fn):
        REG[name] = {"fn": fn, "desc": desc, "domain": fn.__module__.split(".")[-1]}
        return fn
    return deco

def names():
    return sorted(REG)

def describe():
    return [{"name": k, "description": v["desc"], "domain": v["domain"]} for k, v in sorted(REG.items())]
