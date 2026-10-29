import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

# --- إعدادات البوت الأساسية ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

DATA_FILE = "users_id_data.json"
CONFIG_FILE = "server_config.json"
YELLOW_COLOR = discord.Color.from_rgb(255, 215, 0) # لون أصفر ذهبي

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "LOG_CHANNEL_ID": None, 
        "MDT_LOG_CHANNEL_ID": None, 
        "ID_ROLE_ID": None, 
        "POLICE_ROLE_ID": None,
        "ID_TEXT": "اختر الإجراء المطلوب للهوية...",
        "MDT_TEXT": "نظام إدارة القضايا والتحري الجنائي الـ MDT..."
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_unique_national_id(data):
    rare_numbers = {1000, 1001, 1111, 2222, 3333, 4444, 5000}
    used_ids = {user_info["national_id"] for user_info in data.values()}
    while True:
        num = random.randint(1000, 5000)
        formatted_id = f"#{num}"
        if num not in rare_numbers and formatted_id not in used_ids:
            return formatted_id

# --- استمارات التعبئة (Modals) بنصوصك المحددة الحصرية ---

class IDCreateModal(discord.ui.Modal, title="استمارة تسجيل الهوية الوطنية"):
    full_name = discord.ui.TextInput(label="اسم", required=True)
    age = discord.ui.TextInput(label="العمر", required=True)
    birth_place = discord.ui.TextInput(label="موقع الميلاد", required=True)
    character_user = discord.ui.TextInput(label="اليوزر", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        config = load_config()
        user_id = str(interaction.user.id)
        national_id = generate_unique_national_id(data)
        
        data[user_id] = {
            "name": self.full_name.value,
            "age": self.age.value,
            "birth_place": self.birth_place.value,
            "username": self.character_user.value,
            "national_id": national_id,
            "cases": []
        }
        save_data(data)
        
        if config["ID_ROLE_ID"]:
            guild = interaction.guild
            id_role = guild.get_role(int(config["ID_ROLE_ID"]))
            if id_role:
                try:
                    await interaction.user.add_roles(id_role)
                except discord.Forbidden:
                    pass

        embed = discord.Embed(title="💳 بطاقة الهوية الوطنية", color=YELLOW_COLOR)
        embed.add_field(name="اسم", value=self.full_name.value, inline=False)
        embed.add_field(name="العمر", value=self.age.value, inline=False)
        embed.add_field(name="موقع الميلاد", value=self.birth_place.value, inline=False)
        embed.add_field(name="الرقم الوطني", value=national_id, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.client.user.display_avatar.url)
        
        await interaction.response.send_message(content="🎉 تم انشاء هوية بنجاح", embed=embed, ephemeral=True)
        
        if config["LOG_CHANNEL_ID"]:
            log_channel = interaction.guild.get_channel(int(config["LOG_CHANNEL_ID"]))
            if log_channel:
                await log_channel.send(content=f"تم انشاء هوية بواسطة ({interaction.user.name})", embed=embed)

class MDTSearchModal(discord.ui.Modal, title="نظام البحث بالرقم الوطني"):
    national_id_input = discord.ui.TextInput(label="الرقم الوطني للمواطن", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        config = load_config()
        query = self.national_id_input.value.strip()
        found_user = None
        found_uid = None

        for uid, user_info in data.items():
            if user_info["national_id"] == query:
                found_user = user_info
                found_uid = uid
                break

        if config["MDT_LOG_CHANNEL_ID"]:
            log_channel = interaction.guild.get_channel(int(config["MDT_LOG_CHANNEL_ID"]))
            if log_channel:
                log_embed = discord.Embed(title="🔍 سجلات القضايا", color=YELLOW_COLOR)
                log_embed.add_field(name="العسكري المسؤول عن البحث", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="الرقم الوطني للمواطن", value=query, inline=True)
                
                if found_user:
                    log_embed.add_field(name="حالة وجود الرقم في النظام", value="✅ موجود في النظام الجنائي والمدني", inline=False)
                    log_embed.add_field(name="اسم الشخصية المسجلة", value=found_user["name"], inline=True)
                    log_embed.add_field(name="الرقم الوطني المؤكد", value=found_user["national_id"], inline=True)
                else:
                    log_embed.add_field(name="حالة وجود الرقم في النظام", value="لا يوجد مواطن لديه الرقم الوطني ❌", inline=False)
                
                await log_channel.send(embed=log_embed)

        if not found_user:
            await interaction.response.send_message("لا يوجد مواطن لديه الرقم الوطني ❌", ephemeral=True)
            return

        embed = discord.Embed(title="🚨 بيانات المواطن", color=YELLOW_COLOR)
        embed.add_field(name="اسم", value=found_user["name"], inline=True)
        embed.add_field(name="العمر", value=found_user["age"], inline=True)
        embed.add_field(name="الرقم الوطني", value=found_user["national_id"], inline=False)
        
        cases = found_user.get("cases", [])
        if not cases:
            embed.add_field(name="السجل الجنائي", value="لا يوجد قضايا", inline=False)
        else:
            for idx, case in enumerate(cases, start=1):
                embed.add_field(
                    name=f"قضية رقم #{idx}",
                    value=f"**تفاصيل القضية:** {case['infraction']}\n**مدة السجن:** {case['jail_time']}\n**مبلغ المخالفة:** {case['penalty_fine']}\n**اسم العسكري:** {case['officer']}",
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)
class MDTAddCaseModal(discord.ui.Modal, title="تسجيل قضية جنائية جديدة"):
    national_id = discord.ui.TextInput(label="الرقم الوطني للمواطن", required=True)
    infraction = discord.ui.TextInput(label="تفاصيل القضية", required=True)
    jail_time = discord.ui.TextInput(label="مدة السجن", required=True)
    penalty_fine = discord.ui.TextInput(label="مبلغ المخالفة", required=True)
    officer_name = discord.ui.TextInput(label="اسم العسكري المسؤول عن القضية", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        config = load_config()
        nid = self.national_id.value.strip()
        target_uid = None

        for uid, user_info in data.items():
            if user_info["national_id"] == nid:
                target_uid = uid
                break

        if not target_uid:
            await interaction.response.send_message("لا يوجد مواطن لديه الرقم الوطني ❌", ephemeral=True)
            return

        case_entry = {
            "infraction": self.infraction.value,
            "jail_time": self.jail_time.value,
            "penalty_fine": self.penalty_fine.value,
            "officer": self.officer_name.value
        }
        
        data[target_uid]["cases"].append(case_entry)
        save_data(data)

        embed = discord.Embed(title="⚖️ تم تسجيل القضية بنجاح", color=YELLOW_COLOR)
        embed.add_field(name="الرقم الوطني للمواطن", value=nid, inline=True)
        embed.add_field(name="تفاصيل القضية", value=self.infraction.value, inline=False)
        embed.add_field(name="مدة السجن", value=self.jail_time.value, inline=True)
        embed.add_field(name="الغرامة المادية", value=self.penalty_fine.value, inline=True)
        embed.add_field(name="اسم العسكري:", value=self.officer_name.value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        if config["MDT_LOG_CHANNEL_ID"]:
            log_channel = interaction.guild.get_channel(int(config["MDT_LOG_CHANNEL_ID"]))
            if log_channel:
                await log_channel.send(content="⚖️ **قضية جنائية جديدة سجلت في النظام الجنائي:**", embed=embed)

# --- القوائم المنسدلة (Views) ---

class IDSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="اختر الإجراء المطلوب للهوية...",
        options=[
            discord.SelectOption(label="عرض الهوية الوطنية", emoji="🔍"),
            discord.SelectOption(label="إنشاء هوية جديدة", emoji="📝")
        ],
        custom_id="id_system_dropdown_menu"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = load_data()
        user_id = str(interaction.user.id)
        choice = select.values

        if choice == "عرض الهوية الوطنية":
            if user_id not in data:
                await interaction.response.send_message("❌ يرجي انشاء هويه اولا", ephemeral=True)
                return
            
            user_data = data[user_id]
            embed = discord.Embed(title="💳 بطاقة الهوية الوطنية", color=YELLOW_COLOR)
            embed.add_field(name="اسم", value=user_data["name"], inline=False)
            embed.add_field(name="العمر", value=user_data["age"], inline=False)
            embed.add_field(name="موقع الميلاد", value=user_data["birth_place"], inline=False)
            embed.add_field(name="الرقم الوطني", value=user_data["national_id"], inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url if interaction.user.display_avatar else interaction.client.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif choice == "إنشاء هوية جديدة":
            if user_id in data:
                await interaction.response.send_message("❌ لديك هوية بالفعل", ephemeral=True)
                return
            await interaction.response.send_modal(IDCreateModal())

class MDTView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="نظام إدارة القضايا والتحري الجنائي الـ MDT...",
        options=[
            discord.SelectOption(label="البحث عن ملف مواطن", emoji="🔍"),
            discord.SelectOption(label="إنشاء قضية جنائية", emoji="📝")
        ],
        custom_id="police_mdt_dropdown_menu"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        config = load_config()
        if not config["POLICE_ROLE_ID"]:
            await interaction.response.send_message("❌ خطأ إداري: لم يتم ربط وتحديد رتبة جهاز الشرطة حتى الآن.", ephemeral=True)
            return

        police_role = interaction.guild.get_role(int(config["POLICE_ROLE_ID"]))
        if not police_role or police_role not in interaction.user.roles:
            await interaction.response.send_message("انت ليس عسكري ❌", ephemeral=True)
            return
        
        choice = select.values
        if choice == "البحث عن ملف مواطن":
            await interaction.response.send_modal(MDTSearchModal())
        elif choice == "إنشاء قضية جنائية":
            await interaction.response.send_modal(MDTAddCaseModal())

class IDBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        
    async def setup_hook(self):
        self.add_view(IDSelectView())
        self.add_view(MDTView())
        await self.tree.sync()
        print("تمت مزامنة أوامر السلاش بنجاح.")

bot = IDBot()

# --- أوامر السلاش الخاصة بالإدارة ---

@bot.tree.command(name="setup_config", description="إعداد وربط الرتب ورومات اللوج ونصوص لوحات البوت كاملة.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_config(interaction: discord.Interaction, رتبة_الشرطة: discord.Role, رتبة_المواطن: discord.Role, لوق_الهويات: discord.TextChannel, لوق_الام_دي_تي: discord.TextChannel, نص_لوحة_الهوية: str, نص_لوحة_الام_دي_تي: str):
    config = {
        "LOG_CHANNEL_ID": لوق_الهويات.id,
        "MDT_LOG_CHANNEL_ID": لوق_الام_دي_تي.id,
        "ID_ROLE_ID": رتبة_المواطن.id,
        "POLICE_ROLE_ID": رتبة_الشرطة.id,
        "ID_TEXT": نص_لوحة_الهوية,
        "MDT_TEXT": نص_لوحة_الام_دي_تي
    }
    save_config(config)
    await interaction.response.send_message("✅ تم حفظ البنية التحتية وتحديد الرتب وقنوات اللوج وتخصيص النصوص بنجاح.", ephemeral=True)

@bot.tree.command(name="setup_id", description="نشر لوحة استخراج وعرض الهويات الوطنية للمواطنين.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_id(interaction: discord.Interaction):
    config = load_config()
    embed = discord.Embed(title="💳 نظام الهوية الوطنية", description=config.get("ID_TEXT"), color=YELLOW_COLOR)
    await interaction.channel.send(embed=embed, view=IDSelectView())
    await interaction.response.send_message("✅ تم نشر لوحة نظام الهويات الوطنية بنجاح.", ephemeral=True)

@bot.tree.command(name="setup_mdt", description="نشر لوحة كمبيوتر الأمن العام والتحري الجنائي الخاص بالعساكر.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_mdt(interaction: discord.Interaction):
    config = load_config()
    embed = discord.Embed(title="🚔 نظام الأمن العام | كمبيوتر الشرطة الـ MDT", description=config.get("MDT_TEXT"), color=YELLOW_COLOR)
    await interaction.channel.send(embed=embed, view=MDTView())
    await interaction.response.send_message("✅ تم تفعيل كمبيوتر الشرطة بنجاح.", ephemeral=True)

@bot.tree.command(name="remove_case", description="حذف قضية معينة ومحددة برقمها من ملف المواطن الجنائي.")
@app_commands.checks.has_permissions(administrator=True)
async def remove_case(interaction: discord.Interaction, الرقم_الوطني: str, رقم_القضية: int):
    data = load_data()
    config = load_config()
    target_uid = None
    
    for uid, user_info in data.items():
        if user_info["national_id"] == الرقم_الوطني.strip():
            target_uid = uid
            break
            
    if not target_uid:
        await interaction.response.send_message("لا يوجد مواطن لديه الرقم الوطني ❌", ephemeral=True)
        return
        
    cases = data[target_uid].get("cases", [])
    if رقم_القضية < 1 or رقم_القضية > len(cases):
        await interaction.response.send_message("لا توجد قضية بهذا الرقم ❌", ephemeral=True)
        return
        
    removed_case = cases.pop(رقم_القضية - 1)
    save_data(data)
    
    await interaction.response.send_message("✅ تم حذف القضية بنجاح.", ephemeral=True)
    if config["MDT_LOG_CHANNEL_ID"]:
        log_channel = interaction.guild.get_channel(int(config["MDT_LOG_CHANNEL_ID"]))
        if log_channel:
            await log_channel.send(content=f"🚨 الإدارة قامت بحذف القضية رقم #{رقم_القضية} (`{removed_case['infraction']}`) عن صاحب الرقم الوطني `{الرقم_الوطني}`")

@bot.tree.command(name="clear_all_cases", description="تصفير السجل الجنائي لمواطن بالكامل وحذف كافة قضاياه.")
@app_commands.checks.has_permissions(administrator=True)
async def clear_all_cases(interaction: discord.Interaction, الرقم_الوطني: str):
    data = load_data()
    config = load_config()
    target_uid = None
    
    for uid, user_info in data.items():
        if user_info["national_id"] == الرقم_الوطني.strip():
            target_uid = uid
            break
            
    if not target_uid:
        await interaction.response.send_message("لا يوجد مواطن لديه الرقم الوطني ❌", ephemeral=True)
        return
        
    data[target_uid]["cases"] = []
    save_data(data)
    await interaction.response.send_message("✅ تم تصفير وإعادة تعيين السجل الجنائي للمواطن بنجاح.", ephemeral=True)
    
    if config["MDT_LOG_CHANNEL_ID"]:
        log_channel = interaction.guild.get_channel(int(config["MDT_LOG_CHANNEL_ID"]))
        if log_channel:
            await log_channel.send(content=f"🚨 تم تصفير السجل الجنائي بالكامل لصاحب الرقم الوطني `{الرقم_الوطني}` بواسطة الإدارة.")

bot.run("MTU2NDg0MTk5MzIyMDI1OTkwMA.GlNsDB._AMWhn08YP46qtCLqrUYZQUI2oEHxPjvtc-pXA")
