import discord
from discord.ext import commands, tasks
import requests

# Replace 'YOUR_DISCORD_BOT_TOKEN' with your Discord bot token
DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
# Replace 'YOUR_TORN_API_KEY' with your Torn API key
TORN_API_KEY = "YOUR_TORN_API_KEY"
# Replace 'YOUR_CHANNEL_ID' with the ID of the Discord channel where the bot should post messages
CHANNEL_ID = YOUR_CHANNEL_ID

# Torn API URL
TORN_API_URL = f"https://api.torn.com/faction/?selections=chain&key={TORN_API_KEY}"

# Thresholds for warnings
WARN_THRESHOLDS = [120, 90, 60, 45, 30]

# Bot setup
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# State tracking for thresholds and chain activity
last_timeout = None
threshold_announced = set()


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    check_chain_status.start()


@tasks.loop(seconds=10)
async def check_chain_status():
    global last_timeout, threshold_announced

    try:
        # Make the GET request to the Torn API
        response = requests.get(TORN_API_URL)
        data = response.json()

        if "error" in data:
            print(f"API Error: {data['error']['error']}")
            return

        timeout = data.get("timeout")
        if timeout is None:
            print("No timeout value found in API response.")
            return

        # Get the assigned channel
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("Channel not found. Ensure the bot is in the server and the CHANNEL_ID is correct.")
            return

        # Check thresholds
        for threshold in WARN_THRESHOLDS:
            if threshold not in threshold_announced and timeout <= threshold:
                await channel.send(f"⚠️ Chain timeout warning: {timeout // 60}:{timeout % 60:02d} remaining!")
                threshold_announced.add(threshold)

        # Check if the timeout reset (indicating a successful hit)
        if last_timeout is not None and last_timeout <= 30 and timeout > 250:
            await channel.send("🎉 Nice hit! The chain is reset and active again!")
            threshold_announced.clear()  # Reset threshold announcements

        # Update the last timeout
        last_timeout = timeout

    except Exception as e:
        print(f"Error in check_chain_status: {e}")


# Run the bot
bot.run(DISCORD_BOT_TOKEN)
