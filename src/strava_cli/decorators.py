"""Command decorators for reducing boilerplate."""

from __future__ import annotations

import functools
import inspect
import sys
from collections.abc import Callable
from typing import Any, TypeVar

import typer

from strava_cli.exceptions import StravaCLIError

R = TypeVar("R")


def _get_first_param_name(func: Callable) -> str | None:
    """Get the name of the first parameter of a function."""
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    return params[0] if params else None


def _remove_first_parameter(func: Callable) -> inspect.Signature:
    """Remove the first parameter (client) from a function's signature.

    This is needed because Typer inspects the function signature to determine
    CLI parameters. We want to hide the 'client' parameter that the decorator
    injects.

    Also evaluates string annotations so Typer can see the Annotated types.
    """
    from typing import get_type_hints

    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Remove first param (client)
    if params:
        params = params[1:]

    # Get evaluated type hints with Annotated preserved
    try:
        type_hints = get_type_hints(func, include_extras=True)
    except Exception:
        # If evaluation fails, fall back to string annotations
        type_hints = {}

    # Create new parameters with evaluated annotations
    new_params = []
    for param in params:
        if param.name in type_hints:
            # Use the evaluated type hint
            new_params.append(param.replace(annotation=type_hints[param.name]))
        else:
            new_params.append(param)

    return sig.replace(parameters=new_params)


def with_client(func: Callable[..., R]) -> Callable[..., R]:
    """Inject authenticated StravaClient as first argument.

    Usage:
        @app.command()
        @with_client
        def my_command(client: StravaClient, arg1: str) -> None:
            result = client.get_activities()
            ...

    Handles:
        - Config loading from cli.state.config_path
        - Profile selection from cli.state.profile
        - Authentication validation
        - Token refresh if expired
        - StravaCLIError -> proper exit with message
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        # Import here to avoid circular imports
        from strava_cli import cli
        from strava_cli.client import get_client
        from strava_cli.config import Config

        try:
            config = Config.load(cli.state.config_path)
            client = get_client(config, cli.state.profile)
            return func(client, *args, **kwargs)
        except StravaCLIError as e:
            print(f"error: {e.message}", file=sys.stderr)
            if e.hint and not cli.state.quiet:
                print(f"hint: {e.hint}", file=sys.stderr)
            raise typer.Exit(e.exit_code) from None
        except typer.Exit:
            raise  # Let Typer exits through
        except typer.Abort:
            raise  # Let user cancellation through

    # Update the wrapper's signature to hide the 'client' parameter from Typer
    wrapper.__signature__ = _remove_first_parameter(func)  # type: ignore[attr-defined]

    # Also update __annotations__ as Typer uses get_type_hints() which reads from it
    # We need to copy and filter annotations, preserving the proper evaluation context
    first_param = _get_first_param_name(func)
    if first_param and hasattr(func, "__annotations__"):
        # Filter out the first parameter from annotations
        new_annotations = {k: v for k, v in func.__annotations__.items() if k != first_param}
        wrapper.__annotations__ = new_annotations

        # Typer uses get_type_hints() to resolve annotations. For this to work
        # correctly with string annotations, we need to ensure the wrapper has
        # access to the original function's globals. Since __globals__ is read-only,
        # we work around this by updating the wrapper module's globals directly.
        # This is safe because the wrapper is defined in this module.
        original_globals = func.__globals__
        wrapper_globals = wrapper.__globals__
        for name in ["Annotated", "typer"]:
            if name in original_globals and name not in wrapper_globals:
                wrapper_globals[name] = original_globals[name]

    return wrapper


def emit_output(data: Any) -> None:
    """Emit data using global output settings."""
    # Import here to avoid circular imports
    from strava_cli import cli
    from strava_cli.output import output

    output(
        data,
        format=cli.state.format,
        fields=cli.state.fields,
        no_header=cli.state.no_header,
    )


def emit_result(data: Any, human_msg: str) -> None:
    """Emit mutation result using global output settings.

    For human format: prints human_msg only.
    For machine formats: outputs full structured data.
    """
    # Import here to avoid circular imports
    from strava_cli import cli
    from strava_cli.output import emit_result as _emit_result

    _emit_result(
        data,
        human_msg,
        format=cli.state.format,
        fields=cli.state.fields,
        no_header=cli.state.no_header,
    )


def authenticated_command(func: Callable[..., Any]) -> Callable[..., None]:
    """Decorator for authenticated commands that return data to output.

    Injects authenticated client and auto-outputs the return value.

    Usage:
        @app.command()
        @authenticated_command
        def my_command(client: StravaClient, arg1: str) -> Any:
            return client.get_activities()  # Auto-output
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        # Import here to avoid circular imports
        from strava_cli import cli
        from strava_cli.client import get_client
        from strava_cli.config import Config

        try:
            config = Config.load(cli.state.config_path)
            client = get_client(config, cli.state.profile)
            result = func(client, *args, **kwargs)
            if result is not None:
                emit_output(result)
        except StravaCLIError as e:
            print(f"error: {e.message}", file=sys.stderr)
            if e.hint and not cli.state.quiet:
                print(f"hint: {e.hint}", file=sys.stderr)
            raise typer.Exit(e.exit_code) from None
        except typer.Exit:
            raise  # Let Typer exits through
        except typer.Abort:
            raise  # Let user cancellation through

    # Update the wrapper's signature to hide the 'client' parameter from Typer
    wrapper.__signature__ = _remove_first_parameter(func)  # type: ignore[attr-defined]

    # Also update __annotations__ as Typer uses get_type_hints() which reads from it
    first_param = _get_first_param_name(func)
    if first_param and hasattr(func, "__annotations__"):
        new_annotations = {k: v for k, v in func.__annotations__.items() if k != first_param}
        wrapper.__annotations__ = new_annotations

        original_globals = func.__globals__
        wrapper_globals = wrapper.__globals__
        for name in ["Annotated", "typer"]:
            if name in original_globals and name not in wrapper_globals:
                wrapper_globals[name] = original_globals[name]

    return wrapper
