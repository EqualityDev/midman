import discord
import io


async def generate(channel):
    lines = [f"TRANSCRIPT — {channel.name}\n"]
    async for msg in channel.history(limit=200, oldest_first=True):
        ts = msg.created_at.strftime("%d/%m/%Y %H:%M:%S")
        lines.append(f"[{ts}] {msg.author}: {msg.content}")
    return discord.File(
        fp=io.StringIO("\n".join(lines)),
        filename=f"transcript-{channel.name}.txt"
    )
