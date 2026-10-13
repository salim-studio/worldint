"""Fast Click CLI (Arabic+English): `worldint <tool> [--json] [k=v...]` + helpers."""
from __future__ import annotations
import asyncio, json, sys
import click
from . import tools
from .core.registry import REG

def _run_tool(tool, extra):
    """Run any registered tool: worldint earthquakes min_mag=5 limit=5"""
    args = {}
    for a in extra:
        if a == "--json":
            continue
        if "=" in a:
            k, v = a.split("=", 1)
            try: v = json.loads(v)
            except Exception:
                try: v = float(v) if "." in v else int(v)
                except Exception: pass
            args[k] = v
    if tool not in REG:
        click.echo(f"unknown tool: {tool}"); sys.exit(1)
    res = asyncio.run(REG[tool]["fn"](**args))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2, default=str)[:30000])

class DynGroup(click.Group):
    def get_command(self, ctx, name):
        c = super().get_command(ctx, name)
        if c is not None or name in ("--help", "-h"):
            return c
        if name in REG:
            @click.command(name, context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
            @click.pass_context
            def _dyn(ctx, **kw):
                _run_tool(name, ctx.args)
            return _dyn
        return None

@click.group(cls=DynGroup, invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("worldint — fast global-intelligence toolkit\ntools: " + ", ".join(sorted(REG))[:1500])
        click.echo("\nUsage: worldint <tool> [k=v ...]  |  worldint tools  |  worldint brief")

@main.command("tools")
def _tools():
    for k in sorted(REG):
        click.echo(f"{k:22s} {REG[k]['desc'][:90]}")

@main.command("brief")
def _brief():
    from .sources.synth import daily_digest
    r = asyncio.run(daily_digest())
    click.echo(r.get("markdown", r))

@main.command("report")
@click.option("-o", "--out", default="worldint-brief.html")
@click.option("--sections", default="all")
def _report(out, sections):
    from .reports import build_html
    asyncio.run(build_html(out))
    click.echo(f"saved -> {out}")

@main.command("status")
def _status():
    from .sources.synth import status
    click.echo(json.dumps(asyncio.run(status()), ensure_ascii=False, indent=2))

@main.command("search")
@click.argument("query")
def _search(query):
    from . import store
    click.echo(json.dumps(store.search(query), ensure_ascii=False, indent=2)[:6000])

@main.command("run", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("tool")
@click.pass_context
def _run(ctx, tool):
    """Run any tool: worldint run earthquakes min_mag=5 limit=5"""
    _run_tool(tool, ctx.args)

if __name__ == "__main__":
    main()
