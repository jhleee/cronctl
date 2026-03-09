from __future__ import annotations

import click

from cronctl.cli.support import emit, exit_with_error, get_runtime_for_context
from cronctl.core.config import save_config
from cronctl.core.models import NotifyChannel


@click.group()
def notify() -> None:
    """Notification commands."""


@notify.command(name="setup")
@click.option("--non-interactive", is_flag=True, help="Do not prompt; use provided flags only")
@click.option("--discord-webhook", default=None, help="Discord webhook URL")
@click.option("--slack-webhook", default=None, help="Slack webhook URL")
@click.option("--webhook-url", default=None, help="Generic webhook URL")
@click.option("--method", default="POST", show_default=True, help="Generic webhook method")
@click.option("--header", "headers", multiple=True, help="Generic webhook header KEY=VALUE")
@click.option("--replace", is_flag=True, help="Replace existing configured channels")
@click.pass_context
def setup_notify(
    ctx: click.Context,
    non_interactive: bool,
    discord_webhook: str | None,
    slack_webhook: str | None,
    webhook_url: str | None,
    method: str,
    headers: tuple[str, ...],
    replace: bool,
) -> None:
    """Configure notification channels."""
    runtime = get_runtime_for_context(ctx)
    config = runtime.config
    channels = [] if replace else list(config.notifications.channels)
    if discord_webhook:
        channels.append(NotifyChannel(type="discord", webhook_url=discord_webhook))
    if slack_webhook:
        channels.append(NotifyChannel(type="slack", webhook_url=slack_webhook))
    if webhook_url:
        parsed_headers: dict[str, str] = {}
        for item in headers:
            key, _, value = item.partition("=")
            if not key or not _:
                exit_with_error(ctx, f"Invalid header assignment: {item}")
                return
            parsed_headers[key] = value
        channels.append(
            NotifyChannel(
                type="webhook",
                url=webhook_url,
                method=method.upper(),
                headers=parsed_headers,
            )
        )
    if not non_interactive and not any([discord_webhook, slack_webhook, webhook_url]):
        choice = click.Choice(["discord", "slack", "webhook"], case_sensitive=False)
        while True:
            channel_type = click.prompt("Channel type", type=choice)
            if channel_type == "discord":
                channels.append(
                    NotifyChannel(type="discord", webhook_url=click.prompt("Discord webhook URL"))
                )
            elif channel_type == "slack":
                channels.append(
                    NotifyChannel(type="slack", webhook_url=click.prompt("Slack webhook URL"))
                )
            else:
                channels.append(NotifyChannel(type="webhook", url=click.prompt("Webhook URL")))
            if not click.confirm("Add another channel?", default=False):
                break
    config.notifications.channels = channels
    save_config(runtime.paths, config)
    emit(
        ctx,
        {"updated": True, "channels": [channel.to_dict() for channel in channels]},
        human=f"Configured {len(channels)} notification channel(s)",
    )


@notify.command(name="test")
@click.pass_context
def test_notify(ctx: click.Context) -> None:
    """Send a test notification."""
    runtime = get_runtime_for_context(ctx)
    if not runtime.config.notifications.channels:
        exit_with_error(ctx, "No notification channels are configured")
        return
    result = runtime.notifier.send_test(runtime.config)
    emit(ctx, result.to_dict(), human=f"Delivered={result.delivered} failed={result.failed}")
