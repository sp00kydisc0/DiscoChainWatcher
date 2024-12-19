import discord
from discord.ext import commands, tasks
import requests

# Replace these with your actual values
DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
TORN_API_KEY = "YOUR_TORN_API_KEY"
CHANNEL_ID = YOUR_CHANNEL_ID

# Torn API URL
TORN_API_URL = f"https://api.torn.com/faction/?selections=chain&key={TORN_API_KEY}"

# Thresholds for warnings
WARN_THRESHOLDS = [120, 90, 60, 30]

# Bot setup
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# State tracking for thresholds, chain activity, and message suppression
last_timeout = None
last_announced_threshold = {}  # To prevent duplicate messages
threshold_announced = set()
chain_dropped = False  # Track if a "chain dropped" message was sent

# Task loop: Runs every 30 seconds to match Torn API updates
@tasks.loop(seconds=30)
async def check_chain_status():
    global last_timeout, threshold_announced, last_announced_threshold, chain_dropped

    try:
        # Make the GET request to the Torn API
        response = requests.get(TORN_API_URL)
        data = response.json()

        # Debugging: Print the entire API response
        print("API Response:", data)

        # Access the timeout value and current chain from the response
        chain_data = data.get("chain", {})
        timeout = chain_data.get("timeout")
        current_chain = chain_data.get("current", 0)

        if timeout is None:
            print("No timeout value found in API response.")
            return

        # Ignore chains that are not "real" (current chain < 10)
        if current_chain < 10:
            print("Current chain is below threshold (10). Skipping warnings.")
            return

        # Get the assigned channel
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("Channel not found. Ensure the bot is in the server and the CHANNEL_ID is correct.")
            return

        # Check thresholds and send warnings only once per threshold
        for threshold in WARN_THRESHOLDS:
            if threshold not in threshold_announced and timeout <= threshold:
                if last_announced_threshold.get(threshold) != timeout:
                    await channel.send(f"⚠️ Chain timeout warning: Less than {threshold // 60}:{threshold % 60:02d} remaining!")
                    last_announced_threshold[threshold] = timeout
                    threshold_announced.add(threshold)

        # Check if the timeout reset (indicating a successful hit)
        if last_timeout is not None and last_timeout <= 30 and timeout > 250:
            await channel.send("🎉 Nice hit! The chain is reset and active again!")
            threshold_announced.clear()  # Reset threshold announcements
            last_announced_threshold.clear()  # Clear the threshold tracking
            chain_dropped = False  # Reset the chain dropped flag

        # Send a "chain dropped" message when timeout reaches 0, but only once
        if timeout == 0 and not chain_dropped and last_timeout is not None and last_timeout <= 30:
            await channel.send("💔 The chain has dropped. Better luck next time!")
            chain_dropped = True  # Ensure this message is sent only once

        # Update the last timeout
        last_timeout = timeout

    except Exception as e:
        print(f"Error in check_chain_status: {e}")

# Event to start the task loop when the bot is ready
@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    check_chain_status.start()

# Run the bot
bot.run(DISCORD_BOT_TOKEN)
