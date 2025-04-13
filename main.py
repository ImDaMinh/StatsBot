import os
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
from discord.ui import View, Button, Select
from discord import SelectOption
import asyncio
import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
import random
from itertools import combinations
from flask import Flask
from threading import Thread
import aiohttp
import traceback

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

REGION = 'euw1'
REGIONAL_ROUTE = 'europe'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='st/', intents=intents, help_command=None, case_insensitive=True)





# ✅ Trusted users who can access admin commands
ALLOWED_ADMINS = [569882415099674624, 298018954138353664] # Replace with your real Discord user IDs

# In-memory region settings (per user)
user_regions = {}

# Maps REGION to REGIONAL_ROUTE
region_routes = {
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",

    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",

    "kr": "asia",
    "jp1": "asia"
}

# ====== Embed Pages ======

def lol_help_embed(region, user_id):
    embed = discord.Embed(
        title="🏆 League of Legends Commands",
        description="Everything you need to track your Summoner 📊",
        color=discord.Color.from_rgb(28, 35, 41)
    )

    embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/lol_logo.png")
    embed.set_image(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/lol_banner.jpg")

    embed.add_field(
        name="🔓 Public Commands",
        value=(
            "**`st/Stats <RiotID>`** — Full LoL profile: Rank, LP, Winrate, KDA\n"
            "**`st/KDA <RiotID>`** — Average K/D/A (last 5 matches)\n"
            "**`st/Match <RiotID>`** — LoL Match History\n"
            "**`st/RankOnly <RiotID>`** — Only ranked stats"
        ),
        inline=False
    )

    # Show admin commands only if user is trusted
    if user_id in ALLOWED_ADMINS:
        embed.add_field(
            name="🔐 Admin Only",
            value="**`st/ResetStats`** — Reset all stats for testing\n"
                  "**`st/DebugLoL`** — Internal debug command",
            inline=False
        )

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")
    return embed

def tft_help_embed(region, user_id):
    embed = discord.Embed(
        title="🧠 Teamfight Tactics Commands",
        description="Everything TFT — placements, augments, and traits 📈",
        color=discord.Color.from_rgb(24, 68, 76)
    )

    embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/tft_logo.png")
    embed.set_image(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/tft_banner.jpg")

    embed.add_field(
        name="🔓 Public Commands",
        value=(
            "**`st/TFTMatch <RiotID>`** — Recent matches with traits, augments & units\n"
            "**`st/TFTRank <RiotID>`** — Your current TFT rank"
        ),
        inline=False
    )

    if user_id in ALLOWED_ADMINS:
        embed.add_field(
            name="🔐 Admin Only",
            value="**`st/TFTDebug`** — Shows raw match data (for testing)",
            inline=False
        )

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")
    return embed

def bot_help_embed(region, user_id):
    embed = discord.Embed(
        title="⚙️ Bot Settings & Utilities",
        description="Configure your Riot region, info tools, and more 🔧",
        color=discord.Color.from_rgb(54, 57, 63)
    )

    embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/botgear.png")
    embed.set_image(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/settings_banner.jpg")

    embed.add_field(
        name="🔓 Public Tools",
        value=(
            "**`st/Riotstatus`** — to check if Riot servers are online or having issues\n"
            "**`st/SetRegion <region>`** — Set your default Riot region\n"
            "**`st/Help`** or **`/help`** — View all commands\n"
            "**`st/Check`** — Check Riot ID and region"
        ),
        inline=False
    )

    if user_id in ALLOWED_ADMINS:
        embed.add_field(
            name="🔐 Admin Only",
            value="**`st/SyncSlash`**",
            inline=False
        )

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")
    return embed

def custom_help_embed(region, user_id):
    embed = discord.Embed(
        title="🛠️ Custom Matchmaking Commands",
        description="Tools for creating balanced custom games and Tournament🎯",
        color=discord.Color.from_rgb(83, 66, 187)
    )

    embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/custom.png")
    embed.set_image(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/match_banner.jpg")

    embed.add_field(
        name="🧩 Matchmaking Tools",
        value=(
            "**`st/Add <RiotID>`** — Add up to 10 Riot IDs (comma-separated)\n"
            "**`st/GT <num_teams>`** — Create AI-balanced teams (e.g. `st/gt 2`, `st/gt 4`)\n"
            "**`st/StatCount`** — View how many Riot IDs are saved\n"
            "**`st/Remove <RiotID>`** — Remove a Riot ID from saved list\n"
            "**`st/ClearStat`** — Wipe all added Riot IDs (admin only)"
        ),
        inline=False
    )

    if user_id in ALLOWED_ADMINS:
        embed.add_field(
            name="🔐 Admin Only",
            value="**`st/ResetStats`**, **`st/SyncSlash`**, **`st/DebugLoL`**, **`st/TFTDebug`**",
            inline=False
        )

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Team builder powered by AI 📊")
    return embed


# 🔹 Embed Helper Functions

class HelpView(View):
    def __init__(self, region, user_id):
        super().__init__(timeout=180)
        self.region = region
        self.user_id = user_id
        self.add_item(HelpDropdown(self.region, self.user_id))  # row=0 by default

    @discord.ui.button(
        label="🏠 Back to Menu",
        style=discord.ButtonStyle.secondary,
        custom_id="back_to_main",
        row=1
    )
    async def back_to_menu(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.id in ALLOWED_ADMINS
        greeting = "👋 Welcome!" if not is_admin else "👑 Hey, admin!"

        embed = discord.Embed(
            title=f"{greeting} Here’s your Help Menu",
            description=(
                "**Your all-in-one Riot ID tracker inside Discord.**\n\n"
                "🔹 Track League & TFT stats across regions\n"
                "🔹 Generate balance teams for tournament and custom match\n"
                "🔹 Match history, ranked info, region settings, and more!\n\n"
                "**Choose a category below to get started:**\n"
                "• 🏆 **LoL** — League of Legends stats & matches\n"
                "• 🧠 **TFT** — TFT placements, augments & traits\n"
                "• 🛠️ **Custom** — Add Riot IDs, generate fair teams\n"
                "• ⚙️ **Bot Settings** — Region config & admin tools"
            ),
            color=discord.Color.blurple()
        )

        embed.set_image(url="https://i.imgur.com/WZgFMyL.png")
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        embed.set_footer(text=f"🌍 Region: {self.region.upper()} • Powered by Riot Games API")

        await interaction.response.edit_message(embed=embed, view=self)


class HelpDropdown(Select):
    def __init__(self, region, user_id):
        self.region = region
        self.user_id = user_id
        options = [
            SelectOption(label="🏆 LoL", value="lol", description="League of Legends commands"),
            SelectOption(label="🧠 TFT", value="tft", description="Teamfight Tactics commands"),
            SelectOption(label="🛠️ Custom", value="custom", description="Custom team generator"),
            SelectOption(label="⚙️ Bot Settings", value="bot", description="Region & utility tools"),
        ]
        super().__init__(placeholder="📂 Choose a category", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "lol":
            embed = lol_help_embed(self.region, self.user_id)
        elif value == "tft":
            embed = tft_help_embed(self.region, self.user_id)
        elif value == "custom":
            embed = custom_help_embed(self.region, self.user_id)
        elif value == "bot":
            embed = bot_help_embed(self.region, self.user_id)
        else:
            embed = discord.Embed(title="❓ Unknown Category", color=discord.Color.red())

        await interaction.response.edit_message(embed=embed, view=self.view)


# ========== bot events ==========

async def on_command_error(ctx, error):
    # User-friendly messages
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing required argument. Please check `st/Help`.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `st/Help` to see valid options.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Please wait {round(error.retry_after, 1)}s before using this command again.")
    else:
        await ctx.send("❌ An unexpected error occurred. The developer has been notified.")

        # Send detailed traceback to admin(s)
        error_details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        for admin_id in ALLOWED_ADMINS:
            try:
                user = await bot.fetch_user(admin_id)
                if user:
                    embed = discord.Embed(
                        title="🚨 Bot Error Report",
                        description=f"An error occurred in `{ctx.command}`",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="User", value=f"{ctx.author} (`{ctx.author.id}`)", inline=False)
                    embed.add_field(name="Command", value=f"`{ctx.message.content}`", inline=False)
                    embed.add_field(name="Error", value=f"```{str(error)[:1000]}```", inline=False)
                    if len(error_details) <= 1024:
                        embed.add_field(name="Traceback", value=f"```{error_details}```", inline=False)
                    else:
                        embed.add_field(name="Traceback (truncated)", value=f"```{error_details[:1000]}```", inline=False)
                    embed.set_footer(text=f"Channel: #{ctx.channel} • Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
                    await user.send(embed=embed)
            except Exception as e:
                print(f"⚠️ Failed to DM admin ({admin_id}): {e}")


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"⚠️ Slash sync failed: {e}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_riot_key_reminder, 'cron', hour=22, minute=35, timezone='Europe/Paris')
    scheduler.add_job(periodic_reminder, 'interval', hours=3)  # ⏰ Add periodic reminder job
    scheduler.start()


async def send_riot_key_reminder():
    paris = pytz.timezone("Europe/Paris")
    now = datetime.datetime.now(paris).strftime("%Y-%m-%d %H:%M:%S")

    for admin_id in ALLOWED_ADMINS:
        try:
            user = await bot.fetch_user(admin_id)  # ✅ Works even if user is not cached
            embed = discord.Embed(
                title="🔐 Riot API Key Reminder",
                description="Your key’s about to expire! ⚠️ Don’t forget to refresh it.",
                color=discord.Color.red()
            )
            embed.add_field(name="🔗 Refresh Here:", value="[Riot Developer Portal](https://developer.riotgames.com/)", inline=False)
            embed.set_footer(text=f"🕰️ Sent at {now} (Paris time)")

            await user.send(embed=embed)
            print(f"[Reminder] ✅ Riot key reminder sent to {user} at {now}")
        except Exception as e:
            print(f"[Reminder] ❌ Failed to send DM to {admin_id}: {e}")



# 🔁 Periodic reminder every 6 hours (adjustable)
# 🔁 Periodic reminder every 6 hours (with auto-delete of previous message)
async def periodic_reminder():
    channel_id = 1355731331669037136  # Replace with your real channel ID
    channel = bot.get_channel(channel_id)
    if not channel:
        print("⚠️ Channel not found.")
        return

    try:
        # Load last message ID from file
        last_file = "last_reminder.json"
        if os.path.exists(last_file):
            with open(last_file, "r") as f:
                saved = json.load(f)
                old_channel_id = saved.get("channel_id")
                old_message_id = saved.get("message_id")

                # Try to delete previous message
                if old_channel_id == channel_id and old_message_id:
                    try:
                        old_msg = await channel.fetch_message(int(old_message_id))
                        await old_msg.delete()
                        print("🗑️ Deleted old reminder.")
                    except Exception as e:
                        print(f"⚠️ Could not delete old reminder: {e}")

        # Send new reminder
        embed = discord.Embed(
            title="✨ Need Help? Here's What You Can Do!",
            description=(
                "📡 Use **`st/`** as a prefix to start all commands\n"
                "📡 Try **`st/Help`** to explore commands and categories\n"
                "📡 Use **`st/RiotStatus`** to check Riot server status"
            ),
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/ImDaMinh/lolassets/botgear.png")
        embed.set_footer(text="Your friendly Statsbot assistant 💬")

        new_msg = await channel.send(embed=embed)

        # Save new message ID
        with open(last_file, "w") as f:
            json.dump({"channel_id": channel_id, "message_id": new_msg.id}, f)

        print(f"✅ Sent new reminder at {datetime.datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"❌ Error in periodic reminder: {e}")



# ========== Riot API Helper Functions ==========


def get_user_region(user_id):
    region = user_regions.get(user_id, "euw1")  # default to EUW
    route = region_routes.get(region, "europe")
    return region, route


async def get_account_by_riot_id_async(name, tag):
    headers = {"X-Riot-Token": RIOT_API_KEY}
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as res:
                if res.status == 200:
                    return await res.json()
                elif res.status == 404:
                    return None  # Riot ID not found
                else:
                    print(f"⚠️ Riot API error: {res.status} for {name}#{tag}")
                    return None
        except Exception as e:
            print(f"❌ Riot API exception: {e}")
            return None




async def get_summoner_by_puuid_async(session, puuid, region, route):
    headers = {"X-Riot-Token": RIOT_API_KEY}

    # Get LoL summoner data
    summoner_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    async with session.get(summoner_url, headers=headers) as res:
        if res.status != 200:
            return None
        summoner = await res.json()

    # Patch with Riot name info (optional but useful)
    account_url = f"https://{route}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    async with session.get(account_url, headers=headers) as res2:
        account = await res2.json() if res2.status == 200 else {}

    if 'name' not in summoner:
        riot_name = account.get('gameName')
        tag = account.get('tagLine')
        if riot_name and tag:
            summoner['name'] = f"{riot_name}#{tag}"

    return summoner


async def find_summoner_in_any_region(puuid):
    async with aiohttp.ClientSession() as session:
        tasks = []
        valid_regions = []

        for reg, route in region_routes.items():
            tasks.append(get_summoner_by_puuid_async(session, puuid, reg, route))
            valid_regions.append((reg, route))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (region_code, route), result in zip(valid_regions, results):
            if isinstance(result, Exception):
                print(f"⚠️ Error in region {region_code}: {result}")
                continue
            if result:
                return result, region_code, route

    return None, None, None




def get_ranked_data(summoner_id):
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else None

def get_recent_match_kda(puuid):
    matchlist_url = f"https://{REGIONAL_ROUTE}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    matches = requests.get(matchlist_url, headers=headers).json()

    if not isinstance(matches, list):
        return None

    kills = deaths = assists = 0
    count = 0

    for match_id in matches:
        match_url = f"https://{REGIONAL_ROUTE}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers=headers).json()
        participants = match_data.get("info", {}).get("participants", [])
        for p in participants:
            if p["puuid"] == puuid:
                kills += p["kills"]
                deaths += p["deaths"]
                assists += p["assists"]
                count += 1
                break

    if count == 0:
        return None

    return (
        round(kills / count, 1),
        round(deaths / count, 1),
        round(assists / count, 1)
    )

async def resolve_riot_id(ctx, riot_id):
    riot_id = riot_id.replace('-', '#').strip()
    if '#' not in riot_id:
        await ctx.send("❌ Invalid Riot ID format. Use `Name#Tag`.")
        return None, None, None, "invalid"

    name, tag = [part.strip() for part in riot_id.split('#', 1)]
    account = await get_account_by_riot_id_async(name, tag)

    if account is None or "puuid" not in account:
        embed = discord.Embed(
            title="❌ Riot ID Not Found",
            description="Double-check the spelling and format (e.g. **Name#Tag**).",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return None, None, None, "not_found"

    puuid = account["puuid"]
    user_region, user_route = get_user_region(ctx.author.id)

    async with aiohttp.ClientSession() as session:
        # ✅ Try user's preferred region first
        primary = await get_summoner_by_puuid_async(session, puuid, user_region, user_route)
        if primary:
            user_regions[ctx.author.id] = user_region
            return puuid, primary, primary.get("id"), "found"

        # 🔍 Scan all other regions
        tasks = []
        region_list = []
        for reg, route in region_routes.items():
            tasks.append(get_summoner_by_puuid_async(session, puuid, reg, route))
            region_list.append((reg, route))

        results = await asyncio.gather(*tasks)
        valid = [(r, res) for (r, _), res in zip(region_list, results) if res]

        if not valid:
            embed = discord.Embed(
                title="⚠️ Riot ID Found, But No League/TFT Data",
                description="This Riot ID exists, but has no public League or TFT data in any Riot-supported region.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Try again later or verify the account’s activity.")
            await ctx.send(embed=embed)
            return None, None, None, "no_data"

        if len(valid) == 1:
            region, summoner = valid[0]
            user_regions[ctx.author.id] = region
            return puuid, summoner, summoner.get("id"), "found"

        # ✨ Multiple regions found → ask user to choose
        view = View(timeout=30)
        message_sent = await ctx.send("⚠️ Multiple accounts found with the same Riot ID. Please choose one:")

        for reg_code, summoner in valid:
            level = summoner.get("summonerLevel", "?")
            label = f"{reg_code.upper()} (Level {level})"

            async def make_callback(region=reg_code, summ=summoner):
                async def callback(interaction):
                    if interaction.user != ctx.author:
                        return await interaction.response.send_message("⛔ Only the original user can select.", ephemeral=True)

                    user_regions[ctx.author.id] = region
                    await interaction.response.edit_message(content=f"✅ You selected `{region.upper()}`. Retrying command...", view=None)

                    # 🧠 Retry the exact same command message, patched with selected region
                    ctx.message.content = f"{ctx.prefix}{ctx.command.name} {riot_id}"
                    await bot.process_commands(ctx.message)
                return callback

            button = Button(label=label, style=discord.ButtonStyle.primary)
            button.callback = await make_callback()
            view.add_item(button)

        await message_sent.edit(view=view)
        return None, None, None, "multi_region_choice"



# ========== Command Core ==========
def parse_riot_id(riot_id):
    riot_id = riot_id.replace('-', '#').strip()
    if '#' not in riot_id:
        return None, None
    name, tag = riot_id.split('#', 1)
    return name.strip(), tag.strip()


def get_riot_data(riot_id, region, regional_route):
    name, tag = parse_riot_id(riot_id)
    if not name or not tag:
        return None, None, None

    account = get_account_by_riot_id(name, tag)
    if not account or 'puuid' not in account:
        return None, None, None

    puuid = account['puuid']
    summoner = get_summoner_by_puuid(puuid, region, regional_route)
    return puuid, summoner, summoner['id'] if summoner else None


# ========== Help Commands ==========


@bot.command(name="Help")
async def help_command(ctx):
    region, _ = get_user_region(ctx.author.id)
    is_admin = ctx.author.id in ALLOWED_ADMINS
    greeting = "👋 Welcome!" if not is_admin else "👑 Hey, admin!"

    # Initial loading message
    loading_msg = await ctx.send("🔁 Loading.")

    # Emoji animation: rotating spinner
    spinner_frames = [("🔁", "."), ("🔄", ".."), ("🔃", "...")]
    for emoji, dots in spinner_frames:
        await asyncio.sleep(0.5)
        await loading_msg.edit(content=f"{emoji} Loading{dots}")

    # Typing delay for polish
    async with ctx.typing():
        await asyncio.sleep(0.8)

    # Merged Intro + Help Overview Embed
    embed = discord.Embed(
        title=f"{greeting} Here’s your Help Menu",
        description=(
            "**Your all-in-one Riot ID tracker inside Discord.**\n\n"
            "🔹 Track League & TFT stats across regions\n"
            "🔹 Generate balance teams for tournament and custom match\n"
            "🔹 Match history, ranked info, region settings, and more!\n"
            "🔹 Custom commands for tournament!\n\n"
            "**Choose a category below to get started:**\n"
            "• 🏆 **LoL** — League of Legends stats & matches\n"
            "• 🧠 **TFT** — TFT placements, augments & traits\n"
            "• 🛠️ **Custom** — Add Riot IDs, generate fair teams\n"
            "• ⚙️ **Bot Settings** — Region config & admin tools"
        ),
        color=discord.Color.blurple()
    )
    embed.set_image(url="https://i.imgur.com/WZgFMyL.png")
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")

    await loading_msg.edit(content="", embed=embed, view=HelpView(region, ctx.author.id), delete_after=120)


# Slash Help Command (/help)

@bot.tree.command(name="help", description="Show interactive help menu")
async def slash_help(interaction: discord.Interaction):
    region, _ = get_user_region(interaction.user.id)
    is_admin = interaction.user.id in ALLOWED_ADMINS
    greeting = "👋 Welcome!" if not is_admin else "👑 Hey, admin!"

    # Send initial loading message
    await interaction.response.send_message("🔁 Loading.", ephemeral=True)
    message = await interaction.original_response()

    # Spinner animation with emoji + dots
    spinner_frames = [("🔁", "."), ("🔄", ".."), ("🔃", "...")]
    for emoji, dots in spinner_frames:
        await asyncio.sleep(0.5)
        await message.edit(content=f"{emoji} Loading{dots}")

    await asyncio.sleep(0.8)

    embed = discord.Embed(
        title=f"{greeting} Here’s your Help Menu",
        description=(
            "**Your all-in-one Riot ID tracker inside Discord.**\n\n"
            "🔹 Track League & TFT stats across regions\n"
            "🔹 Generate balance teams for tournament and custom match\n"
            "🔹 Match history, ranked info, region settings, and more!\n"
            "🔹 Custom commands for tournament!\n\n"
            "**Choose a category below to get started:**\n"
            "• 🏆 **LoL** — League of Legends stats & matches\n"
            "• 🧠 **TFT** — TFT placements, augments & traits\n"
            "• 🛠️ **Custom** — Add Riot IDs, generate fair teams\n"
            "• ⚙️ **Bot Settings** — Region config & admin tools"
        ),
        color=discord.Color.blurple()
    )
    embed.set_image(url="https://i.imgur.com/WZgFMyL.png")
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")

    await message.edit(content="", embed=embed, view=HelpView(region, interaction.user.id))


# ========== Lol Commands  ==========


@bot.command(name="Stats")
async def full_stats(ctx, *, riot_id):
    print(f"🟡 st/Stats command received: {riot_id}")

    # ✅ Use the new helper to resolve Riot ID
    puuid, summoner, summoner_id, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return  # Error embed already handled in helper

    region, regional_route = get_user_region(ctx.author.id)
    name = summoner.get("name", riot_id)
    icon_id = summoner.get("profileIconId", 29)
    level = summoner.get("summonerLevel", "Unknown")
    icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{icon_id}.png"

    headers = {"X-Riot-Token": RIOT_API_KEY}

    ranked_url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    ranked = requests.get(ranked_url, headers=headers).json()

    matchlist_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    matches = requests.get(matchlist_url, headers=headers).json()

    kills = deaths = assists = count = 0
    for match_id in matches:
        match_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers=headers).json()
        participants = match_data.get("info", {}).get("participants", [])
        for p in participants:
            if p["puuid"] == puuid:
                kills += p["kills"]
                deaths += p["deaths"]
                assists += p["assists"]
                count += 1
                break

    kda = (round(kills / count, 1), round(deaths / count, 1), round(assists / count, 1)) if count else None

    embed = discord.Embed(
        title=f"{name}'s League Profile",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=icon_url)
    embed.add_field(name="🌟 Summoner Level", value=f"**{level}**", inline=True)

    if ranked:
        for queue in ranked:
            qtype = queue['queueType'].replace('_', ' ').title()
            tier = queue['tier']
            rank = queue['rank']
            lp = queue['leaguePoints']
            wins = queue['wins']
            losses = queue['losses']
            wr = round((wins / (wins + losses)) * 100, 2)
            emoji = "🏆" if "Solo" in qtype else "🎯"
            embed.add_field(
                name=f"{emoji} {qtype}",
                value=f"**{tier} {rank}** – {lp} LP\n**{wins}W** / **{losses}L** ({wr}% WR)",
                inline=False
            )
    else:
        embed.add_field(name="🏆 Ranked", value="Unranked", inline=False)

    if kda:
        embed.add_field(name="⚔️ KDA (Last 5 Matches)", value=f"**{kda[0]} / {kda[1]} / {kda[2]}**", inline=False)
    else:
        embed.add_field(name="⚔️ KDA", value="No recent match data", inline=False)

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Use st/SetRegion <region> to change • Type st/Help for commands")
    await ctx.send(embed=embed)



@bot.command(name="RankOnly")
async def rank_only(ctx, *, riot_id):
    print(f"🟡 st/RankOnly command received: {riot_id}")

    puuid, summoner, summoner_id, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return

    region, _ = get_user_region(ctx.author.id)
    name = summoner.get("name", "Unknown Summoner")
    icon_id = summoner.get("profileIconId", 29)
    icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{icon_id}.png"

    ranked_url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    ranked = requests.get(ranked_url, headers={"X-Riot-Token": RIOT_API_KEY}).json()

    embed = discord.Embed(title=f"🏆 {name}'s Ranked Stats", color=discord.Color.gold())
    embed.set_thumbnail(url=icon_url)

    if ranked:
        for queue in ranked:
            qtype = queue['queueType'].replace('_', ' ').title()
            tier = queue['tier']
            rank = queue['rank']
            lp = queue['leaguePoints']
            wins = queue['wins']
            losses = queue['losses']
            wr = round((wins / (wins + losses)) * 100, 2)
            emoji = "🏆" if "Solo" in qtype else "🎯"

            embed.add_field(
                name=f"{emoji} **{qtype}**",
                value=f"**{tier} {rank}** — `{lp} LP`\n📊 {wins}W / {losses}L ({wr}% WR)",
                inline=False
            )
    else:
        embed.add_field(name="📉 Ranked", value="Unranked", inline=False)

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Use st/SetRegion <region> to change • Powered by Riot API")
    await ctx.send(embed=embed)





@bot.command(name="KDA")
async def kda_only(ctx, *, riot_id):
    print(f"🟡 st/KDA command received: {riot_id}")

    puuid, summoner, _, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return

    region, regional_route = get_user_region(ctx.author.id)
    name = summoner.get("name", riot_id)
    icon_id = summoner.get("profileIconId", 29)
    icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{icon_id}.png"

    matchlist_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    matches = requests.get(matchlist_url, headers={"X-Riot-Token": RIOT_API_KEY}).json()

    kills = deaths = assists = count = 0
    for match_id in matches:
        match_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers={"X-Riot-Token": RIOT_API_KEY}).json()
        for p in match_data.get("info", {}).get("participants", []):
            if p["puuid"] == puuid:
                kills += p["kills"]
                deaths += p["deaths"]
                assists += p["assists"]
                count += 1
                break

    kda = (round(kills/count, 1), round(deaths/count, 1), round(assists/count, 1)) if count else None

    embed = discord.Embed(
        title=f"⚔️ {name}'s KDA Summary",
        description="Last 5 Ranked or Normal Games",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=icon_url)

    if kda:
        embed.add_field(name="📊 Average K/D/A", value=f"**{kda[0]} / {kda[1]} / {kda[2]}**", inline=False)
    else:
        embed.add_field(name="📊 KDA", value="No recent match data available", inline=False)

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Use st/SetRegion to change • Powered by Riot API")
    await ctx.send(embed=embed)





@bot.command(name="Match")
async def match_history(ctx, *, riot_id):
    print(f"🟡 st/Match command received: {riot_id}")

    puuid, summoner, _, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return

    region, regional_route = get_user_region(ctx.author.id)
    name = summoner.get("name", "Unknown Summoner")
    icon_id = summoner.get("profileIconId", 29)
    icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{icon_id}.png"

    matchlist_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5"
    match_ids = requests.get(matchlist_url, headers={"X-Riot-Token": RIOT_API_KEY}).json()

    if not isinstance(match_ids, list) or len(match_ids) == 0:
        embed = discord.Embed(
            title="❌ No Recent Matches",
            description="This player hasn’t played any recent games, or data is unavailable.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot Games API")
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title=f"🎮 {name}'s Last 5 Matches",
        description="Match stats, game mode, champion, and win/loss 📜",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=icon_url)

    game_mode_emojis = {
        "ARAM": "❄️", "CLASSIC": "⚔️", "URF": "🚀",
        "CHERRY": "🏟️", "ARENA": "🏰", "ONEFORALL": "🧑‍🤝‍🧑",
        "PICK URF": "⚡", "TUTORIAL": "📘", "NEXUSBLITZ": "🔥",
        "UNKNOWN": "❓"
    }

    for match_id in match_ids:
        match_url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_data = requests.get(match_url, headers={"X-Riot-Token": RIOT_API_KEY}).json()
        info = match_data.get("info", {})
        raw_mode = info.get("gameMode", "UNKNOWN").upper()
        game_mode = "Arena" if raw_mode == "CHERRY" else raw_mode.title()
        duration = round(info.get("gameDuration", 0) / 60)

        for p in info.get("participants", []):
            if p["puuid"] == puuid:
                champ = p["championName"]
                k, d, a = p["kills"], p["deaths"], p["assists"]
                result = "✅ **Win**" if p["win"] else "❌ **Loss**"
                emoji = game_mode_emojis.get(raw_mode, "🎮")

                embed.add_field(
                    name=f"{emoji} {game_mode} • {champ} • {duration} min",
                    value=f"{result}\n**KDA**: `{k}/{d}/{a}`",
                    inline=False
                )
                break

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Use st/SetRegion to change • Powered by Riot Games API")
    await ctx.send(embed=embed)




# ========== TFT Commands  ==========


from discord.ui import View, Button

@bot.command(name="TFTMatch")
async def tft_match_history(ctx, *, riot_id):
    print(f"🟡 st/TFTMatch command received: {riot_id}")

    puuid, summoner, _, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return

    region, regional_route = get_user_region(ctx.author.id)
    name = summoner.get("name", riot_id)

    matchlist_url = f"https://{regional_route}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?start=0&count=5"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    match_ids = requests.get(matchlist_url, headers=headers).json()

    if not isinstance(match_ids, list) or len(match_ids) == 0:
        embed = discord.Embed(
            title="❌ No Recent TFT Matches",
            description="No recent TFT match history found for this player.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot API")
        return await ctx.send(embed=embed)

    pages = []

    for match_id in match_ids:
        match_url = f"https://{regional_route}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        match_data = requests.get(match_url, headers=headers).json()
        info = match_data.get("info", {})

        for p in info.get("participants", []):
            if p["puuid"] == puuid:
                placement = p.get("placement", "?")
                level = p.get("level", "?")
                gold = p.get("gold_left", "?")
                duration = round(info.get("game_length", 0) / 60)

                emoji = "🥇" if placement == 1 else "🥈" if placement == 2 else "🥉" if placement == 3 else (
                    "🟢" if placement <= 4 else "🟡" if placement <= 6 else "🔴")

                traits = ', '.join([
                    f"{t['name'].split('_')[-1].title()} (T{t['tier_current']})"
                    for t in p.get("traits", []) if t['tier_current'] >= 1
                ]) or "None"

                augments = ', '.join([
                    a.split('_')[-1]
                    .replace('Augment', '').replace('PlusPlus', '++').replace('Plus', '+')
                    .replace('TFT9_', '').replace('TFT6_', '').replace('TFT10_', '').replace('TFT_', '')
                    .replace('_', ' ').title()
                    for a in p.get("augments", [])
                ]) or "None"

                units = ', '.join([
                    f"{u['character_id'].split('_')[-1].title()}⭐{u['tier']}"
                    for u in p.get("units", [])
                ]) or "None"

                traits_safe = traits if len(traits) <= 300 else traits[:297] + "..."
                augments_safe = augments if len(augments) <= 300 else augments[:297] + "..."
                units_safe = units if len(units) <= 300 else units[:297] + "..."

                match_header = f"{emoji} Placement {placement} • Level {level} • {duration} min"

                embed = discord.Embed(title=f"{name}'s TFT Match", color=discord.Color.teal())
                embed.set_author(name="Recent TFT Matches", icon_url="https://i.imgur.com/bXFzldD.png")
                embed.add_field(
                    name=match_header,
                    value=(
                        f"💰 Gold Left: `{gold}`\n"
                        f"🧬 Traits: `{traits_safe}`\n"
                        f"🎯 Augments: `{augments_safe}`\n"
                        f"🧙 Units: `{units_safe}`"
                    ),
                    inline=False
                )
                pages.append(embed)
                break

    # ✅ Add page footer with numbering
    for i, embed in enumerate(pages):
        embed.set_footer(
            text=f"📄 Match {i + 1} of {len(pages)} • 🌍 Region: {region.upper()} • Powered by Riot API"
        )

    # Show first page with buttons
    if pages:
        current_page = 0

        class TFTMatchView(View):
            def __init__(self):
                super().__init__(timeout=180)

            @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
            async def previous(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if current_page > 0:
                    current_page -= 1
                    await interaction.response.edit_message(embed=pages[current_page], view=self)

            @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
            async def next(self, interaction: discord.Interaction, button: Button):
                nonlocal current_page
                if current_page < len(pages) - 1:
                    current_page += 1
                    await interaction.response.edit_message(embed=pages[current_page], view=self)

        await ctx.send(embed=pages[0], view=TFTMatchView())
    else:
        await ctx.send("⚠️ Could not retrieve TFT matches.")






@bot.command(name="TFTRank")
async def tft_rank(ctx, *, riot_id):
    print(f"🟡 st/TFTRank command received: {riot_id}")

    puuid, summoner, summoner_id, status = await resolve_riot_id(ctx, riot_id)
    if status != "found":
        return

    region, _ = get_user_region(ctx.author.id)
    name = summoner.get("name", riot_id)

    ranked_url = f"https://{region}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    ranked = requests.get(ranked_url, headers=headers).json()

    embed = discord.Embed(title=f"{name}'s TFT Ranked Stats", color=discord.Color.blue())
    embed.set_thumbnail(url="https://i.imgur.com/bXFzldD.png")

    if ranked:
        for queue in ranked:
            if queue['queueType'] == "RANKED_TFT":
                tier = queue['tier']
                rank = queue['rank']
                lp = queue['leaguePoints']
                wins = queue['wins']
                losses = queue['losses']
                wr = round(wins / (wins + losses) * 100, 2)
                embed.add_field(
                    name="🏆 RANKED TFT",
                    value=f"{tier} {rank} - {lp} LP\n{wins}W / {losses}L ({wr}% WR)",
                    inline=False
                )
                break
    else:
        embed.add_field(name="📉 TFT Ranked", value="Unranked", inline=False)

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Powered by Riot API")
    await ctx.send(embed=embed)


# ========== Custom Commands  ==========

@bot.command(name="Check")
async def check_riot_id(ctx, *, riot_id):
    print(f"🟡 st/Check command received: {riot_id}")

    puuid, summoner, _, status = await resolve_riot_id(ctx, riot_id)

    if status == "invalid":
        return  # Already sent error
    elif status == "not_found":
        return  # Already sent error
    elif status == "unsupported":
        return  # Already sent error
    elif status == "no_data":
        return  # Already sent error

    # ✅ If we got here, the Riot ID exists and has summoner data
    riot_name = summoner.get("name", riot_id)
    region, route = get_user_region(ctx.author.id)
    headers = {"X-Riot-Token": RIOT_API_KEY}

    # Scan only current region for LoL/TFT
    lol_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    tft_url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    lol_res = requests.get(lol_url, headers=headers)
    tft_res = requests.get(tft_url, headers=headers)

    has_lol = lol_res.status_code == 200
    has_tft = tft_res.status_code == 200

    embed = discord.Embed(
        title=f"🔍 Riot ID Check: {riot_name}",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url="https://i.imgur.com/Ce4GrEz.png")
    embed.add_field(name="💬 Riot ID Status", value="✅ Valid Riot ID", inline=True)

    if has_lol or has_tft:
        found_in = []
        if has_lol:
            found_in.append("⚔️ League of Legends")
        if has_tft:
            found_in.append("🔮 Teamfight Tactics")
        embed.add_field(
            name=f"✅ Found in {region.upper()}",
            value="\n".join(found_in),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ No LoL or TFT Data Found",
            value=(
                "This Riot ID exists but has no public **LoL** or **TFT** data "
                f"in `{region.upper()}`.\nIt might be inactive or private."
            ),
            inline=False
        )

    embed.set_footer(text=f"🌍 Auto-detected Region: {region.upper()} • Use st/SetRegion if needed")
    await ctx.send(embed=embed)



@bot.command(name="Add")
async def add_riot_ids(ctx, *, riot_ids):
    ids = [r.strip() for r in riot_ids.split(',')]
    if len(ids) > 10:
        return await ctx.send("❌ You can only add up to 10 Riot IDs at a time.")

    try:
        file_path = f"statdata_{ctx.author.id}.json"
        if os.path.exists(file_path) and os.stat(file_path).st_size > 0:
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            data = []
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    existing_ids = {entry["riot_id"].lower() for entry in data}
    added = []

    for riot_id in ids:
        puuid, summoner, summoner_id, status = await resolve_riot_id(ctx, riot_id)

        if status != "found":
            continue  # Already handled error message in resolve_riot_id

        region, route = get_user_region(ctx.author.id)
        name = summoner.get("name", riot_id)
        if name.lower() in existing_ids:
            await ctx.send(f"⚠️ `{name}` is already in your saved data. Skipped.")
            continue

        ranked_data = get_ranked_data(summoner_id)
        kda = get_recent_match_kda(puuid)
        level = summoner.get("summonerLevel", "?")
        icon_id = summoner.get("profileIconId", 29)
        icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.6.1/img/profileicon/{icon_id}.png"

        entry = {
            "riot_id": name,
            "level": level,
            "kda": kda if kda else (0, 0, 0),
            "ranked": ranked_data if ranked_data else []
        }
        added.append(entry)

        embed = discord.Embed(
            title=f"✅ Added {name}",
            description=f"📥 Riot ID has been saved.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=icon_url)
        embed.add_field(name="🌟 Level", value=f"**{level}**", inline=True)

        if ranked_data:
            for queue in ranked_data:
                qtype = queue['queueType'].replace('_', ' ').title()
                tier = queue['tier']
                rank = queue['rank']
                lp = queue['leaguePoints']
                wins = queue['wins']
                losses = queue['losses']
                wr = round((wins / (wins + losses)) * 100, 2)
                emoji = "🏆" if "Solo" in qtype else "🎯"
                embed.add_field(
                    name=f"{emoji} {qtype}",
                    value=f"{tier} {rank} - {lp} LP\n{wins}W / {losses}L ({wr}% WR)",
                    inline=False
                )
        else:
            embed.add_field(name="📊 Ranked", value="Unranked", inline=False)

        if kda:
            embed.add_field(name="⚔️ KDA (Last 5)", value=f"{kda[0]} / {kda[1]} / {kda[2]}", inline=False)

        embed.set_footer(text=f"🌍 Region: {region.upper()} • Use -GT to generate fair teams")
        await ctx.send(embed=embed)

    # Save new entries
    if added:
        data.extend(added)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)


@bot.command(name="GT")
async def generate_teams(ctx, num_teams: int = 2):
    try:
        file_path = f"statdata_{ctx.author.id}.json"
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return await ctx.send("❌ No stat data available. Add Riot IDs with `st/Add <RiotID>`.")

    players_per_team = 5
    if num_teams < 2 or num_teams > 20:
        return await ctx.send("❌ Choose a number of teams between 2 and 20.")
    if len(data) != num_teams * players_per_team:
        return await ctx.send(f"❌ You need exactly **{num_teams * players_per_team}** players to form {num_teams} balanced teams of 5.")

    rank_weights = {
        "IRON": 1, "BRONZE": 2, "SILVER": 3, "GOLD": 4,
        "PLATINUM": 5, "EMERALD": 6, "DIAMOND": 7,
        "MASTER": 8, "GRANDMASTER": 9, "CHALLENGER": 10
    }

    def get_primary_rank_info(ranked_list):
        for entry in ranked_list:
            if "SOLO" in entry.get("queueType", ""):
                return entry
        return ranked_list[0] if ranked_list else None

    def get_score(player):
        kda = player.get("kda", [0, 0, 0])
        avg_kda = sum(kda) / 3
        ranked = get_primary_rank_info(player.get("ranked", []))
        wr = (ranked["wins"] / (ranked["wins"] + ranked["losses"])) if ranked else 0.5
        rank_weight = rank_weights.get(ranked["tier"].upper(), 1) if ranked else 1
        return avg_kda * 2.0 + (wr * 100) * 0.5 + rank_weight * 10

    def format_player(p):
        kda = p["kda"]
        ranked = get_primary_rank_info(p["ranked"])
        level = p.get("level", "?")
        riot_id = p.get("riot_id", "Unknown")
        if ranked:
            tier = ranked.get("tier", "Unranked")
            lp = ranked.get("leaguePoints", 0)
            wins = ranked.get("wins", 0)
            losses = ranked.get("losses", 0)
            wr = round((wins / (wins + losses)) * 100, 2)
            rank_str = f"{tier} - {lp} LP • {wins}W / {losses}L ({wr}% WR)"
        else:
            rank_str = "Unranked"
        return f"**{riot_id}** (Lv{level})\n🏆 {rank_str}\n⚔️ KDA: `{kda[0]}/{kda[1]}/{kda[2]}`"

    def team_average(team):
        total_kills = total_deaths = total_assists = total_wr = total_rank = 0
        count = len(team)
        for p in team:
            k, d, a = p["kda"]
            total_kills += k
            total_deaths += d
            total_assists += a
            ranked = get_primary_rank_info(p["ranked"])
            wr = (ranked["wins"] / (ranked["losses"] + ranked["wins"])) if ranked else 0.5
            rank = rank_weights.get(ranked["tier"].upper(), 1) if ranked else 1
            total_wr += wr
            total_rank += rank
        return (
            round(total_kills / count, 1),
            round(total_deaths / count, 1),
            round(total_assists / count, 1),
            round((total_wr / count) * 100, 2),
            round(total_rank / count)
        )

    def rank_from_weight(w):
        for r, v in rank_weights.items():
            if v == w:
                return r.title()
        return "Unranked"

    best_score_diff = float("inf")
    best_teams = []
    for _ in range(1000):
        random.shuffle(data)
        teams = [data[i * players_per_team:(i + 1) * players_per_team] for i in range(num_teams)]
        scores = [sum(get_score(p) for p in team) for team in teams]
        diff = max(scores) - min(scores)
        if diff < best_score_diff:
            best_score_diff = diff
            best_teams = teams

    embed = discord.Embed(
        title="⚖️ Balanced Custom Teams",
        description=f"{len(data)} players → {num_teams} teams • Balanced by KDA, Winrate, and Rank",
        color=discord.Color.purple()
    )

    emojis = ["🟥", "🟦", "🟩", "🟨", "🟧", "🟪", "🟫", "⬛", "⬜", "🟤"]
    for i, team in enumerate(best_teams):
        color_emoji = emojis[i % len(emojis)]
        team_title = f"{color_emoji} Team {i+1}"
        value = ""

        for p in team:
            value += format_player(p) + "\n━━━━━━━━━━━━━\n"

        k, d, a, wr, r = team_average(team)
        value += f"\n📊 Avg: KDA {k}/{d}/{a} • Winrate {wr}% • Rank {rank_from_weight(r)}"
        embed.add_field(name=team_title, value=value, inline=False)

    embed.set_footer(text="📌 Use st/ClearStat to reset player list • Custom team builder powered by AI")
    await ctx.send(embed=embed)


@bot.command(name="StatCount")
async def stat_count(ctx):
    file_path = f"statdata_{ctx.author.id}.json"
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        count = len(data)
        await ctx.send(f"📊 You have **{count} Riot ID(s)** saved for matchmaking.")
    except FileNotFoundError:
        await ctx.send("⚠️ You have not added any Riot ID yet. Use `st/Add` to get started.")



@bot.command(name="ClearStat")
async def clear_statdata(ctx):
    file_path = f"statdata_{ctx.author.id}.json"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            count = len(data)
        else:
            count = 0

        with open(file_path, "w") as f:
            json.dump([], f, indent=4)

        embed = discord.Embed(
            title="🧹 Statdata Cleared",
            description=f"Successfully removed `{count}` Riot ID(s) from your personal list.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Your custom match data has been reset.")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Failed to clear your data: `{e}`")



@bot.command(name="Remove")
async def remove_riot_id(ctx, *, riot_id):
    file_path = f"statdata_{ctx.author.id}.json"
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return await ctx.send("❌ Failed to load your data. File may be missing or corrupted.")

    riot_id_clean = riot_id.strip().lower()
    original_count = len(data)
    updated_data = [entry for entry in data if entry.get("riot_id", "").lower() != riot_id_clean]

    if len(updated_data) == original_count:
        return await ctx.send(f"⚠️ Riot ID `{riot_id}` was not found in your saved data.")

    with open(file_path, "w") as f:
        json.dump(updated_data, f, indent=4)

    embed = discord.Embed(
        title="🗑️ Riot ID Removed",
        description=f"Successfully removed `{riot_id}` from your saved custom data.",
        color=discord.Color.orange()
    )
    embed.set_footer(text="Use st/StatCount to view remaining Riot IDs.")
    await ctx.send(embed=embed)





# ========== Setting Commands  ==========

@bot.command(name="RiotStatus")
async def riot_status(ctx):
    region, _ = get_user_region(ctx.author.id)
    url = f"https://{region}.api.riotgames.com/lol/status/v4/platform-data"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            statuses = data.get("incidents", [])

            if statuses:
                embed = discord.Embed(
                    title="⚠️ Riot Server Incident(s) Reported",
                    color=discord.Color.orange()
                )
                for incident in statuses:
                    updates = incident.get("updates", [])
                    if updates:
                        latest = updates[0]
                        embed.add_field(
                            name=incident.get("titles", [{}])[0].get("content", "Incident"),
                            value=latest.get("translations", [{}])[0].get("content", "No details."),
                            inline=False
                        )
            else:
                embed = discord.Embed(
                    title="✅ Riot Servers Look Healthy",
                    description="No incidents or outages reported by Riot.",
                    color=discord.Color.green()
                )
        else:
            embed = discord.Embed(
                title="❌ Could Not Fetch Riot Status",
                description=f"Riot API returned `{res.status_code}` — may be temporarily down.",
                color=discord.Color.red()
            )

    except Exception as e:
        embed = discord.Embed(
            title="❌ Failed to Connect to Riot API",
            description=f"Likely a network issue or invalid Riot API key.\n\n`{e}`",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"🌍 Region: {region.upper()} • Use st/SetRegion to change")
    await ctx.send(embed=embed)


@bot.command(name="SetRegion")
async def set_region(ctx, region_code):
    region_code = region_code.lower()

    if region_code not in region_routes:
        await ctx.send(
            "❌ Invalid region code.\n"
            "Try one of: `euw1`, `na1`, `eun1`, `kr`, `br1`, `jp1`, `la1`, `la2`, `tr1`, `ru`, `oc1`"
        )
        return

    user_regions[ctx.author.id] = region_code
    await ctx.send(f"✅ Region set to `{region_code.upper()}` for your commands!")


# ========== ADmin Commands  ==========


@bot.command(name="ResetStats")
async def reset_stats(ctx):
    if ctx.author.id not in ALLOWED_ADMINS:
        return await ctx.send("❌ You do not have permission to use this command.")
    
    # Placeholder for reset logic
    await ctx.send("🔁 Stats have been reset!")



@bot.command(name="DebugLoL")
async def debug_lol(ctx):
    if ctx.author.id not in ALLOWED_ADMINS:
        return await ctx.send("❌ You do not have permission.")
    
    region, route = get_user_region(ctx.author.id)
    await ctx.send(f"🧪 LoL Debug:\nRegion: `{region}`\nRoute: `{route}`\nUser: `{ctx.author}`")



@bot.command(name="TFTDebug")
async def tft_debug(ctx):
    if ctx.author.id not in ALLOWED_ADMINS:
        return await ctx.send("❌ You do not have permission.")
    
    region, route = get_user_region(ctx.author.id)
    await ctx.send(f"🧪 TFT Debug:\nRegion: `{region}`\nRoute: `{route}`\nUser: `{ctx.author}`")

    


@bot.command(name="SyncSlash")
async def sync_slash(ctx):
    if ctx.author.id not in ALLOWED_ADMINS:
        return await ctx.send("❌ You do not have permission.")
    
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced `{len(synced)}` slash command(s).")
    except Exception as e:
        await ctx.send(f"⚠️ Sync failed: `{e}`")


app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


# 🚀 Run the bot
bot.run(DISCORD_BOT_TOKEN)
