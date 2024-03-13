import discord
from discord.ext import commands, tasks
import re
from datetime import datetime, timedelta
import json
import os
from tabulate import tabulate

PREFIX = "/"
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


if not os.path.exists("json"):
    os.makedirs("json")

try:
    with open("json/cooldowns.json", "r") as f:
        cooldowns = json.load(f)
except FileNotFoundError:
    cooldowns = {}

vip_roles = {
    "VIP1": {"id": 618187446974414848},
    "VIP2": {"id": 618187446974414849},
    "VIP3": {"id": 618187446974414850},
    "VIP4": {"id": 618187446974414851},
    "VIP5": {"id": 618187446974414852}
}
log_channel_id = 796092687961948211

@tasks.loop(minutes=1)
async def check_vip_cooldown():
    if bot.is_ready():  
        guild = bot.get_guild(618174343217938442)
        log_channel = guild.get_channel(log_channel_id)
        current_time = datetime.now()
        for member_id, user_data in cooldowns.items():
            member = await guild.fetch_member(int(member_id))  # Use await aqui
            if member:
                for role_id, role_data in user_data.items():
                    if role_id in vip_roles:
                        role = guild.get_role(vip_roles[role_id]["id"])
                        if role and role in member.roles:
                            final_date_str = role_data["finalDate"]
                            # Attempt to parse the date in different formats
                            for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
                                try:
                                    final_date = datetime.strptime(final_date_str, date_format)
                                    if current_time > final_date:
                                        await member.remove_roles(role)
                                        del cooldowns[member_id][role_id]
                                        await log_channel.send(f'{member.mention} teve o cargo {role.name} removido após o período de cooldown.')
                                        save_data_to_json("json/cooldowns.json", cooldowns)
                                    break  # Stop iterating if date is successfully parsed
                                except ValueError:
                                    continue  # Try next format if ValueError occurs

@bot.event
async def on_ready():
    check_vip_cooldown.start()  

@bot.command()
async def darvip(ctx, member: discord.Member, vip_level: str, duracao: str, amount: float, currency: str):
    try:
        # Verificar se o autor do comando tem permissões de administrador, é o proprietário do bot ou é o usuário mencionado
        if ctx.author.guild_permissions.administrator and vip_level.upper() in vip_roles:
            guild = ctx.guild
            role_id = vip_roles[vip_level.upper()]["id"]
            role = guild.get_role(role_id)
            log_channel = guild.get_channel(log_channel_id)
            if role:
                # Convertendo a duração para minutos
                duracao_numerica = int(re.match(r"(\d+)([DdMm])", duracao).group(1))
                duracao_unidade = re.match(r"(\d+)([DdMm])", duracao).group(2).upper()
                if duracao_unidade == "D":
                    duracao_minutos = duracao_numerica * 24 * 60
                elif duracao_unidade == "M":
                    duracao_minutos = duracao_numerica
                else:
                    await ctx.send("Unidade de duração inválida. Use 'D' para dias ou 'M' para minutos.")
                    return
                # Calcular data final
                final_date = (datetime.now() + timedelta(minutes=duracao_minutos)).strftime('%d/%m/%Y')  # Corrigindo o formato da data
                # Criar entrada no JSON
                user_data = {
                    "usuario": member.name,
                    "dataCompra": datetime.now().strftime('%d/%m/%Y'),
                    "finalDate": final_date,  # Ajuste do formato da data
                    "VIP": vip_level.upper(),
                    "duracao": duracao_numerica,
                    "amount": amount,
                    "currency": currency
                }
                # Adicionar cargo ao usuário
                await member.add_roles(role)
                # Atualizar JSON
                if str(member.id) not in cooldowns:
                    cooldowns[str(member.id)] = {}
                cooldowns[str(member.id)][vip_level.upper()] = user_data

                # Convert finalDate to ISO 8601 format before saving
                final_date_iso = datetime.strptime(final_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                cooldowns[str(member.id)][vip_level.upper()]['finalDate'] = final_date_iso

                save_data_to_json("json/cooldowns.json", cooldowns)
                await ctx.send(f'{member.mention} recebeu o cargo {role.name}.')
                await log_channel.send(f'{member.name} recebeu o cargo {role.name}.')
            else:
                await ctx.send("O cargo especificado não existe neste servidor.")
        else:
            await ctx.send("Nível VIP inválido ou você não tem permissão para executar este comando.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


def save_data_to_json(file_path, data):
    try:
        with open(file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
            print("Dados salvos em JSON com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar dados em JSON: {e}")

# Comando "/removervip"
@bot.command()
async def removervip(ctx, member: discord.Member, vip_level: str):
    try:
        if ctx.author.guild_permissions.administrator and vip_level.upper() in vip_roles:
            guild = ctx.guild
            role_id = vip_roles[vip_level.upper()]["id"]
            role = guild.get_role(role_id)
            log_channel = guild.get_channel(log_channel_id)
            if role:
                if role in member.roles:
                    # Remover cargo do usuário
                    await member.remove_roles(role)
                    # Remover entrada do VIP do JSON
                    del cooldowns[str(member.id)][vip_level.upper()]
                    save_data_to_json("json/cooldowns.json", cooldowns)
                    await ctx.send(f'{member.mention} teve o cargo {role.name} removido.')
                else:
                    await ctx.send(f'{member.mention} não possui o cargo {role.name}.')
            else:
                await ctx.send("O cargo especificado não existe neste servidor.")
        else:
            await ctx.send("Nível VIP inválido ou você não tem permissão para executar este comando.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


# Comando "/changevip"
@bot.command()
async def changevip(ctx, member: discord.Member, new_vip_level: str, duracao: str, amount: float, currency: str):
    try:
        if ctx.author.guild_permissions.administrator and new_vip_level.upper() in vip_roles:
            guild = ctx.guild
            role_id = vip_roles[new_vip_level.upper()]["id"]
            role = guild.get_role(role_id)
            log_channel = guild.get_channel(log_channel_id)
            if role:
                if role in member.roles:
                    # Atualizar dados do usuário no JSON
                    duracao_numerica = int(re.match(r"(\d+)([DdMm])", duracao).group(1))
                    duracao_unidade = re.match(r"(\d+)([DdMm])", duracao).group(2).upper()
                    if duracao_unidade == "D":
                        duracao_minutos = duracao_numerica * 24 * 60
                    elif duracao_unidade == "M":
                        duracao_minutos = duracao_numerica
                    else:
                        await ctx.send("Unidade de duração inválida. Use 'D' para dias ou 'M' para minutos.")
                        return
                    final_date = datetime.now() + timedelta(minutes=duracao_minutos)
                    cooldowns[str(member.id)][new_vip_level.upper()] = {
                        "dataCompra": datetime.now().isoformat(),
                        "finalDate": final_date.isoformat(),
                        "VIP": new_vip_level.upper(),
                        "duracao": duracao_numerica,
                        "amount": amount,
                        "currency": currency
                    }
                    save_data_to_json("json/cooldowns.json", cooldowns)
                    await ctx.send(f'{member.mention} teve seu VIP alterado para {new_vip_level.upper()}.')
                else:
                    await ctx.send(f'{member.mention} não possui o cargo {role.name}.')
            else:
                await ctx.send("O cargo especificado não existe neste servidor.")
        else:
            await ctx.send("Nível VIP inválido ou você não tem permissão para executar este comando.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# Comando "/status"
@bot.command()
async def status(ctx):
    try:
        embed = discord.Embed(title="Status dos Usuários", color=discord.Color.blue())
        for user_id, user_data in cooldowns.items():
            member = ctx.guild.get_member(int(user_id))
            user_mention = member.mention if member else f"Usuário não encontrado ({user_id})"
            roles_info = ""
            for vip_level, vip_data in user_data.items():
                roles_info += f"**VIP**: {vip_data['VIP']}, **Duração**: {vip_data['duracao']} dias\n"
            embed.add_field(name=f"Usuário: {user_mention}", value=roles_info, inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# Substitua "SEU_TOKEN" pelo seu token de bot do Discord
bot.run("MTIxNjYwMjY2NDkyNjcwNzc0Mw.G31UGq.N1tCMe8RtP9g1Zn9w7W5rzUuklHPJh9Y7I-5C0")
