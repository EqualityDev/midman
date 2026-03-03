import os
base = "/data/data/com.termux/files/home/midman_bot"

with open(f"{base}/cogs/modals.py", "r") as f:
    code = f.read()

old = """    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)"""

new = """    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        guild = interaction.guild

        # Cek apakah user sudah punya tiket aktif
        for ch_id, t in cog.active_tickets.items():
            if t["pihak1"] and t["pihak1"].id == interaction.user.id:
                ch = guild.get_channel(ch_id)
                if ch:
                    await interaction.response.send_message(
                        f"Kamu masih memiliki tiket aktif: {ch.mention}\\nSelesaikan tiket tersebut sebelum membuka yang baru.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Kamu masih memiliki tiket aktif. Selesaikan tiket tersebut sebelum membuka yang baru.",
                        ephemeral=True
                    )
                return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)"""

code = code.replace(old, new)

with open(f"{base}/cogs/modals.py", "w") as f:
    f.write(code)

print("Berhasil.")
