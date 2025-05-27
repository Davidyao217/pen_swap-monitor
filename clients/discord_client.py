import asyncio
import discord
from discord.ext import commands, tasks
from config import DISCORD_TOKEN, CHANNEL_ID, INTERVAL
from clients.reddit_client import fetch_and_send_new_posts, force_search_recent_posts
import shelve
import os
from datetime import datetime
from utils.text_utils import (
    find_matching_pen_names, 
    get_all_search_terms_for_pens,
    add_new_pen_mapping,
    add_aliases_to_pen,
    remove_aliases_from_pen,
    remove_pen_completely,
    pen_names_map,
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
from utils.db_manager import get_seen_posts_count, get_recent_posts_count, repair_database
from thefuzz import fuzz

class PenSearchBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.reddit_client = None
        self.monitoring_channel = None
        self.start_time = datetime.now()

    async def setup_hook(self):
        """Called when the bot is starting up."""
        await self.tree.sync()
        print(f"Synced {len(self.tree.get_commands())} slash commands")

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.monitoring_channel = self.get_channel(CHANNEL_ID)
        if self.monitoring_channel:
            print(f"Found monitoring channel: {self.monitoring_channel.name}")
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
        "`/reload_aliases` - Reload pen database\n"
        "`/reload_monitoring` - Reload monitoring list\n"
        "`/repair_database` - Fix counter inconsistencies\n"
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
    """List all fountain pens in the database with their aliases."""
    await interaction.response.defer()
    
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
    """Add pens to the current monitoring list."""
    await interaction.response.defer()
    
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
    """Remove pens from the monitoring list. Use 'ALL' to remove all monitoring."""
    await interaction.response.defer()
    
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
    """Remove a pen completely from the database (formal name and all aliases)."""
    await interaction.response.defer()
    
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
    """Force search recent posts without waiting for monitoring cycle."""
    await interaction.response.defer()
    
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

@bot.tree.command(name="reload_aliases", description="Reload pen aliases from the pen_aliases.txt file")
async def reload_aliases(interaction: discord.Interaction):
    """Reload pen aliases from the file, updating in-memory data."""
    await interaction.response.defer()
    
    success, message = reload_pen_aliases_from_file()
    
    if success:
        embed = discord.Embed(
            title="🔄 Aliases Reloaded",
            description=message,
            color=discord.Color.green()
        )
        embed.add_field(
            name="File Location",
            value="`pen_aliases.txt`",
            inline=False
        )
        embed.add_field(
            name="Current Database Size",
            value=f"{len(pen_names_map.keys())} pens",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="❌ Reload Failed",
            description=message,
            color=discord.Color.red()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="reload_monitoring", description="Reload monitoring list from the monitoring_list.txt file")
async def reload_monitoring(interaction: discord.Interaction):
    """Reload monitoring list from the file, updating in-memory data."""
    await interaction.response.defer()
    
    success, message = reload_monitoring_from_file()
    
    if success:
        current_monitoring = get_monitoring_list()
        total_search_terms = len(get_all_monitoring_search_terms())
        
        embed = discord.Embed(
            title="🔄 Monitoring Reloaded",
            description=message,
            color=discord.Color.green()
        )
        embed.add_field(
            name="File Location",
            value="`monitoring_list.txt`",
            inline=False
        )
        embed.add_field(
            name="Current Monitoring",
            value=f"{len(current_monitoring)} pens → {total_search_terms} search terms",
            inline=False
        )
        
        if current_monitoring:
            pen_list = '\n'.join([f"• {pen}" for pen in sorted(current_monitoring[:5])])
            if len(current_monitoring) > 5:
                pen_list += f"\n• ... and {len(current_monitoring) - 5} more"
            embed.add_field(
                name="Monitored Pens",
                value=pen_list,
                inline=False
            )
    else:
        embed = discord.Embed(
            title="❌ Reload Failed",
            description=message,
            color=discord.Color.red()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="check_alias", description="Check which pen model an alias maps to")
async def check_alias(interaction: discord.Interaction, alias: str):
    """Look up which formal pen name an alias maps to."""
    await interaction.response.defer()
    
    if not alias or not alias.strip():
        embed = discord.Embed(
            title="❌ Invalid Input",
            description="Please provide an alias to check",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    alias = alias.strip().lower()
    
    # First try direct lookup in the many-to-one mapping
    direct_match = None
    for formal_name, aliases in pen_names_map._one_to_many.items():
        if alias in aliases:
            direct_match = formal_name
            break
    
    if direct_match:
        # Found exact match
        all_aliases = sorted(list(pen_names_map.get_values(direct_match)))
        
        embed = discord.Embed(
            title="✅ Alias Match Found",
            description=f"The alias `{alias}` maps to:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Formal Pen Name",
            value=f"**{direct_match}**",
            inline=False
        )
        embed.add_field(
            name="All Aliases",
            value=', '.join(all_aliases),
            inline=False
        )
    else:
        # No exact match, try fuzzy matching to suggest alternatives
        matches = find_matching_pen_names(alias, max_results=3, threshold=75)
        
        if matches:
            embed = discord.Embed(
                title="❓ No Exact Match Found",
                description=f"The alias `{alias}` doesn't map to any pen directly, but here are some similar pens:",
                color=discord.Color.orange()
            )
            
            for i, match in enumerate(matches, 1):
                all_aliases = sorted(list(pen_names_map.get_values(match)))
                embed.add_field(
                    name=f"Suggestion {i}: {match}",
                    value=f"Aliases: {', '.join(all_aliases)}",
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="❌ No Match Found",
                description=f"The alias `{alias}` doesn't map to any pen in the database.",
                color=discord.Color.red()
            )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="debug_match", description="Debug how a search term matches to pen models")
async def debug_match(interaction: discord.Interaction, search_term: str):
    """Show detailed information about how a search term matches to pen models."""
    await interaction.response.defer()
    
    if not search_term or not search_term.strip():
        embed = discord.Embed(
            title="❌ Invalid Input",
            description="Please provide a search term to debug",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    search_term = search_term.strip()
    search_term_lower = search_term.lower()
    search_term_normalized = normalize_text(search_term)
    
    # Get the top matches using our improved algorithm
    matches = find_matching_pen_names(search_term, max_results=5, threshold=60)
    
    if not matches:
        embed = discord.Embed(
            title="❌ No Matches Found",
            description=f"No pens matched `{search_term}` with a score above the threshold.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return
    
    # Collect details about each match for debugging
    match_details = []
    
    for formal_name in matches:
        # Check different matching criteria
        formal_name_lower = formal_name.lower()
        formal_name_normalized = normalize_text(formal_name)
        
        # Get all aliases
        aliases = list(pen_names_map.get_values(formal_name))
        
        # Determine match type and score
        match_type = "unknown"
        match_score = 0
        matching_alias = None
        
        # 1. Exact case-insensitive match with formal name
        if formal_name_lower == search_term_lower:
            match_type = "exact_formal"
            match_score = 100
        
        # 2. Exact case-insensitive match with any alias
        elif any(alias.lower() == search_term_lower for alias in aliases):
            match_type = "exact_alias"
            match_score = 99
            matching_alias = next(alias for alias in aliases if alias.lower() == search_term_lower)
        
        # 3. Normalized exact match with formal name
        elif formal_name_normalized == search_term_normalized:
            match_type = "normalized_formal"
            match_score = 98
        
        # 4. Normalized exact match with any alias
        elif any(normalize_text(alias) == search_term_normalized for alias in aliases):
            match_type = "normalized_alias"
            match_score = 97
            matching_alias = next(alias for alias in aliases if normalize_text(alias) == search_term_normalized)
        
        # 5. Exact word match in alias
        elif any(search_term_normalized in normalize_text(alias).split() for alias in aliases):
            match_type = "exact_word_match"
            match_score = 96
            matching_alias = next(alias for alias in aliases if search_term_normalized in normalize_text(alias).split())
        
        # 6. Exact word match in formal name
        elif search_term_normalized in formal_name_normalized.split():
            match_type = "formal_word_match"
            match_score = 95
        
        # 7. Must be fuzzy match
        else:
            match_type = "fuzzy"
            # Get best fuzzy score across all aliases
            for alias in aliases:
                alias_normalized = normalize_text(alias)
                ratio_score = fuzz.ratio(search_term_normalized, alias_normalized)
                partial_score = fuzz.partial_ratio(search_term_normalized, alias_normalized)
                score = max(ratio_score, partial_score)
                
                if score > match_score:
                    match_score = score
                    matching_alias = alias
            
            # Also check formal name
            ratio_score = fuzz.ratio(search_term_normalized, formal_name_normalized)
            partial_score = fuzz.partial_ratio(search_term_normalized, formal_name_normalized)
            score = max(ratio_score, partial_score)
            
            if score > match_score:
                match_score = score
                matching_alias = None  # Match is with formal name
        
        match_details.append({
            "formal_name": formal_name,
            "match_type": match_type,
            "match_score": match_score,
            "matching_alias": matching_alias,
            "aliases": aliases
        })
    
    # Create embed with detailed match information
    embed = discord.Embed(
        title="🔍 Match Debugging Results",
        description=f"How `{search_term}` matches to pen models:",
        color=discord.Color.blue()
    )
    
    for i, detail in enumerate(match_details, 1):
        match_description = [
            f"**Score:** {detail['match_score']}",
            f"**Match Type:** {detail['match_type']}"
        ]
        
        if detail['matching_alias']:
            match_description.append(f"**Matched Alias:** {detail['matching_alias']}")
        
        match_description.append(f"**All Aliases:** {', '.join(detail['aliases'])}")
        
        embed.add_field(
            name=f"{i}. {detail['formal_name']}",
            value="\n".join(match_description),
            inline=False
        )
    
    embed.set_footer(text="This command helps diagnose matching issues and shows how the search algorithm works")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="fix_lamy_dialog", description="Fix the Lamy Dialog entry in the database")
async def fix_lamy_dialog(interaction: discord.Interaction):
    """Fix the Lamy Dialog entry specifically."""
    await interaction.response.defer()
    
    # First check if it exists
    has_lamy = False
    for key in pen_names_map._one_to_many.keys():
        if key.lower() == "lamy dialog":
            has_lamy = True
            print(f"Found existing Lamy Dialog as '{key}'")
            break
    
    # Force remove any existing entry to clean up
    if has_lamy:
        for key in list(pen_names_map._one_to_many.keys()):
            if key.lower() == "lamy dialog":
                # Remove from one-to-many
                aliases = list(pen_names_map._one_to_many[key])
                del pen_names_map._one_to_many[key]
                # Remove from many-to-one
                for alias in aliases:
                    if alias in pen_names_map._many_to_one:
                        del pen_names_map._many_to_one[alias]
                print(f"Removed existing Lamy Dialog entry: '{key}' with aliases {aliases}")
    
    # Now add a fresh entry
    formal_name = "Lamy Dialog"
    aliases = ["dialog", "dialog 3", "dialog cc", "lamy dialog"]
    
    # Add to map
    for alias in aliases:
        pen_names_map.add(formal_name, alias)
    
    # Save to file - using functions we already imported at the top
    save_pen_aliases_to_file(pen_names_map, get_aliases_file_path())
    
    # Validate the map
    issues_fixed = pen_names_map.validate()
    if issues_fixed:
        print(f"Fixed {len(issues_fixed)} issues after adding Lamy Dialog")
    
    # Check if it was added
    if "Lamy Dialog" in pen_names_map._one_to_many:
        embed = discord.Embed(
            title="✅ Fixed Lamy Dialog",
            description="Successfully added/fixed the Lamy Dialog entry",
            color=discord.Color.green()
        )
        
        actual_aliases = list(pen_names_map.get_values("Lamy Dialog"))
        embed.add_field(
            name="Lamy Dialog Aliases",
            value=', '.join(actual_aliases),
            inline=False
        )
        
        # Count all pens
        all_pens = list(pen_names_map._one_to_many.keys())
        embed.add_field(
            name="Database Status",
            value=f"{len(all_pens)} pens in database",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="❌ Fix Failed",
            description="Could not add Lamy Dialog to the database",
            color=discord.Color.red()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="check_map", description="Check the pen map for consistency issues")
async def check_map(interaction: discord.Interaction):
    """Check and repair the pen map for consistency."""
    await interaction.response.defer()
    
    # Force validation of the map
    issues_fixed = pen_names_map.validate()
    
    # Check for Lamy Dialog specifically
    has_lamy = False
    for key in pen_names_map._one_to_many.keys():
        if key.lower() == "lamy dialog":
            has_lamy = True
            lamy_key = key
            break
            
    if issues_fixed:
        embed = discord.Embed(
            title="🔧 Map Repaired",
            description=f"Fixed {len(issues_fixed)} consistency issues in the pen map",
            color=discord.Color.green()
        )
        
        # Show some of the fixes
        fixes_text = "\n".join([f"• {issue}" for issue in issues_fixed[:5]])
        if len(issues_fixed) > 5:
            fixes_text += f"\n... and {len(issues_fixed) - 5} more"
            
        embed.add_field(
            name="Issues Fixed",
            value=fixes_text,
            inline=False
        )
    else:
        embed = discord.Embed(
            title="✅ Map Consistency Check",
            description="The pen map is consistent with no issues found",
            color=discord.Color.green()
        )
    
    # Map statistics
    embed.add_field(
        name="Map Statistics",
        value=f"• Formal pen names: {len(pen_names_map._one_to_many)}\n• Total aliases: {len(pen_names_map._many_to_one)}",
        inline=False
    )
    
    # Lamy Dialog check
    if has_lamy:
        lamy_aliases = list(pen_names_map.get_values(lamy_key))
        embed.add_field(
            name="Lamy Dialog Check",
            value=f"✅ Present as '{lamy_key}' with {len(lamy_aliases)} aliases: {', '.join(lamy_aliases)}",
            inline=False
        )
    else:
        embed.add_field(
            name="Lamy Dialog Check",
            value="❌ Not found in the map",
            inline=False
        )
        
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="repair_database", description="Repair the post database to fix counter inconsistencies")
async def repair_database_command(interaction: discord.Interaction):
    """Repair the post database to fix any inconsistencies."""
    await interaction.response.defer()
    
    # Run the repair function
    report = repair_database()
    
    # Create an embed with the results
    embed = discord.Embed(
        title="🔧 Database Repair Results",
        color=discord.Color.blue()
    )
    
    # Original state
    embed.add_field(
        name="📊 Original State",
        value=f"**Lifetime Posts:** {report['original_lifetime']}\n"
              f"**Recent Posts:** {report['original_recent']}",
        inline=True
    )
    
    # New state
    embed.add_field(
        name="✅ New State",
        value=f"**Lifetime Posts:** {report['new_lifetime']}\n"
              f"**Recent Posts:** {report['new_recent']}",
        inline=True
    )
    
    # Changes made
    changes = []
    if report["fixed_lifetime_count"]:
        changes.append("✓ Fixed inconsistent lifetime count")
    if report["fixed_post_order"]:
        changes.append("✓ Fixed post order list")
    if report["removed_duplicates"] > 0:
        changes.append(f"✓ Removed {report['removed_duplicates']} duplicate entries")
    if "error" in report:
        changes.append(f"❌ Error occurred: {report['error']}")
    if not changes:
        changes.append("✓ No issues found, database is healthy")
        
    embed.add_field(
        name="🔍 Changes Made",
        value="\n".join(changes),
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

async def run_discord_bot(reddit_client):
    """Initialize and run the Discord bot with Reddit monitoring."""
    bot.set_reddit_client(reddit_client)
    await bot.start(DISCORD_TOKEN) 