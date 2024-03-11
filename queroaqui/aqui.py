import discord
from discord.ext import commands, tasks
import re
from datetime import datetime, timedelta
import json
import os

# Defina o prefixo do bot
PREFIX = "/"

# Define os intents necessários para o bot
intents = discord.Intents.default()  # Ativa os intents padrão
intents.members = True  # Necessário para receber eventos de atualização de membros, como join e leave

# Inicializa o bot com os intents definidos
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Verifica se o diretório 'json' existe e o cria se não existir
if not os.path.exists("json"):
    os.makedirs("json")

# Carrega os dados de cooldown do arquivo JSON, se existir
try:
    with open("json/cooldowns.json", "r") as f:
        cooldowns = json.load(f)
except FileNotFoundError:
    cooldowns = {}

# Dicionário para mapear os níveis VIP aos IDs de cargos correspondentes
vip_roles = {
    "VIP1": {"id": 618187446974414848},  # Exemplo de VIP1 com ID de cargo
}

# ID do canal de log
log_channel_id = 796092687961948211  # Substitua pelo ID do seu canal de log

# Função para verificar e remover o cargo VIP de membros que ultrapassaram o cooldown
@tasks.loop(minutes=1)
async def check_vip_cooldown():
    try:
        guild = bot.get_guild(618174343217938442)  # Substitua pelo ID do seu servidor
        log_channel = guild.get_channel(log_channel_id)  # Obtém o canal de log
        for member_id, roles in list(cooldowns.items()):
            member = guild.get_member(int(member_id))
            if member:
                for role_id, cooldown_end_time in roles.items():
                    role = guild.get_role(int(role_id))
                    if role in member.roles:
                        if datetime.now() > datetime.fromisoformat(cooldown_end_time):
                            await member.remove_roles(role)
                            del cooldowns[member_id][role_id]
                            await log_channel.send(
                                f'{member.mention} teve o cargo {role.name} removido após o período de cooldown.')
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    # Inicia a verificação de cooldowns
    check_vip_cooldown.start()

    # Verifica se o usuário especificado já possui o cargo VIP e, caso contrário, atribui-o
    guild = bot.get_guild(618174343217938442)  # Substitua pelo ID do seu servidor
    log_channel = guild.get_channel(log_channel_id)  # Obtém o canal de log
    member = guild.get_member(378549050779107329)  # Substitua pelo ID do usuário
    if member:
        vip_level = "VIP1"
        role_id = vip_roles[vip_level]["id"]
        role = guild.get_role(role_id)
        if role and role not in member.roles:
            await member.add_roles(role)
            cooldown_minutes = 1  # Defina o tempo de cooldown em minutos
            if str(member.id) not in cooldowns:
                cooldowns[str(member.id)] = {}
            cooldown_end_time = (datetime.now() + timedelta(minutes=cooldown_minutes)).isoformat()
            cooldowns[str(member.id)][str(role_id)] = cooldown_end_time
            await log_channel.send(
                f'{member.mention} recebeu o cargo {role.name} com cooldown de {cooldown_minutes} minutos.')
    else:
        print("O usuário especificado não foi encontrado neste servidor.")

@bot.command()
async def darvip(ctx, member: discord.Member, vip_level: str, cooldown_time: str):
    try:
        if ctx.author.guild_permissions.administrator:
            if vip_level.upper() in vip_roles:
                guild = ctx.guild
                role_id = vip_roles[vip_level.upper()]["id"]
                role = guild.get_role(role_id)
                log_channel = guild.get_channel(log_channel_id)
                if role:
                    cooldown_match = re.match(r"(\d+)([DdMm])", cooldown_time.upper())
                    if cooldown_match:
                        cooldown_value = int(cooldown_match.group(1))
                        cooldown_unit = cooldown_match.group(2).upper()
                        if cooldown_unit == "D":
                            cooldown_days = cooldown_value
                            cooldown_end_date = datetime.now() + timedelta(days=cooldown_days)
                        elif cooldown_unit == "M":
                            cooldown_days = cooldown_value / (24 * 60)  # Convertendo minutos para dias para cálculo
                            cooldown_end_date = datetime.now() + timedelta(days=cooldown_days)
                        else:
                            await ctx.send("Unidade de cooldown inválida. Use 'D' para dias ou 'M' para minutos.")
                            return
                        
                        await member.add_roles(role)
                        formatted_current_date = datetime.now().strftime('%d/%m/%Y')
                        formatted_cooldown_end_date = cooldown_end_date.strftime('%d/%m/%Y')
                        
                        # Construindo a mensagem de log
                        log_message = (f'{member.name} (ID: {member.id}) recebeu o cargo {role.name} (ID: {role_id}) '
                                       f'com cooldown de {cooldown_days} dias. Data de início: {formatted_current_date}, '
                                       f'Data de expiração: {formatted_cooldown_end_date}.')
                        
                        await ctx.send(f'{member.mention} recebeu o cargo <@&{role_id}>.')
                        await log_channel.send(log_message)
                        
                        # Salva os dados de cooldown no arquivo JSON
                        save_data_to_json("json/cooldowns.json", cooldowns, log_message)
                    else:
                        await ctx.send("Formato de cooldown inválido. Use o formato 'Xm' ou 'Xd', onde X é o número de minutos ou dias.")
                else:
                    await ctx.send("O cargo especificado não existe neste servidor.")
            else:
                await ctx.send("Nível VIP inválido.")
        else:
            await ctx.send("Você não tem permissão para executar este comando.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


def save_data_to_json(file_path, data, log_message=None):
    # Se houver um log_message, extraia as informações
    if log_message:
        match = re.match(
            r'(.+) \(ID: (\d+)\) recebeu o cargo (.+) \(ID: (\d+)\) com cooldown de (\d+) dias\. Data de início: (\d+/\d+/\d+), Data de expiração: (\d+/\d+/\d+)', log_message)
        
        if match:
            # Extrair informações correspondentes aos grupos da expressão regular
            name, user_id, cargo, cargo_id, tempo, data_inicio, data_fim = match.groups()

            # Formatar os dados como um dicionário
            log_entry = {
                "nome": name,
                "id_usuario": user_id,
                "cargo": cargo,
                "id_cargo": cargo_id,
                "tempo": tempo,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            }

            # Verificar se o arquivo já contém registros
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                # Adicionar uma vírgula ao final do arquivo antes de adicionar o novo registro
                with open(file_path, "rb+") as f:
                    f.seek(-1, os.SEEK_END)
                    f.truncate()
                    f.write(b',')

            # Salvar o registro no arquivo JSON
            with open(file_path, "a") as f:
                json.dump(log_entry, f, indent=4)
                f.write("\n")
        else:
            print("Log message não corresponde ao padrão esperado.")
    else:
        # Salvar os dados de cooldown no arquivo JSON
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

# Salva os dados de cooldown no arquivo JSON
@bot.event
async def on_shutdown():
    for log_message in log_messages:
        save_data_to_json("json/log_messages.json", cooldowns, log_message)
    save_data_to_json("json/cooldowns.json", cooldowns)

# Substitua "SEU_TOKEN" pelo seu token de bot do Discord
bot.run("TOKEN")
