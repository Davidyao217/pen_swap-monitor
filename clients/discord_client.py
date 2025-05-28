import asyncio
import discord
from discord.ext import commands, tasks
from config import DISCORD_TOKEN, CHANNEL_ID, INTERVAL
from clients.reddit_client import fetch_and_send_new_posts, force_search_recent_posts
import shelve
import os
from datetime import datetime
import sys
from thefuzz import fuzz

# Implement lazy loading - import these only when needed
# instead of at startup
_text_utils_loaded = False
_db_manager_loaded = False
_pen_names_map = None
_fuzz = None

# Lazy loading functions
def load_text_utils():
    global _text_utils_loaded, find_matching_pen_names, get_all_search_terms_for_pens
    global add_new_pen_mapping, add_aliases_to_pen, remove_aliases_from_pen
    global remove_pen_completely, _pen_names_map, get_monitoring_list
    global add_formal_pens_to_monitoring, remove_formal_pens_from_monitoring
    global clear_all_monitoring, get_all_monitoring_search_terms
    global format_discord_message, reload_pen_aliases_from_file
    global reload_monitoring_from_file, validate_pen_name_input
    global validate_aliases_input, normalize_text, save_pen_aliases_to_file
    global get_aliases_file_path
    
    if not _text_utils_loaded:
        print("Loading text utilities...")
        from utils.text_utils import (
            find_matching_pen_names, 
            get_all_search_terms_for_pens,
            add_new_pen_mapping,
            add_aliases_to_pen,
            remove_aliases_from_pen,
            remove_pen_completely,
            pen_names_map as loaded_pen_names_map,
            get_monitoring_list,
            add_formal_pens_to_monitoring,
            remove_formal_pens_from_monitoring,
            clear_all_monitoring,
            get_all_monitoring_search_terms,
            format_discord_message,
            reload_pen_aliases_from_file,
            reload_monitoring_from_file,
            validate_pen_name_input,
            validate_aliases_input,
            normalize_text,
            save_pen_aliases_to_file,
            get_aliases_file_path
        )
        global pen_names_map
        pen_names_map = loaded_pen_names_map
        _pen_names_map = loaded_pen_names_map
        _text_utils_loaded = True

def load_db_manager():
    global _db_manager_loaded, get_seen_posts_count, get_recent_posts_count, repair_database
    
    if not _db_manager_loaded:
        print("Loading database manager...")
        from utils.db_manager import get_seen_posts_count, get_recent_posts_count, repair_database
        _db_manager_loaded = True

def load_fuzz():
    global _fuzz
    if not _fuzz:
        print("Loading fuzzy matching...")
        from thefuzz import fuzz
        _fuzz = fuzz

class PenSearchBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.reddit_client = None
        self.monitoring_channel = None
        self.start_time = datetime.now()
        self.commands_synced = False

    async def setup_hook(self):
        """Called when the bot is starting up."""
        # Defer syncing commands until absolutely necessary
        pass

    async def sync_commands(self):
        """Sync commands only when needed"""
        if not self.commands_synced:
            print("Syncing commands...")
            start_time = datetime.now()
            await self.tree.sync()
            duration = (datetime.now() - start_time).total_seconds()
            print(f"Synced {len(self.tree.get_commands())} slash commands in {duration:.2f}s")
            self.commands_synced = True

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
        # Load the monitoring channel
        self.monitoring_channel = self.get_channel(CHANNEL_ID)
        if self.monitoring_channel:
            print(f"Found monitoring channel: {self.monitoring_channel.name}")
            
            # Start syncing commands in the background
            asyncio.create_task(self.sync_commands())
            
            # Start monitoring
            if not self.reddit_monitor.is_running():
                self.reddit_monitor.start()
        else:
            print(f"Warning: Could not find channel with ID {CHANNEL_ID}")

    def set_reddit_client(self, reddit_client):
        """Set the Reddit client for monitoring."""
        self.reddit_client = reddit_client

    @tasks.loop(seconds=INTERVAL)
    async def reddit_monitor(self):
        """Monitor Reddit for new posts."""
        if self.monitoring_channel and self.reddit_client:
            load_text_utils()  # Ensure text utilities are loaded
            print("Calling fetch_and_send_new_posts")
            await fetch_and_send_new_posts(self.monitoring_channel, self.reddit_client)

    @reddit_monitor.before_loop
    async def before_reddit_monitor(self):
        """Wait for the bot to be ready before starting the monitor."""
        await self.wait_until_ready()

    def get_uptime(self):
        """Get bot uptime as a formatted string."""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

# Create bot instance
bot = PenSearchBot()

@bot.command(name="info")
async def info_command(ctx):
    """Show bot commands and statistics."""
    
    # Load dependencies when needed
    load_text_utils()
    load_db_manager()
    
    # Get statistics
    monitoring_list = get_monitoring_list()
    total_search_terms = len(get_all_monitoring_search_terms())
    seen_posts_count = get_seen_posts_count()
    recent_posts_count = get_recent_posts_count()
    uptime = bot.get_uptime()
    reddit_status = "🟢 Connected" if bot.reddit_client else "🔴 Disconnected"
    
    embed = discord.Embed(
        title="🖋️ Fountain Pen Bot Info",
        description="Monitor r/Pen_Swap for fountain pen mentions",
        color=discord.Color.blue()
    )
    
    # Bot Statistics
    embed.add_field(
        name="📊 Bot Statistics",
        value=f"**Uptime:** {uptime}\n"
              f"**Reddit Status:** {reddit_status}\n"
              f"**Check Interval:** {INTERVAL}s\n"
              f"**Lifetime Posts Seen:** {seen_posts_count:,}\n"
              f"**Recent Posts Seen:** {recent_posts_count:,}",
        inline=True
    )
    
    # Database Statistics  
    embed.add_field(
        name="🗄️ Database Stats",
        value=f"**Total Pens:** {len(pen_names_map.keys())}\n"
              f"**Monitored Pens:** {len(monitoring_list)}\n"
              f"**Search Terms:** {total_search_terms}",
        inline=True
    )
    
    # Command Summary
    commands_text = (
        "**📝 Pen Management**\n"
        "`/add_pen` - Add new pen to database\n"
        "`/remove_pen` - Remove pen completely\n"
        "`/add_aliases` - Add aliases to existing pen\n"
        "`/remove_aliases` - Remove aliases from pen\n"
        "`/list_aliases` - Show all pens and aliases\n\n"
        
        "**👁️ Monitoring**\n"
        "`/add_monitoring` - Start monitoring pen(s)\n"
        "`/remove_monitoring` - Stop monitoring pen(s)\n"
        "`/show_monitoring` - Show monitored pens\n"
        "`/force_search` - Search recent posts now\n\n"
        
        "**🔄 System**\n"
        "`/reload` - Reload data from files (aliases, monitoring)\n"
        "`/maintenance` - Perform system maintenance (check map, repair database)\n"
        "`!info` - Show this info message"
    )
    
    embed.add_field(
        name="⚙️ Commands (12 total)",
        value=commands_text,
        inline=False
    )
    
    # Usage tips
    embed.add_field(
        name="💡 Quick Tips",
        value="• Use fuzzy matching: `vp` finds `Pilot Vanishing Point`\n"
              "• Add multiple pens: `/add_monitoring pen_names:vp, lamy 2000`\n"
              "• Remove all monitoring: `/remove_monitoring pen_names:ALL`\n"
              "• Force search for immediate results: `/force_search limit:25`",
        inline=False
    )
    
    embed.set_footer(text="Use slash commands (/) for pen management • Type !info for this message")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="add_aliases", description="Add aliases to an existing fountain pen")
async def add_aliases(interaction: discord.Interaction, pen_name: str, new_aliases: str):
    """Add new aliases to an existing pen in the database."""
    await interaction.response.defer()
    
    # Load required modules
    load_text_utils()
    
    # Validate pen name input
    is_valid, error_msg = validate_pen_name_input(pen_name)
    if not is_valid:
        embed = discord.Embed(
            title="❌ Invalid Pen Name",
            description=error_msg,
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Validate and parse aliases
    is_valid, error_msg, alias_list = validate_aliases_input(new_aliases)
    if not is_valid:
        embed = discord.Embed(
            title="❌ Invalid Aliases",
            description=error_msg,
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Find the formal pen name
    matches = find_matching_pen_names(pen_name, max_results=1)
    if not matches:
        embed = discord.Embed(
            title="❌ Pen Not Found",
            description=f"No pen found matching '{pen_name}'. Use /list_aliases to see available pens, or /add_pen to add a new pen.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    formal_name = matches[0]
    
    # Add the new aliases
    add_aliases_to_pen(formal_name, alias_list)
    
    embed = discord.Embed(
        title="✅ Aliases Added",
        description=f"Successfully added aliases to '{formal_name}'",
        color=discord.Color.green()
    )
    embed.add_field(
        name="New Aliases",
        value=', '.join(alias_list),
        inline=False
    )
    
    # Show all current aliases
    all_aliases = list(pen_names_map.get_values(formal_name))
    embed.add_field(
        name="All Aliases",
        value=', '.join(sorted(all_aliases)),
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="add_pen", description="Add a completely new fountain pen to the database")
async def add_pen(interaction: discord.Interaction, formal_name: str, aliases: str = ""):
    """Add a completely new pen to the database with its aliases."""
    await interaction.response.defer()
    
    # Load required modules
    load_text_utils()
    
    # Validate formal name input
    is_valid, error_msg = validate_pen_name_input(formal_name)
    if not is_valid:
        embed = discord.Embed(
            title="❌ Invalid Pen Name",
            description=error_msg,
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    formal_name_clean = formal_name.strip()
    
    # Handle aliases - if empty, use formal name as only alias
    if aliases.strip():
        is_valid, error_msg, alias_list = validate_aliases_input(aliases)
        if not is_valid:
            embed = discord.Embed(
                title="❌ Invalid Aliases",
                description=error_msg,
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
    else:
        # If no aliases provided, use the formal name itself as the only alias
        alias_list = [formal_name_clean.lower()]
    
    # Check if pen already exists
    if formal_name_clean in pen_names_map.keys():
        embed = discord.Embed(
            title="❌ Pen Already Exists",
            description=f"'{formal_name_clean}' already exists in the database. Use /add_aliases to add more aliases.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check if any alias conflicts with existing formal names
    conflicts = []
    for alias in alias_list:
        if alias.lower() in [fn.lower() for fn in pen_names_map.keys()]:
            conflicts.append(alias)
    
    if conflicts:
        embed = discord.Embed(
            title="❌ Alias Conflict",
            description=f"These aliases conflict with existing formal pen names: {', '.join(conflicts)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Add the new pen
    add_new_pen_mapping(formal_name_clean, alias_list)
    
    embed = discord.Embed(
        title="✅ New Pen Added",
        description=f"Successfully added '{formal_name_clean}' to the database",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Formal Name",
        value=formal_name_clean,
        inline=False
    )
    embed.add_field(
        name="Aliases",
        value=', '.join(alias_list),
        inline=False
    )
    embed.add_field(
        name="Total Pens in Database",
        value=f"{len(pen_names_map.keys())} pens",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="remove_aliases", description="Remove aliases from an existing fountain pen")
async def remove_aliases(interaction: discord.Interaction, pen_name: str, aliases_to_remove: str):
    """Remove aliases from an existing pen in the database."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    # Parse aliases to remove
    aliases_list = [alias.strip().lower() for alias in aliases_to_remove.split(',') if alias.strip()]
    
    if not aliases_list:
        embed = discord.Embed(
            title="❌ Error",
            description="Please provide at least one alias to remove (comma-separated)",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Find the formal pen name
    matches = find_matching_pen_names(pen_name, max_results=1)
    if not matches:
        embed = discord.Embed(
            title="❌ Pen Not Found",
            description=f"No pen found matching '{pen_name}'. Use /list_aliases to see available pens.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    formal_name = matches[0]
    
    # Remove aliases using the persistent function
    removed_aliases, not_found_aliases = remove_aliases_from_pen(formal_name, aliases_list)
    
    embed = discord.Embed(
        title="✅ Aliases Removed" if removed_aliases else "⚠️ No Changes",
        color=discord.Color.green() if removed_aliases else discord.Color.orange()
    )
    
    if removed_aliases:
        embed.add_field(
            name="Removed Aliases",
            value=', '.join(removed_aliases),
            inline=False
        )
    
    if not_found_aliases:
        embed.add_field(
            name="⚠️ Not Found",
            value=', '.join(not_found_aliases),
            inline=False
        )
    
    # Show remaining aliases
    remaining_aliases = list(pen_names_map.get_values(formal_name))
    embed.add_field(
        name="Remaining Aliases",
        value=', '.join(sorted(remaining_aliases)) if remaining_aliases else "None",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="list_aliases", description="List all fountain pens and their aliases")
async def list_aliases(interaction: discord.Interaction):
    """List all fountain pens and their aliases."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    # Read directly from the file instead of relying on the map data structure
    from utils.text_utils import get_aliases_file_path
    file_path = get_aliases_file_path()
    
    # Read the file manually to get all pens
    all_pens = []
    pen_aliases = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue
                
                if '|' not in line:
                    continue
                
                formal_name, aliases_str = line.split('|', 1)
                formal_name = formal_name.strip()
                
                if not formal_name:
                    continue
                
                # Parse aliases (comma-separated)
                aliases = [alias.strip().lower() for alias in aliases_str.split(',') if alias.strip()]
                
                all_pens.append(formal_name)
                pen_aliases[formal_name] = aliases
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error Reading Pen Database",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Sort the pens
    all_pens.sort()
    
    if not all_pens:
        embed = discord.Embed(
            title="📚 Pen Database",
            description="No pens found in database",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Split into chunks if too many pens
    pen_chunks = [all_pens[i:i+10] for i in range(0, len(all_pens), 10)]
    
    for chunk_idx, pen_chunk in enumerate(pen_chunks):
        embed = discord.Embed(
            title=f"📚 Pen Database (Page {chunk_idx + 1}/{len(pen_chunks)})",
            color=discord.Color.green()
        )
        
        for formal_name in pen_chunk:
            aliases = pen_aliases.get(formal_name, [])
            aliases_text = ', '.join(sorted(aliases)) if aliases else "None"
            embed.add_field(
                name=formal_name,
                value=f"**Aliases:** {aliases_text}",
                inline=False
            )
        
        if chunk_idx == 0:
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="add_monitoring", description="Add pens to the monitoring list")
async def add_monitoring(interaction: discord.Interaction, pen_names: str):
    """Add pens to the monitoring list."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    # Parse pen names (comma-separated)
    input_names = [name.strip() for name in pen_names.split(',') if name.strip()]
    
    if not input_names:
        embed = discord.Embed(
            title="❌ Error",
            description="Please provide at least one pen name (comma-separated)",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Find matching formal names for each input
    all_matches = []
    not_found = []
    
    for input_name in input_names:
        matches = find_matching_pen_names(input_name, max_results=1)  # Only get the BEST match
        if matches:
            all_matches.extend(matches)
        else:
            not_found.append(input_name)
    
    if not all_matches:
        embed = discord.Embed(
            title="❌ No Matches Found",
            description=f"None of the provided pen names matched any in the database:\n{', '.join(not_found)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Add formal names to monitoring (not all search terms)
    new_names_added = add_formal_pens_to_monitoring(all_matches)
    
    embed = discord.Embed(
        title="✅ Monitoring Added",
        description=f"Added {len(all_matches)} pen model(s) to monitoring",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Added Pens",
        value='\n'.join([f"• {name}" for name in all_matches]),
        inline=False
    )
    
    if new_names_added > 0:
        embed.add_field(
            name="New Pens Added",
            value=f"{new_names_added} new pens",
            inline=False
        )
    else:
        embed.add_field(
            name="Already Monitoring",
            value="All these pens were already being monitored",
            inline=False
        )
    
    if not_found:
        embed.add_field(
            name="⚠️ Not Found",
            value=', '.join(not_found),
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="remove_monitoring", description="Remove pens from the monitoring list")
async def remove_monitoring(interaction: discord.Interaction, pen_names: str):
    """Remove pens from the monitoring list."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    # Handle special case: remove ALL monitoring
    if pen_names.strip().upper() == "ALL":
        current_monitoring = get_monitoring_list()
        if not current_monitoring:
            embed = discord.Embed(
                title="⚠️ Already Empty",
                description="No pens are currently being monitored",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Find which formal pen names were being monitored
        monitored_pens = set(current_monitoring)  # Now contains formal names directly
        
        removed_count = clear_all_monitoring()
        
        embed = discord.Embed(
            title="✅ All Monitoring Removed",
            description=f"Cleared all monitoring ({removed_count} formal pen names)",
            color=discord.Color.green()
        )
        
        if monitored_pens:
            embed.add_field(
                name="Previously Monitored Pens",
                value='\n'.join([f"• {pen}" for pen in sorted(monitored_pens)]),
                inline=False
            )
        
        embed.add_field(
            name="Formal Names Removed",
            value=f"{removed_count} pens removed",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        return
    
    # Parse pen names (comma-separated)
    input_names = [name.strip() for name in pen_names.split(',') if name.strip()]
    
    if not input_names:
        embed = discord.Embed(
            title="❌ Error",
            description="Please provide at least one pen name (comma-separated) or 'ALL'",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Find matching formal names for each input
    all_matches = []
    not_found = []
    
    for input_name in input_names:
        matches = find_matching_pen_names(input_name, max_results=1)
        if matches:
            all_matches.extend(matches)
        else:
            not_found.append(input_name)
    
    if not all_matches:
        embed = discord.Embed(
            title="❌ No Matches Found",
            description=f"None of the provided pen names matched any in the database:\n{', '.join(not_found)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Remove formal names from monitoring (not search terms)
    removed_count = remove_formal_pens_from_monitoring(all_matches)
    
    embed = discord.Embed(
        title="✅ Monitoring Removed",
        description=f"Removed {len(all_matches)} pen model(s) from monitoring",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Removed Pens",
        value='\n'.join([f"• {name}" for name in all_matches]),
        inline=False
    )
    
    embed.add_field(
        name="Formal Names Removed",
        value=f"{removed_count} pens removed",
        inline=False
    )
    
    if not_found:
        embed.add_field(
            name="⚠️ Not Found",
            value=', '.join(not_found),
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="show_monitoring", description="Show which pens are currently being monitored")
async def show_monitoring(interaction: discord.Interaction):
    """Show which pens are currently being monitored."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    monitoring_list = get_monitoring_list()
    
    if not monitoring_list:
        embed = discord.Embed(
            title="👁️ Current Monitoring",
            description="No pens are currently being monitored",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="👁️ Current Monitoring",
        description=f"Monitoring {len(monitoring_list)} pen model(s)",
        color=discord.Color.blue()
    )
    
    pen_list = '\n'.join([f"• {pen}" for pen in sorted(monitoring_list)])
    embed.add_field(
        name="Monitored Pens (Formal Names)",
        value=pen_list,
        inline=False
    )
    
    # Show total search terms that will be used for actual searching
    total_search_terms = len(get_all_monitoring_search_terms())
    embed.add_field(
        name="Total Search Terms Generated",
        value=f"{total_search_terms} terms (including all aliases)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_pen", description="Completely remove a fountain pen from the database")
async def remove_pen(interaction: discord.Interaction, pen_name: str):
    """Completely remove a fountain pen from the database."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    # Find the formal pen name
    matches = find_matching_pen_names(pen_name, max_results=1)
    if not matches:
        embed = discord.Embed(
            title="❌ Pen Not Found",
            description=f"No pen found matching '{pen_name}'. Use /list_aliases to see available pens.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    formal_name = matches[0]
    
    # Get all search terms for this pen before removing (for monitoring cleanup)
    formal_names_to_remove = [formal_name]
    
    # Remove the pen completely
    success, removed_aliases = remove_pen_completely(formal_name)
    
    if not success:
        embed = discord.Embed(
            title="❌ Removal Failed",
            description=f"Failed to remove '{formal_name}' from database",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Also remove from monitoring if it's being monitored
    monitoring_removed = remove_formal_pens_from_monitoring(formal_names_to_remove)
    
    embed = discord.Embed(
        title="🗑️ Pen Removed",
        description=f"Successfully removed '{formal_name}' from the database",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Removed Aliases",
        value=', '.join(removed_aliases) if removed_aliases else "None",
        inline=False
    )
    
    if monitoring_removed > 0:
        embed.add_field(
            name="Also Removed from Monitoring",
            value=f"{monitoring_removed} search terms removed from monitoring",
            inline=False
        )
    
    embed.add_field(
        name="Database Status",
        value=f"{len(pen_names_map.keys())} pens remaining in database",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="force_search", description="Force search recent posts immediately (max 50)")
async def force_search(interaction: discord.Interaction, limit: int = 10):
    """Force search recent posts immediately without checking seen status."""
    await interaction.response.defer()
    
    # Load required modules
    load_text_utils()
    load_db_manager()  # Ensure DB manager is loaded for get_seen_posts_count
    
    # Validate limit
    if limit < 1 or limit > 50:
        embed = discord.Embed(
            title="❌ Invalid Limit",
            description="Limit must be between 1 and 50",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check if we have pens to monitor
    monitoring_list = get_monitoring_list()
    if not monitoring_list:
        embed = discord.Embed(
            title="❌ No Monitoring Active",
            description="No pens are currently being monitored. Use `/add_monitoring` to add pens first.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Check if bot has Reddit client
    if not bot.reddit_client:
        embed = discord.Embed(
            title="❌ Reddit Client Not Available",
            description="Reddit client is not initialized. Bot may be starting up.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    try:
        # Perform the force search
        found_posts = await force_search_recent_posts(bot.reddit_client, limit)
        
        if not found_posts:
            embed = discord.Embed(
                title="🔍 Force Search Complete",
                description=f"Searched {limit} recent posts - no matches found",
                color=discord.Color.orange()
            )
            
            # Get updated count
            posts_seen_count = get_seen_posts_count()
            embed.add_field(
                name="Lifetime Posts Seen",
                value=f"{posts_seen_count} posts",
                inline=True
            )
            
            recent_posts_count = get_recent_posts_count()
            embed.add_field(
                name="Recent Posts Stored",
                value=f"{recent_posts_count}/100 posts",
                inline=True
            )
            
            embed.add_field(
                name="Monitoring",
                value=f"{len(monitoring_list)} pens: {', '.join(monitoring_list[:3])}{'...' if len(monitoring_list) > 3 else ''}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Send results summary first
        embed = discord.Embed(
            title="🔍 Force Search Complete",
            description=f"Found {len(found_posts)} matching posts from {limit} searched",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Matches",
            value=f"{len(found_posts)} posts contain monitored pens",
            inline=False
        )
        
        # Get updated count
        posts_seen_count = get_seen_posts_count()
        embed.add_field(
            name="Lifetime Posts Seen",
            value=f"{posts_seen_count} posts",
            inline=True
        )
        
        recent_posts_count = get_recent_posts_count()
        embed.add_field(
            name="Recent Posts Stored",
            value=f"{recent_posts_count}/100 posts",
            inline=True
        )
        
        embed.add_field(
            name="Monitoring",
            value=f"{len(monitoring_list)} pens: {', '.join(monitoring_list[:3])}{'...' if len(monitoring_list) > 3 else ''}",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        # Send each matching post as a formatted message
        for post_data in found_posts:
            submission = post_data['submission']
            found_models = post_data['found_models']
            combined_text = post_data['combined_text']
            
            # Format the same way as the monitoring system
            message = format_discord_message(
                submission_title=submission.title,
                combined_text=combined_text,
                found_pen_models=found_models,
                permalink=submission.permalink
            )
            
            # Add a prefix to indicate this is from force search
            force_search_message = f"🔍 **FORCE SEARCH RESULT:**\n{message}"
            await interaction.followup.send(force_search_message)
            
    except Exception as e:
        print(f"Error in force search command: {e}")
        embed = discord.Embed(
            title="❌ Search Failed",
            description=f"An error occurred during the search: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="maintenance", description="Perform system maintenance (check map, repair database)")
async def maintenance(interaction: discord.Interaction, operation: str = "all"):
    """Combined maintenance command for system operations."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    load_db_manager()
    
    embed = discord.Embed(
        title="🔧 System Maintenance",
        color=discord.Color.blue()
    )
    
    # Check pen map if requested
    if operation.lower() in ["all", "map"]:
        # Force validation of the map
        issues_fixed = pen_names_map.validate()
        
        if issues_fixed:
            embed.add_field(
                name="🔧 Map Repair",
                value=f"Fixed {len(issues_fixed)} consistency issues in the pen map",
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Map Check",
                value="The pen map is consistent with no issues found",
                inline=False
            )
            
        # Map statistics
        embed.add_field(
            name="Map Statistics",
            value=f"• Formal pen names: {len(pen_names_map._one_to_many)}\n• Total aliases: {len(pen_names_map._many_to_one)}",
            inline=True
        )
    
    # Repair database if requested
    if operation.lower() in ["all", "database"]:
        # Run the repair function
        report = repair_database()
        
        # Original state
        embed.add_field(
            name="📊 Database Repair",
            value=f"**Original:** {report['original_lifetime']} lifetime, {report['original_recent']} recent\n"
                  f"**New:** {report['new_lifetime']} lifetime, {report['new_recent']} recent",
            inline=False
        )
        
        # Changes made
        changes = []
        if report.get("fixed_lifetime_count"):
            changes.append("✓ Fixed inconsistent lifetime count")
        if report.get("fixed_post_order"):
            changes.append("✓ Fixed post order list")
        if report.get("removed_duplicates", 0) > 0:
            changes.append(f"✓ Removed {report['removed_duplicates']} duplicate entries")
        if "error" in report:
            changes.append(f"❌ Error occurred: {report['error']}")
        if not changes:
            changes.append("✓ No issues found, database is healthy")
            
        if changes:
            embed.add_field(
                name="🔍 Changes Made",
                value="\n".join(changes),
                inline=False
            )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="reload", description="Reload data from files (aliases, monitoring)")
async def reload(interaction: discord.Interaction, data_type: str = "all"):
    """Combined reload command for reloading data from files."""
    await interaction.response.defer()
    
    # Load dependencies
    load_text_utils()
    
    embed = discord.Embed(
        title="🔄 Reload Data",
        color=discord.Color.blue()
    )
    
    # Reload pen aliases if requested
    if data_type.lower() in ["all", "aliases"]:
        success, message = reload_pen_aliases_from_file()
        embed.add_field(
            name="Pen Aliases Reload",
            value=f"{'✅' if success else '❌'} {message}",
            inline=False
        )
    
    # Reload monitoring list if requested
    if data_type.lower() in ["all", "monitoring"]:
        success, message = reload_monitoring_from_file()
        embed.add_field(
            name="Monitoring List Reload",
            value=f"{'✅' if success else '❌'} {message}",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

async def run_discord_bot(reddit_client):
    """Initialize and run the Discord bot with Reddit monitoring."""
    try:
        print("Starting Discord bot...")
        bot.set_reddit_client(reddit_client)
        print("Discord initialization completed, connecting to Discord API...")
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"Discord bot error: {e}") 