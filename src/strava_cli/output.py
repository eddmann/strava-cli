"""Output formatters for different formats."""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    jsonl = "jsonl"
    csv = "csv"
    tsv = "tsv"
    human = "human"


def serialize_value(value: Any) -> Any:
    """Serialize a value to JSON-compatible format."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if hasattr(value, "__dict__"):
        # Handle stravalib model objects
        return serialize_object(value)
    return value


def serialize_object(obj: Any) -> dict[str, Any]:
    """Serialize an object to a dictionary."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: serialize_value(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        # Pydantic v2
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        # Pydantic v1 fallback
        return obj.dict()
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                result[key] = serialize_value(value)
        return result
    return {"value": str(obj)}


def filter_fields(data: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """Filter dictionary to only include specified fields."""
    if fields is None:
        return data
    return {k: v for k, v in data.items() if k in fields}


def output_json(data: Any, fields: list[str] | None = None) -> None:
    """Output data as JSON."""
    if isinstance(data, (list, tuple)):
        serialized = [serialize_object(item) for item in data]
        if fields:
            serialized = [filter_fields(item, fields) for item in serialized]
    else:
        serialized = serialize_object(data)
        if fields:
            serialized = filter_fields(serialized, fields)

    print(json.dumps(serialized, indent=2, default=str))


def output_jsonl(data: Any, fields: list[str] | None = None) -> None:
    """Output data as JSON Lines (one JSON object per line)."""
    if not isinstance(data, (list, tuple)):
        data = [data]

    for item in data:
        serialized = serialize_object(item)
        if fields:
            serialized = filter_fields(serialized, fields)
        print(json.dumps(serialized, default=str))


def output_csv(
    data: Any,
    fields: list[str] | None = None,
    no_header: bool = False,
    delimiter: str = ",",
) -> None:
    """Output data as CSV or TSV."""
    if not isinstance(data, (list, tuple)):
        data = [data]

    if not data:
        return

    # Serialize all items
    serialized = [serialize_object(item) for item in data]

    # Determine columns
    if fields:
        columns = fields
    else:
        # Get all unique keys from all items
        all_keys: set[str] = set()
        for item in serialized:
            all_keys.update(item.keys())
        columns = sorted(all_keys)

    # Write CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        delimiter=delimiter,
        extrasaction="ignore",
    )

    if not no_header:
        writer.writeheader()

    for item in serialized:
        # Flatten nested objects to strings
        flat_item = {}
        for col in columns:
            val = item.get(col)
            if isinstance(val, (dict, list)):
                flat_item[col] = json.dumps(val, default=str)
            else:
                flat_item[col] = val
        writer.writerow(flat_item)

    print(output.getvalue(), end="")


def output_tsv(
    data: Any,
    fields: list[str] | None = None,
    no_header: bool = False,
) -> None:
    """Output data as TSV."""
    output_csv(data, fields, no_header, delimiter="\t")


def format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_distance(meters: float | None) -> str:
    """Format distance in meters to human-readable string."""
    if meters is None:
        return "-"
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{meters:.0f} m"


def format_date(dt: datetime | str | None) -> str:
    """Format datetime to human-readable string."""
    if dt is None:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    return dt.strftime("%b %d, %Y")


def output_human(
    data: Any,
    fields: list[str] | None = None,
    columns: list[tuple[str, str, int]] | None = None,
) -> None:
    """Output data as human-readable table.

    Args:
        data: Data to output
        fields: Fields to include
        columns: List of (field_name, header, width) tuples for table formatting
    """
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        if not isinstance(data, (list, tuple)):
            data = [data]

        if not data:
            return

        # Serialize all items
        serialized = [serialize_object(item) for item in data]

        # Create table
        table = Table(show_header=True, header_style="bold")

        # Determine columns
        if columns:
            for _, header, _ in columns:
                table.add_column(header)
            col_fields = [c[0] for c in columns]
        elif fields:
            col_fields = fields
            for f in fields:
                table.add_column(f.upper())
        else:
            all_keys: set[str] = set()
            for item in serialized:
                all_keys.update(item.keys())
            col_fields = sorted(all_keys)
            for f in col_fields:
                table.add_column(f.upper())

        # Add rows
        for item in serialized:
            row = []
            for f in col_fields:
                val = item.get(f)
                if isinstance(val, (dict, list)):
                    row.append(json.dumps(val, default=str))
                elif val is None:
                    row.append("-")
                else:
                    row.append(str(val))
            table.add_row(*row)

        console.print(table)

    except ImportError:
        # Fallback to simple output without Rich
        output_tsv(data, fields)


def output(
    data: Any,
    format: OutputFormat = OutputFormat.json,
    fields: list[str] | None = None,
    no_header: bool = False,
    human_columns: list[tuple[str, str, int]] | None = None,
) -> None:
    """Output data in the specified format.

    Args:
        data: Data to output
        format: Output format
        fields: Fields to include
        no_header: Whether to omit header in CSV/TSV
        human_columns: Column definitions for human output
    """
    if format == OutputFormat.json:
        output_json(data, fields)
    elif format == OutputFormat.jsonl:
        output_jsonl(data, fields)
    elif format == OutputFormat.csv:
        output_csv(data, fields, no_header)
    elif format == OutputFormat.tsv:
        output_tsv(data, fields, no_header)
    elif format == OutputFormat.human:
        output_human(data, fields, human_columns)


def emit_result(
    data: Any,
    human_msg: str,
    format: OutputFormat = OutputFormat.json,
    fields: list[str] | None = None,
    no_header: bool = False,
) -> None:
    """Output mutation result with format-aware messaging.

    For human format: prints human_msg to stdout.
    For machine formats (json, jsonl, csv, tsv): outputs structured data.

    Args:
        data: Structured data to output for machine formats
        human_msg: Human-friendly message for human format
        format: Output format
        fields: Fields to include (machine formats only)
        no_header: Whether to omit header in CSV/TSV
    """
    if format == OutputFormat.human:
        print(human_msg)
    else:
        output(data, format=format, fields=fields, no_header=no_header)


def error(message: str, exit_code: int = 1) -> None:
    """Print error message to stderr."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def warn(message: str) -> None:
    """Print warning message to stderr."""
    print(f"warning: {message}", file=sys.stderr)


def info(message: str, verbose: bool = False) -> None:
    """Print info message to stderr if verbose."""
    if verbose:
        print(f"info: {message}", file=sys.stderr)


def verbose_print(message: str, verbose: bool = False) -> None:
    """Print verbose message to stderr if verbose mode is enabled.

    Use this for extra debug/info output that helps power users
    understand what the CLI is doing.
    """
    if verbose:
        print(f"[verbose] {message}", file=sys.stderr)


def status_print(message: str, quiet: bool = False) -> None:
    """Print status message to stderr unless quiet mode is enabled.

    Use this for informational messages that aren't errors but
    help users understand progress (e.g., "Opening browser...").
    """
    if not quiet:
        print(message, file=sys.stderr)
