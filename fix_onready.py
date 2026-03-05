content = open('main.py').read()
old = '@bot.event                                                                                                                                              \nasync def on_ready():\n    from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView\n    bot.add_view(MidmanMainView())\n    bot.add_view(AdminSetupView())\n    bot.add_view(TradeFinishView())\n    print(f"Online sebagai {bot.user}")\n\n'
new = ''
content = content.replace(old, new)
open('main.py', 'w').write(content)
print("Done!")
