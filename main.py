import discord
import os
import asyncio
import aiosqlite
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
APP_ID = os.getenv('DISCORD_APP_ID')

try:
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
except (TypeError, ValueError):
    LOG_CHANNEL_ID = None

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

DB_NAME = "bingo_data.db"

# --- DATABASE FUNCTIONS (ต้องอยู่ด้านบนสุด เพื่อให้ Class เรียกใช้ได้) ---

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # ตารางเก็บข้อมูลการส่ง
        await db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                user_id INTEGER,
                event_name TEXT,
                image_url TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, event_name)
            )
        """)
        # ตารางเก็บสถานะกิจกรรม (1=Open, 0=Closed)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_name TEXT PRIMARY KEY,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.commit()

async def is_event_active(event_name: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT is_active FROM events WHERE event_name = ?", (event_name,))
        result = await cursor.fetchone()
        if result is None:
            return True # Default Open
        return result[0] == 1

async def toggle_event_status(event_name: str, status: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO events (event_name, is_active) VALUES (?, ?)", (event_name, status))
        await db.commit()

async def check_submission(user_id: int, event_name: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM submissions WHERE user_id = ? AND event_name = ?", (user_id, event_name))
        result = await cursor.fetchone()
        return result is not None

# นี่คือฟังก์ชันที่ Error ก่อนหน้านี้ (ผมเอามาวางไว้ตรงนี้ให้แล้ว)
async def add_submission(user_id: int, event_name: str, image_url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO submissions (user_id, event_name, image_url) VALUES (?, ?, ?)", 
            (user_id, event_name, image_url)
        )
        await db.commit()

async def delete_submission(user_id: int, event_name: str) -> bool:
    """ลบข้อมูลการส่งของ User คนนั้นออก"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM submissions WHERE user_id = ? AND event_name = ?", (user_id, event_name))
        if await cursor.fetchone() is None:
            return False 
        await db.execute("DELETE FROM submissions WHERE user_id = ? AND event_name = ?", (user_id, event_name))
        await db.commit()
        return True

# --- BOT SETUP ---

class BingoBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=APP_ID
        )

    async def setup_hook(self):
        await init_db()
        self.add_view(SubmissionView()) 
        await self.tree.sync()
        print("✅ Slash commands synced & Database initialized!")

bot = BingoBot()

# --- VIEWS ---

class AdminDeleteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🗑️ Delete Channel", style=discord.ButtonStyle.danger)
    async def delete_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.channel.delete()

class UserReviewView(View):
    def __init__(self, user: discord.Member, event_name: str, target_channel_id: int, image_url: str):
        super().__init__(timeout=None)
        self.user = user
        self.event_name = event_name
        self.target_channel_id = target_channel_id
        self.image_url = image_url

    @discord.ui.button(label="✅ Confirm & Close Ticket", style=discord.ButtonStyle.primary)
    async def confirm_close(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ You cannot perform this action.", ephemeral=True)

        if not await is_event_active(self.event_name):
            return await interaction.response.send_message("🔴 **Event Closed!** Submissions are no longer accepted.", ephemeral=True)

        if await check_submission(self.user.id, self.event_name):
             return await interaction.response.send_message("⚠️ You have already submitted for this event!", ephemeral=True)

        button.disabled = True
        await interaction.response.edit_message(view=self)

        # บันทึกลง Database (เรียกใช้ฟังก์ชันที่ประกาศไว้ข้างบน)
        await add_submission(self.user.id, self.event_name, self.image_url)
        print(f"💾 Saved: {self.user.name} - {self.event_name}")

        # Send Log
        if LOG_CHANNEL_ID:
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="📝 New Submission Logged",
                    description=f"User has confirmed their submission.",
                    color=discord.Color.orange()
                )
                log_embed.add_field(name="👤 User", value=f"{self.user.mention} (`{self.user.id}`)", inline=True)
                log_embed.add_field(name="🎉 Event", value=f"**{self.event_name}**", inline=True)
                log_embed.add_field(name="🖼️ Image", value=f"[Click to View]({self.image_url})", inline=True)
                log_embed.set_thumbnail(url=self.image_url)
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)

        await interaction.channel.send(f"🔒 **Confirmed!** Closing ticket in **10 seconds**...")
        await asyncio.sleep(10)

        try:
            if interaction.guild.me.top_role > self.user.top_role:
                await interaction.channel.set_permissions(self.user, overwrite=None)
            else:
                await interaction.channel.send("⚠️ Note: Cannot auto-remove user due to role hierarchy.")
        except Exception as e:
            print(f"Error removing permissions: {e}")

        embed = discord.Embed(
            title="🔒 Ticket Locked",
            description=f"Ticket closed by {self.user.mention}.\n**Event:** {self.event_name}\nAdmin, please delete this channel when ready.",
            color=discord.Color.dark_grey()
        )
        await interaction.channel.send(embed=embed, view=AdminDeleteView())

class SubmissionView(View):
    def __init__(self, event_name: str = None, target_channel_id: int = None):
        super().__init__(timeout=None)
        
        if event_name and target_channel_id:
            custom_id = f"bingo_submit:{event_name}:{target_channel_id}"
            self.add_item(discord.ui.Button(
                label="📤 Submit Prediction", 
                style=discord.ButtonStyle.green, 
                custom_id=custom_id
            ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if "custom_id" in interaction.data and interaction.data["custom_id"].startswith("bingo_submit:"):
            await self.handle_submit(interaction)
            return False 
        return True

    async def handle_submit(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        
        try:
            custom_id = interaction.data["custom_id"]
            parts = custom_id.split(":")
            if len(parts) < 3:
                raise ValueError("Invalid custom_id format")
            target_channel_id = int(parts[-1])
            event_name = ":".join(parts[1:-1])
            
        except (ValueError, IndexError):
            await interaction.response.send_message("❌ Error parsing button data.", ephemeral=True)
            return

        if not await is_event_active(event_name):
            await interaction.response.send_message(f"🔴 **Event Closed**\nSubmissions for **{event_name}** are closed.", ephemeral=True)
            return

        if await check_submission(user.id, event_name):
            await interaction.response.send_message(f"🚫 You already submitted for **{event_name}**.", ephemeral=True)
            return

        target_channel = guild.get_channel(target_channel_id)
        if not target_channel:
             await interaction.response.send_message(f"❌ Destination channel not found.", ephemeral=True)
             return

        base_name = f"bingo-{user.name}"
        channel_name = "".join(c for c in base_name if c.isalnum() or c in "-_").lower()

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"⚠️ Finish your open ticket first: {existing_channel.mention}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if guild.me.top_role > user.top_role:
            overwrites[user] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, read_message_history=True 
            )
        
        try:
            temp_channel = await guild.create_text_channel(
                name=channel_name, 
                overwrites=overwrites, 
                category=interaction.channel.category,
                reason=f"Bingo Submission: {event_name}"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating channel: {e}", ephemeral=True)
            return
        
        await interaction.followup.send(f"✅ **Ticket Created!** {temp_channel.mention}", ephemeral=True)

        instruction_embed = discord.Embed(
            title=f"📸 Upload Prediction: {event_name}",
            description=f"Welcome {user.mention}!\nPlease upload your image here.",
            color=discord.Color.gold()
        )
        await temp_channel.send(embed=instruction_embed)

        def check(m):
            return m.channel.id == temp_channel.id and m.author.id == user.id and len(m.attachments) > 0

        try:
            message = await bot.wait_for('message', check=check, timeout=600.0)
            
            try:
                file = await message.attachments[0].to_file()
                
                admin_embed = discord.Embed(title=f"🎲 New Submission: {event_name}", color=discord.Color.blue())
                admin_embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
                admin_embed.set_image(url=f"attachment://{file.filename}")
                admin_embed.add_field(name="User ID", value=user.id, inline=True)
                admin_embed.timestamp = discord.utils.utcnow()

                sent_message = await target_channel.send(embed=admin_embed, file=file)
                final_image_url = sent_message.attachments[0].url if sent_message.attachments else ""

                feedback_embed = discord.Embed(
                    title="✅ Submission Received!",
                    description="Is this image correct? Press Confirm to finalize.",
                    color=discord.Color.green()
                )
                if final_image_url:
                    feedback_embed.set_image(url=final_image_url)
                
                await temp_channel.send(
                    content=user.mention, 
                    embed=feedback_embed, 
                    view=UserReviewView(user, event_name, target_channel_id, final_image_url)
                )

            except Exception as e:
                print(f"Error sending image: {e}")
                await temp_channel.send(f"❌ Error forwarding image: `{e}`")

        except asyncio.TimeoutError:
            try:
                await temp_channel.send("⏰ Timeout. Closing...")
                await asyncio.sleep(3)
                await temp_channel.delete()
            except:
                pass

# --- COMMANDS ---

@bot.tree.command(name="setup_bingo", description="Setup Bingo button (Limit: 1 per person)")
@app_commands.describe(event_name="Unique Event Name", target_channel="Destination Channel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_bingo(interaction: discord.Interaction, event_name: str, target_channel: discord.TextChannel):
    if ":" in event_name:
         await interaction.response.send_message("❌ Event Name cannot contain colons (:).", ephemeral=True)
         return
    
    await toggle_event_status(event_name, 1)

    embed = discord.Embed(
        title=f"🔮 Bingo Prediction: {event_name}",
        description="Click below to submit your prediction!\n*Limit: 1 Submission per person.*",
        color=discord.Color.gold()
    )
    view = SubmissionView(event_name=event_name, target_channel_id=target_channel.id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="reset_user", description="Allow a user to resubmit (Admin Only)")
@app_commands.describe(user="The user to reset", event_name="Event Name")
@app_commands.checks.has_permissions(administrator=True)
async def reset_user(interaction: discord.Interaction, user: discord.Member, event_name: str):
    await interaction.response.defer(ephemeral=True)
    if await delete_submission(user.id, event_name):
        await interaction.followup.send(f"✅ Reset successful for {user.mention} in event **{event_name}**.", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ User hasn't submitted anything for **{event_name}**.", ephemeral=True)

@bot.tree.command(name="toggle_event", description="Open or Close submissions")
@app_commands.describe(event_name="Name of the event", status="True = Open, False = Close")
@app_commands.checks.has_permissions(administrator=True)
async def toggle_event(interaction: discord.Interaction, event_name: str, status: bool):
    new_status = 1 if status else 0
    await toggle_event_status(event_name, new_status)
    status_str = "🟢 OPEN" if status else "🔴 CLOSED"
    await interaction.response.send_message(f"✅ Event **{event_name}** is now {status_str}.", ephemeral=True)

@bot.tree.command(name="export_db", description="Download database file")
@app_commands.checks.has_permissions(administrator=True)
async def export_db(interaction: discord.Interaction):
    if not os.path.exists(DB_NAME):
        return await interaction.response.send_message("❌ No DB found.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("📂 Database File:", file=discord.File(DB_NAME))

@bot.tree.command(name="reset_db", description="⚠ DANGER: Reset database")
@app_commands.checks.has_permissions(administrator=True)
async def reset_db(interaction: discord.Interaction):
    await interaction.response.send_message("⚠ **WARNING:** Delete ALL data? Type `/confirm_reset` to proceed.", ephemeral=True)

@bot.tree.command(name="confirm_reset", description="Confirm database reset")
@app_commands.checks.has_permissions(administrator=True)
async def confirm_reset(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        if os.path.exists(DB_NAME): os.remove(DB_NAME)
        await init_db()
        await interaction.followup.send("♻️ Database has been reset.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(TOKEN)