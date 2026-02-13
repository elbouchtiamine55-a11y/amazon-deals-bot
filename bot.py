import discord
from discord.ext import commands, tasks
import requests
import os

# ==============================
# CONFIGURATION
# ==============================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("API_KEY")
CHECK_INTERVAL = 300  # 5 minutes
MIN_DISCOUNT = 25  # réduction minimale (%)

# ==============================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_channels = set()
sent_links = set()

CATEGORIES = {
    "GPU": "graphics card",
    "Casques": "headphones",
    "SSD": "ssd",
    "Smartphones": "smartphone"
}


def get_deals():
    deals = []

    for category, keyword in CATEGORIES.items():
        url = "https://api.rainforestapi.com/request"
        params = {
            "api_key": API_KEY,
            "type": "search",
            "amazon_domain": "amazon.fr",
            "search_term": keyword,
            "sort_by": "price_low_to_high"
        }

        response = requests.get(url, params=params)
        data = response.json()

        for product in data.get("search_results", [])[:10]:
            price_data = product.get("price", {})
            price = price_data.get("value")

            original_price_data = product.get("list_price", {})
            original_price = original_price_data.get("value")

            title = product.get("title")
            link = product.get("link")
            image = product.get("image")

            if not price or not original_price:
                continue

            discount = (original_price - price) / original_price * 100

            if discount >= MIN_DISCOUNT:
                deals.append({
                    "title": f"[{category}] {title}",
                    "price": price,
                    "original_price": original_price,
                    "discount": int(discount),
                    "link": link,
                    "image": image
                })

    return deals


async def send_deal(deal, channel):
    embed = discord.Embed(
        title=deal["title"],
        url=deal["link"],
        description=(
            f"💸 **{deal['price']}€** au lieu de {deal['original_price']}€\n"
            f"🔥 Réduction : **-{deal['discount']}%**"
        ),
        color=0x00ff99
    )
    embed.set_image(url=deal["image"])
    await channel.send(embed=embed)


@tasks.loop(seconds=CHECK_INTERVAL)
async def deal_loop():
    deals = get_deals()

    for deal in deals:
        if deal["link"] in sent_links:
            continue

        sent_links.add(deal["link"])

        for channel_id in tracked_channels:
            channel = bot.get_channel(channel_id)
            if channel:
                await send_deal(deal, channel)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    deal_loop.start()


# ==============================
# COMMANDES DISCORD
# ==============================

@bot.command()
async def start(ctx):
    tracked_channels.add(ctx.channel.id)
    await ctx.send("✅ Alertes activées dans ce salon.")


@bot.command()
async def stop(ctx):
    if ctx.channel.id in tracked_channels:
        tracked_channels.remove(ctx.channel.id)
        await ctx.send("⛔ Alertes désactivées.")
    else:
        await ctx.send("Ce salon n'était pas actif.")


@bot.command()
async def status(ctx):
    if ctx.channel.id in tracked_channels:
        await ctx.send("🟢 Alertes actives.")
    else:
        await ctx.send("🔴 Alertes inactives.")


bot.run(DISCORD_TOKEN)
