import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!!", intents=intents)

# 数据库初始化
def init_db():
    conn = sqlite3.connect('trigger_words.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS triggers
                 (channel_id INTEGER, key TEXT, response TEXT)''')
    conn.commit()
    conn.close()

# 从数据库加载触发词
def load_triggers():
    conn = sqlite3.connect('trigger_words.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, key, response FROM triggers")
    rows = c.fetchall()
    trigger_words = {}
    for row in rows:
        channel_id, key, response = row
        if channel_id not in trigger_words:
            trigger_words[channel_id] = {}
        trigger_words[channel_id][key] = response
    conn.close()
    return trigger_words

# 初始化数据库和加载触发词
init_db()
trigger_words = load_triggers()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    channel_triggers = trigger_words.get(message.channel.id, {})
    for key in channel_triggers:
        if key in message.content:
            await message.reply(channel_triggers[key])
            break
    await bot.process_commands(message)

@bot.tree.command(name="add_trigger")
@app_commands.checks.has_permissions(administrator=True)
async def add_trigger(interaction: discord.Interaction, channel: discord.TextChannel, key: str, response: str):
    if channel.id not in trigger_words:
        trigger_words[channel.id] = {}
    trigger_words[channel.id][key] = response
    
    # 将新触发词保存到数据库
    conn = sqlite3.connect('trigger_words.db')
    c = conn.cursor()
    c.execute("INSERT INTO triggers (channel_id, key, response) VALUES (?, ?, ?)",
              (channel.id, key, response))
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"已添加触发词 '{key}' 及其回复 '{response}' 到频道 {channel.name}")

@bot.tree.command(name="remove_trigger")
@app_commands.checks.has_permissions(administrator=True)
async def remove_trigger(interaction: discord.Interaction, channel: discord.TextChannel, key: str):
    if channel.id in trigger_words and key in trigger_words[channel.id]:
        del trigger_words[channel.id][key]
        
        # 从数据库中删除触发词
        conn = sqlite3.connect('trigger_words.db')
        c = conn.cursor()
        c.execute("DELETE FROM triggers WHERE channel_id = ? AND key = ?", (channel.id, key))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"已从频道 {channel.name} 中删除触发词 '{key}'")
    else:
        await interaction.response.send_message(f"在频道 {channel.name} 中未找到触发词 '{key}'")

@bot.tree.command(name="list_triggers")
@app_commands.checks.has_permissions(administrator=True)
async def list_triggers(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in trigger_words and trigger_words[channel.id]:
        trigger_list = "\n".join([f"'{key}': '{response}'" for key, response in trigger_words[channel.id].items()])
        await interaction.response.send_message(f"频道 {channel.name} 的触发词列表：\n{trigger_list}")
    else:
        await interaction.response.send_message(f"频道 {channel.name} 中没有设置任何触发词")

@bot.event
async def on_ready():
    print(f"{bot.user} 已连接到 Discord!")
    try:
        synced = await bot.tree.sync()
        print(f"同步了 {len(synced)} 个命令")
    except Exception as e:
        print(f"同步命令时出错: {e}")

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
bot.run(TOKEN)
