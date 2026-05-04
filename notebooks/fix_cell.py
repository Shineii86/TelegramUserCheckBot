#@title 🤖 Launch Telegram Bot (Fixed)
#@markdown ---
#@markdown ### 🔑 Paste your Bot Token
BOT_TOKEN_HERE = ""  #@param {type:"string"}

#@markdown ---
#@markdown ### ▶️ Then run this cell!

import os, sys, asyncio
sys.path.insert(0, ".")

# ⚡ FIX: Patch event loop BEFORE importing telegram
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "nest_asyncio"])
    import nest_asyncio
    nest_asyncio.apply()

from IPython.display import display, HTML

if not BOT_TOKEN_HERE:
    print("❌ Please enter your BOT_TOKEN above.")
    print("   Get one from: https://t.me/BotFather → /newbot")
else:
    os.environ["TELEGRAM_BOT_TOKEN"] = BOT_TOKEN_HERE

    display(HTML('''
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
                padding: 20px; border-radius: 12px; font-family: sans-serif; margin: 10px 0;">
        <h3 style="margin:0 0 10px 0;">🤖 Telegram Bot is Starting...</h3>
        <p style="margin:0; opacity:0.9; line-height: 1.8;">
            ✅ Open <b>Telegram</b> and find your bot<br>
            ✅ Send <code>/start</code> to begin<br>
            ✅ Try: <code>/check username</code> or just type a username<br>
            ✅ <b>Keep this cell running!</b> Stopping it kills the bot
        </p>
    </div>
    '''))

    print("\n" + "═" * 50)
    print("  🤖 TelegramUserCheckBot is LIVE")
    print("═" * 50)
    print("  📱 /start /check /batch /generate /pattern /settings /stats /ping")
    print("  💡 Just type any username to quick-check")
    print("  🛑 Click ⏹️ to stop")
    print("═" * 50 + "\n")

    try:
        from bot.handlers import run_bot
        run_bot(BOT_TOKEN_HERE)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
