import asyncio
import aiohttp
import json
import sys
import os
import time
import base64
from datetime import datetime
from colorama import init, Fore, Back, Style, just_fix_windows_console
import shutil
import math

just_fix_windows_console()
init(autoreset=True)

class ConsoleColors:
    HEADER = Fore.MAGENTA
    OKBLUE = Fore.CYAN
    OKGREEN = Fore.GREEN
    WARNING = Fore.YELLOW
    FAIL = Fore.RED
    ENDC = Fore.RESET
    BOLD = Style.BRIGHT
    DIM = Style.DIM
    WHITE = Fore.WHITE
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE

class ProgressBar:
    @staticmethod
    def create_bar(percentage, width=50, fill_char='█', empty_char='░', color=ConsoleColors.CYAN):
        filled = int(width * percentage / 100)
        bar = f"{color}{fill_char * filled}{ConsoleColors.DIM}{empty_char * (width - filled)}{ConsoleColors.ENDC}"
        return bar
    
    @staticmethod
    def progress(iterable, desc="Processing", total=None, color=ConsoleColors.CYAN):
        if total is None:
            total = len(iterable)
        
        start_time = time.time()
        last_update = 0
        
        for idx, item in enumerate(iterable, 1):
            yield item
            
            if idx % max(1, total // 50) == 0 or idx == total:
                percentage = (idx / total) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / idx) * (total - idx) if idx > 0 else 0
                
                bar = ProgressBar.create_bar(percentage, color=color)
                status = f"{color}{desc}{ConsoleColors.ENDC} "
                progress_text = f"[{bar}] {percentage:>6.1f}%"
                eta_text = f"ETA: {ProgressBar._format_time(eta)}" if eta > 0 else ""
                
                sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns)
                sys.stdout.write(f'\r{status}{progress_text} {eta_text}')
                sys.stdout.flush()
                
                last_update = idx
        
        print()

    @staticmethod
    def _format_time(seconds):
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

class Spinner:
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, message, color=ConsoleColors.CYAN):
        self.message = message
        self.color = color
        self.running = False
        self.task = None
    
    async def start(self):
        self.running = True
        idx = 0
        while self.running:
            frame = Spinner.FRAMES[idx % len(Spinner.FRAMES)]
            sys.stdout.write(f'\r{self.color}{frame} {self.message}{ConsoleColors.ENDC}')
            sys.stdout.flush()
            idx += 1
            await asyncio.sleep(0.1)
        sys.stdout.write('\r' + ' ' * shutil.get_terminal_size().columns + '\r')
    
    def stop(self):
        self.running = False

class Table:
    @staticmethod
    def create_table(headers, rows, border_style=ConsoleColors.CYAN, header_style=ConsoleColors.BOLD + Fore.MAGENTA):
        if not rows:
            return "No data to display"
        
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(cell)))
        
        separator = f"{border_style}{'─' * (sum(col_widths) + len(col_widths) * 3 + 1)}{ConsoleColors.ENDC}"
        
        output = [separator]
        
        header_line = f"{border_style}│{ConsoleColors.ENDC} "
        for idx, header in enumerate(headers):
            header_line += f"{header_style}{str(header).center(col_widths[idx])}{ConsoleColors.ENDC} {border_style}│{ConsoleColors.ENDC} "
        output.append(header_line[:-1])
        output.append(separator)
        
        for row in rows:
            line = f"{border_style}│{ConsoleColors.ENDC} "
            for idx, cell in enumerate(row):
                line += f"{str(cell).ljust(col_widths[idx])} {border_style}│{ConsoleColors.ENDC} "
            output.append(line[:-1])
        
        output.append(separator)
        return '\n'.join(output)

class Panel:
    @staticmethod
    def create(content, title=None, border_style=ConsoleColors.CYAN):
        content_lines = str(content).split('\n')
        width = max(len(line) for line in content_lines) + 4
        border = border_style + '─' * width + ConsoleColors.ENDC
        
        output = [border]
        if title:
            title_line = f"{border_style}│{ConsoleColors.ENDC} {ConsoleColors.BOLD}{title}{ConsoleColors.ENDC} "
            output.append(title_line.ljust(width + 3) + f"{border_style}│{ConsoleColors.ENDC}")
            output.append(border)
        
        for line in content_lines:
            output.append(f"{border_style}│{ConsoleColors.ENDC} {line.ljust(width - 2)} {border_style}│{ConsoleColors.ENDC}")
        
        output.append(border)
        return '\n'.join(output)

class DiscordAPIClient:
    BASE_URL = "https://discord.com/api/v10"
    
    def __init__(self, max_workers=10, retry_attempts=5):
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.semaphore = asyncio.Semaphore(max_workers)
        self.session = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=60, connect=30)
        connector = aiohttp.TCPConnector(limit=max(self.max_workers * 2, 20))
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    def _get_headers(self, token, token_type="bot"):
        headers = {
            "Content-Type": "application/json",
            "X-RateLimit-Precision": "millisecond",
            "User-Agent": "Mozilla/5.0 (compatible; DiscordClone/2.0)"
        }
        if token_type.lower() == "bot":
            headers["Authorization"] = f"Bot {token}"
        else:
            headers["Authorization"] = token
        return headers
    
    async def _request_with_retry(self, method, path, token, token_type="bot", payload=None, retries=None):
        url = f"{self.BASE_URL}{path}"
        retries = retries or self.retry_attempts
        headers = self._get_headers(token, token_type)
        
        for attempt in range(retries):
            async with self.semaphore:
                async with self.session.request(method, url, json=payload, headers=headers) as response:
                    if response.status == 429:
                        response_data = await response.json()
                        retry_after = response_data.get("retry_after", 1.5)
                        print(f"{ConsoleColors.WARNING}Rate limited. Waiting {retry_after:.2f}s{ConsoleColors.ENDC}")
                        await asyncio.sleep(retry_after + 0.1)
                        continue
                        
                    if response.status in (200, 201):
                        return await response.json(), None
                        
                    if response.status == 204:
                        return {}, None
                        
                    if response.status >= 500:
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                    error_data = await response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status}")
                    error_code = error_data.get("code", "")
                    if error_code:
                        return None, f"{error_msg} (Code: {error_code})"
                    return None, error_msg
                    
        return None, "Max retries exceeded"
    
    async def get_bot_user(self, token):
        return await self._request_with_retry("GET", "/users/@me", token, "bot")
    
    async def get_user(self, token):
        return await self._request_with_retry("GET", "/users/@me", token, "user")
    
    async def get_guild(self, guild_id, token, token_type="user"):
        return await self._request_with_retry("GET", f"/guilds/{guild_id}?with_counts=true", token, token_type)
    
    async def get_guild_channels(self, guild_id, token, token_type="user"):
        return await self._request_with_retry("GET", f"/guilds/{guild_id}/channels", token, token_type)
    
    async def get_guild_roles(self, guild_id, token, token_type="user"):
        return await self._request_with_retry("GET", f"/guilds/{guild_id}/roles", token, token_type)
    
    async def create_channel(self, guild_id, payload, token):
        return await self._request_with_retry("POST", f"/guilds/{guild_id}/channels", token, "bot", payload)
    
    async def create_role(self, guild_id, payload, token):
        return await self._request_with_retry("POST", f"/guilds/{guild_id}/roles", token, "bot", payload)
    
    async def delete_channel(self, channel_id, token):
        _, error = await self._request_with_retry("DELETE", f"/channels/{channel_id}", token, "bot")
        return error is None
    
    async def delete_role(self, guild_id, role_id, token):
        _, error = await self._request_with_retry("DELETE", f"/guilds/{guild_id}/roles/{role_id}", token, "bot")
        return error is None
    
    async def modify_channel(self, channel_id, payload, token):
        return await self._request_with_retry("PATCH", f"/channels/{channel_id}", token, "bot", payload)
    
    async def modify_guild(self, guild_id, payload, token):
        return await self._request_with_retry("PATCH", f"/guilds/{guild_id}", token, "bot", payload)
    
    async def reorder_roles(self, guild_id, positions, token):
        return await self._request_with_retry("PATCH", f"/guilds/{guild_id}/roles", token, "bot", positions)

class GuildCloner:
    def __init__(self, api_client):
        self.api = api_client
        self.role_mapping = {}
        self.category_mapping = {}
        self.created_channels = []
        self.failed_items = []
        
    def _get_timestamp(self):
        return datetime.now().strftime("%H:%M:%S")
    
    def _log(self, level, message):
        config = {
            "info": ("→", ConsoleColors.CYAN),
            "ok": ("✓", ConsoleColors.GREEN),
            "err": ("✗", ConsoleColors.RED),
            "warn": ("!", ConsoleColors.YELLOW),
            "clone": ("⊕", ConsoleColors.MAGENTA),
            "del": ("−", ConsoleColors.RED),
            "fetch": ("↓", ConsoleColors.BLUE),
            "verify": ("~", ConsoleColors.MAGENTA),
        }
        icon, color = config.get(level, ("·", ConsoleColors.WHITE))
        print(f"  {ConsoleColors.DIM}{self._get_timestamp()}{ConsoleColors.ENDC}  {color}{icon}{ConsoleColors.ENDC}  {message}")
    
    def _print_section(self, title):
        print()
        print(f"{ConsoleColors.MAGENTA}{'═' * 60}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.BOLD}{ConsoleColors.MAGENTA}{title.upper()}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.MAGENTA}{'═' * 60}{ConsoleColors.ENDC}")
        print()
    
    def _print_banner(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print()
        
        ascii_art = """
                ██╗██████╗░███████╗███╗░░██╗██╗░█████╗░
                ██║██╔══██╗██╔════╝████╗░██║██║██╔══██╗
                ██║██████╔╝█████╗░░██╔██╗██║██║██║░░╚═╝
                ██║██╔══██╗██╔══╝░░██║╚████║██║██║░░██╗
                ██║██║░░██║███████╗██║░╚███║██║╚█████╔╝
                ╚═╝╚═╝░░╚═╝╚══════╝╚═╝░░╚══╝╚═╝░╚════╝░
        """
        print(f"{ConsoleColors.MAGENTA}{ConsoleColors.BOLD}{ascii_art}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.CYAN}{'=' * 60}{ConsoleColors.ENDC}")
        print(f"{ConsoleColors.CYAN}MADE BY Irenic")
        print(f"{ConsoleColors.CYAN}{'=' * 60}{ConsoleColors.ENDC}")
        print()
    
    async def validate_tokens(self, bot_token, user_token):
        self._log("info", "Validating tokens...")
        
        bot_data, bot_error = await self.api.get_bot_user(bot_token)
        if bot_error or not bot_data:
            self._log("err", f"Bot token invalid: {bot_error}")
            return False, None, None
            
        user_data, user_error = await self.api.get_user(user_token)
        if user_error or not user_data:
            self._log("err", f"User token invalid: {user_error}")
            return False, None, None
            
        self._log("ok", f"Bot: {bot_data.get('username')}#{bot_data.get('discriminator', '0')}")
        self._log("ok", f"User: {user_data.get('username')}#{user_data.get('discriminator', '0')}")
        
        return True, bot_data.get('username'), user_data.get('username')
    
    async def validate_bot_in_guild(self, guild_id, bot_token):
        self._log("info", f"Verifying bot access to guild {guild_id}")
        
        guild_data, error = await self.api.get_guild(guild_id, bot_token, "bot")
        if error or not guild_data:
            self._log("err", "Bot not in destination server or lacks permissions")
            print()
            print(Panel.create(
                "Add the bot to the destination server with Administrator permissions:\n\n"
                "https://discord.com/oauth2/authorize?client_id=BOT_CLIENT_ID&permissions=8&scope=bot",
                title="Bot Missing",
                border_style=ConsoleColors.RED
            ))
            return False
            
        self._log("ok", f"Bot verified in: {guild_data.get('name')}")
        return True
    
    async def fetch_source_guild_data(self, guild_id, user_token):
        self._log("fetch", "Retrieving source guild data...")
        
        guild_info, error1 = await self.api.get_guild(guild_id, user_token, "user")
        if error1 or not guild_info:
            self._log("err", f"Could not fetch source guild: {error1}")
            return None, None, None
            
        channels, error2 = await self.api.get_guild_channels(guild_id, user_token, "user")
        if error2:
            self._log("err", f"Could not fetch channels: {error2}")
            return None, None, None
            
        roles, error3 = await self.api.get_guild_roles(guild_id, user_token, "user")
        if error3:
            self._log("err", f"Could not fetch roles: {error3}")
            return None, None, None
            
        self._display_source_info(guild_info, channels, roles)
        return guild_info, channels, roles
    
    def _display_source_info(self, guild_info, channels, roles):
        categories = [c for c in channels if c.get('type') == 4]
        text_channels = [c for c in channels if c.get('type') == 0]
        voice_channels = [c for c in channels if c.get('type') == 2]
        other_channels = [c for c in channels if c.get('type') not in (0, 2, 4)]
        user_roles = [r for r in roles if r.get('name') != '@everyone' and not r.get('managed')]
        
        info_data = {
            "Name": guild_info.get('name', '?'),
            "ID": guild_info.get('id', '?'),
            "Members": guild_info.get('approximate_member_count', '?'),
            "Online": guild_info.get('approximate_presence_count', '?'),
            "Icon": "Yes" if guild_info.get('icon') else "No",
            "Description": guild_info.get('description') or "—",
            "Boost Level": guild_info.get('premium_tier', 0),
            "Total Channels": len(channels),
            "Categories": len(categories),
            "Text Channels": len(text_channels),
            "Voice Channels": len(voice_channels),
            "Other Channels": len(other_channels),
            "Roles": len(user_roles),
        }
        
        rows = [[k.upper(), str(v).upper()] for k, v in info_data.items()]
        print(Table.create_table(["Property", "Value"], rows))
    
    async def wipe_channels(self, guild_id, bot_token):
        self._log("info", "Clearing existing channels...")
        
        channels, error = await self.api.get_guild_channels(guild_id, bot_token, "bot")
        if error or not channels:
            self._log("err", f"Could not fetch channels: {error}")
            return
            
        if not channels:
            self._log("info", "No channels to clear")
            return
            
        self._log("info", f"Removing {len(channels)} channels...")
        
        tasks = [self.api.delete_channel(c['id'], bot_token) for c in channels]
        successful = 0
        for i in range(0, len(tasks), self.api.max_workers):
            batch = tasks[i:i + self.api.max_workers]
            results = await asyncio.gather(*batch, return_exceptions=True)
            successful += sum(1 for r in results if r is True)
        
        self._log("ok", f"Removed {successful}/{len(channels)} channels")
    
    async def wipe_roles(self, guild_id, bot_token):
        self._log("info", "Clearing existing roles...")
        
        roles, error = await self.api.get_guild_roles(guild_id, bot_token, "bot")
        if error or not roles:
            self._log("err", f"Could not fetch roles: {error}")
            return
            
        removable = sorted(
            [r for r in roles if not r.get('managed') and r['name'] != '@everyone'],
            key=lambda r: r['position'],
            reverse=True
        )
        
        if not removable:
            self._log("info", "No removable roles found")
            return
            
        self._log("info", f"Removing {len(removable)} roles...")
        
        successful = 0
        for role in removable:
            success = await self.api.delete_role(guild_id, role['id'], bot_token)
            if success:
                successful += 1
            else:
                self._log("warn", f"Could not delete role: {role['name']}")
            await asyncio.sleep(0.25)
        
        self._log("ok", f"Removed {successful}/{len(removable)} roles")
    
    async def _build_permission_overwrites(self, overwrites):
        built = []
        for ow in overwrites:
            target_id = None
            if ow['type'] == 0:
                target_id = self.role_mapping.get(ow['id'])
            elif ow['type'] == 1:
                target_id = ow['id']
            if target_id:
                built.append({
                    "id": target_id,
                    "type": ow['type'],
                    "allow": ow.get('allow', '0'),
                    "deny": ow.get('deny', '0'),
                })
        return built
    
    async def clone_roles(self, source_roles, guild_id, bot_token):
        self._log("info", "Cloning roles...")
        self.role_mapping.clear()
        
        cloneable = sorted(
            [r for r in source_roles if r['name'] != '@everyone' and not r.get('managed')],
            key=lambda r: r['position'],
            reverse=True
        )
        
        self._log("info", f"Cloning {len(cloneable)} roles...")
        
        created_roles = []
        for role in cloneable:
            payload = {
                "name": role['name'],
                "permissions": role.get('permissions', '0'),
                "color": role.get('color', 0),
                "hoist": role.get('hoist', False),
                "mentionable": role.get('mentionable', False),
            }
            
            data, error = await self.api.create_role(guild_id, payload, bot_token)
            if error:
                self._log("err", f"Failed to create role {role['name']}: {error}")
                self.failed_items.append({"type": "role", "name": role['name'], "reason": error})
            elif data and 'id' in data:
                self.role_mapping[role['id']] = data['id']
                created_roles.append({"id": data['id'], "position": role['position']})
                self._log("clone", f"Cloned role: {role['name']}")
            await asyncio.sleep(0.25)
        
        if created_roles:
            self._log("info", "Reordering roles...")
            positions = [{"id": r['id'], "position": r['position']} for r in created_roles]
            _, error = await self.api.reorder_roles(guild_id, positions, bot_token)
            if error:
                self._log("warn", f"Could not reorder roles: {error}")
            else:
                self._log("ok", "Roles reordered successfully")
        
        self._log("ok", f"Cloned {len(self.role_mapping)}/{len(cloneable)} roles")
    
    async def clone_categories(self, source_channels, guild_id, bot_token):
        self._log("info", "Cloning categories...")
        self.category_mapping.clear()
        
        categories = sorted([c for c in source_channels if c['type'] == 4], key=lambda c: c['position'])
        self._log("info", f"Cloning {len(categories)} categories...")
        
        for cat in categories:
            overwrites = await self._build_permission_overwrites(cat.get('permission_overwrites', []))
            payload = {
                "name": cat['name'],
                "type": 4,
                "position": cat['position'],
                "permission_overwrites": overwrites,
            }
            
            data, error = await self.api.create_channel(guild_id, payload, bot_token)
            if error:
                self._log("err", f"Failed to create category {cat['name']}: {error}")
                self.failed_items.append({"type": "category", "name": cat['name'], "reason": error})
            elif data and 'id' in data:
                self.category_mapping[cat['id']] = data['id']
                self._log("clone", f"Cloned category: {cat['name']}")
            await asyncio.sleep(0.2)
        
        self._log("ok", f"Cloned {len(self.category_mapping)}/{len(categories)} categories")
    
    async def clone_single_channel(self, channel, guild_id, bot_token):
        overwrites = await self._build_permission_overwrites(channel.get('permission_overwrites', []))
        payload = {
            "name": channel['name'],
            "type": channel['type'],
            "position": channel['position'],
            "permission_overwrites": overwrites,
        }
        
        if channel.get('parent_id') and channel['parent_id'] in self.category_mapping:
            payload['parent_id'] = self.category_mapping[channel['parent_id']]
        
        if channel['type'] == 0:
            payload['topic'] = channel.get('topic') or ""
            payload['nsfw'] = channel.get('nsfw', False)
            payload['rate_limit_per_user'] = channel.get('rate_limit_per_user', 0)
        elif channel['type'] == 2:
            payload['bitrate'] = channel.get('bitrate', 64000)
            payload['user_limit'] = channel.get('user_limit', 0)
        elif channel['type'] in (5, 15):
            payload['topic'] = channel.get('topic') or ""
        
        return await self.api.create_channel(guild_id, payload, bot_token)
    
    async def clone_channels(self, source_channels, guild_id, bot_token):
        self._log("info", "Cloning channels...")
        
        non_categories = sorted(
            [c for c in source_channels if c['type'] != 4],
            key=lambda c: (c.get('parent_id') or "", c['position'])
        )
        
        self._log("info", f"Cloning {len(non_categories)} channels...")
        
        successful = 0
        for i in range(0, len(non_categories), self.api.max_workers):
            batch = non_categories[i:i + self.api.max_workers]
            tasks = [self.clone_single_channel(ch, guild_id, bot_token) for ch in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, result in enumerate(results):
                channel = batch[idx]
                if isinstance(result, Exception):
                    self._log("err", f"Exception cloning #{channel['name']}: {str(result)}")
                    self.failed_items.append({"type": "channel", "name": channel['name'], "reason": str(result)})
                elif result and result[0] and 'id' in result[0]:
                    data, _ = result
                    self.created_channels.append({"orig": channel, "new": data})
                    self._log("clone", f"Cloned channel: #{channel['name']}")
                    successful += 1
                else:
                    self._log("err", f"Failed to clone #{channel['name']}")
                    self.failed_items.append({"type": "channel", "name": channel['name'], "reason": "Unknown error"})
        
        self._log("ok", f"Cloned {successful}/{len(non_categories)} channels")
    
    async def apply_server_info(self, source_info, guild_id, bot_token):
        self._log("info", "Applying server info...")
        payload = {"name": source_info.get('name', 'Cloned Server')}
        
        if source_info.get('description'):
            payload['description'] = source_info['description']
        
        if source_info.get('icon'):
            self._log("fetch", "Downloading server icon...")
            icon_hash = source_info['icon']
            ext = "gif" if icon_hash.startswith("a_") else "png"
            icon_url = f"https://cdn.discordapp.com/icons/{source_info['id']}/{icon_hash}.{ext}?size=4096"
            
            async with self.api.session.get(icon_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    b64_icon = base64.b64encode(image_data).decode('utf-8')
                    payload['icon'] = f"data:image/{ext};base64,{b64_icon}"
                    self._log("ok", f"Icon ready ({len(image_data)//1024}KB)")
                else:
                    self._log("warn", f"Icon download returned {response.status}")
        
        data, error = await self.api.modify_guild(guild_id, payload, bot_token)
        if error:
            self._log("warn", f"Server update failed: {error}")
        else:
            self._log("ok", f"Server updated to: {data.get('name')}")
    
    async def verify_channels(self, source_channels):
        self._log("verify", f"Checking {len(self.created_channels)} channels...")
        
        mismatches = []
        verified = 0
        
        for item in self.created_channels:
            orig = item['orig']
            created = item['new']
            
            pos_ok = created.get('position') == orig.get('position')
            cat_ok = True
            if orig.get('parent_id'):
                cat_ok = self.category_mapping.get(orig['parent_id']) == created.get('parent_id')
            
            if pos_ok and cat_ok:
                verified += 1
            else:
                mismatches.append(item)
        
        self._log("ok", f"Verified {verified}/{len(self.created_channels)} channels")
        
        if mismatches:
            self._log("warn", f"Found {len(mismatches)} mismatches, repairing...")
            repaired = 0
            for item in mismatches:
                orig = item['orig']
                created = item['new']
                fix = {"position": orig.get('position', 0)}
                pid = orig.get('parent_id')
                if pid and pid in self.category_mapping:
                    fix['parent_id'] = self.category_mapping[pid]
                
                data, error = await self.api.modify_channel(created['id'], fix, bot_token)
                if error:
                    self._log("err", f"Repair failed #{orig['name']}: {error}")
                else:
                    self._log("ok", f"Repaired #{orig['name']}")
                    repaired += 1
                await asyncio.sleep(0.25)
            
            self._log("ok", f"Repaired {repaired}/{len(mismatches)} mismatches")
    
    def _display_summary(self, source_roles, source_channels):
        self._print_section("Summary")
        
        total_roles = len([r for r in source_roles if r['name'] != '@everyone' and not r.get('managed')])
        total_categories = len([c for c in source_channels if c['type'] == 4])
        total_channels = len([c for c in source_channels if c['type'] != 4])
        
        role_failures = len([f for f in self.failed_items if f['type'] == 'role'])
        category_failures = len([f for f in self.failed_items if f['type'] == 'category'])
        channel_failures = len([f for f in self.failed_items if f['type'] == 'channel'])
        
        rows = [
            ["ROLES CLONED", f"{len(self.role_mapping)}/{total_roles}"],
            ["CATEGORIES CLONED", f"{len(self.category_mapping)}/{total_categories}"],
            ["CHANNELS CLONED", f"{len(self.created_channels)}/{total_channels}"],
            ["ROLE FAILURES", str(role_failures) if role_failures > 0 else f"{ConsoleColors.GREEN}0{ConsoleColors.ENDC}"],
            ["CATEGORY FAILURES", str(category_failures) if category_failures > 0 else f"{ConsoleColors.GREEN}0{ConsoleColors.ENDC}"],
            ["CHANNEL FAILURES", str(channel_failures) if channel_failures > 0 else f"{ConsoleColors.GREEN}0{ConsoleColors.ENDC}"],
            ["TOTAL FAILURES", str(len(self.failed_items)) if self.failed_items else f"{ConsoleColors.GREEN}0{ConsoleColors.ENDC}"],
        ]
        
        print(Table.create_table(["Metric", "Value"], rows))
        
        if self.failed_items:
            print()
            print(f"{ConsoleColors.WARNING}Common causes for failures:{ConsoleColors.ENDC}")
            print(f"{ConsoleColors.WARNING}  Bot role sits below roles it's trying to create{ConsoleColors.ENDC}")
            print(f"{ConsoleColors.WARNING}  Missing Manage Roles / Manage Channels permissions{ConsoleColors.ENDC}")
            print(f"{ConsoleColors.WARNING}  Discord rejecting special characters in names{ConsoleColors.ENDC}")
        else:
            print()
            print(f"{ConsoleColors.GREEN}{ConsoleColors.BOLD}DONE — ZERO ERRORS{ConsoleColors.ENDC}")

async def run():
    api_client = DiscordAPIClient(max_workers=10, retry_attempts=5)
    cloner = GuildCloner(api_client)
    
    cloner._print_banner()
    cloner._print_section("Setup")
    
    print(f"{ConsoleColors.CYAN}Enter Bot Token:{ConsoleColors.ENDC} ")
    bot_token = input().strip()
    
    print(f"{ConsoleColors.CYAN}Enter User Token:{ConsoleColors.ENDC} ")
    user_token = input().strip()
    
    async with api_client:
        valid, bot_name, user_name = await cloner.validate_tokens(bot_token, user_token)
        if not valid:
            print(f"{ConsoleColors.RED}Fix token issues before continuing{ConsoleColors.ENDC}")
            return
        
        cloner._print_section("Source Server")
        print(f"{ConsoleColors.CYAN}Enter Source Server ID:{ConsoleColors.ENDC} ")
        source_id = input().strip()
        
        source_info, source_channels, source_roles = await cloner.fetch_source_guild_data(source_id, user_token)
        if not source_info:
            return
        
        cloner._print_section("Destination Server")
        print(f"{ConsoleColors.CYAN}Enter Destination Server ID:{ConsoleColors.ENDC} ")
        dest_id = input().strip()
        
        bot_ok = await cloner.validate_bot_in_guild(dest_id, bot_token)
        if not bot_ok:
            return
        
        print()
        print(f"{ConsoleColors.YELLOW}Wipe destination before cloning? (y/n):{ConsoleColors.ENDC} ")
        wipe = input().strip().lower() == 'y'
        
        if wipe:
            await cloner.wipe_channels(dest_id, bot_token)
            await asyncio.sleep(0.5)
            await cloner.wipe_roles(dest_id, bot_token)
            await asyncio.sleep(0.5)
        
        await cloner.clone_roles(source_roles, dest_id, bot_token)
        await asyncio.sleep(0.3)
        
        await cloner.clone_categories(source_channels, dest_id, bot_token)
        await asyncio.sleep(0.3)
        
        await cloner.clone_channels(source_channels, dest_id, bot_token)
        await asyncio.sleep(0.3)
        
        await cloner.apply_server_info(source_info, dest_id, bot_token)
        await asyncio.sleep(0.3)
        
        await cloner.verify_channels(source_channels)
        
        cloner._display_summary(source_roles, source_channels)

if __name__ == "__main__":
    asyncio.run(run())
