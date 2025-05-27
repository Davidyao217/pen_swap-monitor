# Discord Bot Commands

This bot provides **9 simple commands** for managing fountain pen aliases and monitoring:

## Commands Overview

### 1. Add New Pen - `/add_pen`
Add a completely new fountain pen to the database with its aliases.

**Usage:** `/add_pen formal_name:<formal name> aliases:<alias1, alias2, alias3>`

**Parameters:**
- `formal_name`: The official/formal name for the pen (e.g., "Pelikan M200")
- `aliases`: *(Optional)* Comma-separated list of aliases/casual names (e.g., "m200, pelikan m200")

**Examples:**
```
/add_pen formal_name:Pelikan M200 aliases:m200, pelikan m200
/add_pen formal_name:Opus 88 Koloro    (no aliases - will use "opus 88 koloro" as only alias)
```

**What it does:**
- Adds a completely new pen entry to the database
- If no aliases provided, uses the formal name (lowercased) as the only alias
- Validates that the formal name doesn't already exist
- Checks for conflicts with existing formal names
- Saves permanently to the `pen_aliases.txt` file
- Shows the total number of pens in the database

### 2. Remove Pen - `/remove_pen`
Completely remove a fountain pen from the database.

**Usage:** `/remove_pen pen_name:<pen name>`

**Parameters:**
- `pen_name`: The pen to remove (uses fuzzy matching)

**Example:**
```
/remove_pen pen_name:pelikan m200
```

**What it does:**
- Completely removes the pen and ALL its aliases from the database
- Also removes the pen from monitoring if it's currently being monitored
- Permanently deletes from the `pen_aliases.txt` file
- Shows what was removed and remaining database size
- ⚠️ **This action cannot be undone!**

### 3. Add Aliases - `/add_aliases`
**Description:** Add aliases to an existing fountain pen  
**Usage:** `/add_aliases pen_name:<name> new_aliases:<alias1, alias2, ...>`

- Adds new aliases to an existing pen in the database
- Aliases should be comma-separated
- Uses fuzzy matching to find the pen name
- Shows all current aliases after adding

#### `/remove_aliases`
**Description:** Remove aliases from an existing fountain pen  
**Usage:** `/remove_aliases pen_name:<name> aliases_to_remove:<alias1, alias2, ...>`

- Removes specific aliases from an existing pen
- Aliases should be comma-separated
- Shows which aliases were removed and which weren't found
- Shows remaining aliases after removal

#### `/list_aliases`
**Description:** List all fountain pens and their aliases  
**Usage:** `/list_aliases`

- Shows all pens in the database with their aliases
- Paginated if there are many pens (10 per page)
- Use this to see what pens are available

### Monitoring Management

#### `/add_monitoring`
**Description:** Add pens to the monitoring list  
**Usage:** `/add_monitoring pen_names:<name1, name2, ...>`

- Adds multiple pens to the current monitoring list
- Pen names should be comma-separated
- Uses fuzzy matching to find each pen name
- Won't add duplicate terms if already monitoring
- Shows which pens were added and which weren't found

#### `/remove_monitoring`
**Description:** Remove pens from the monitoring list  
**Usage:** `/remove_monitoring pen_names:<name1, name2, ...>` or `/remove_monitoring pen_names:ALL`

- Removes multiple pens from the monitoring list
- Pen names should be comma-separated
- Uses fuzzy matching to find each pen name
- Shows which pens were removed and which weren't found

#### `/show_monitoring`
**Description:** Show which pens are currently being monitored  
**Usage:** `/show_monitoring`

- Displays only the formal pen names being monitored
- Shows total number of active search terms
- Clean view without showing all individual search terms

### Force Search

#### `/force_search`
**Description:** Force search recent posts immediately without waiting  
**Usage:** `/force_search limit:<number>`

- Searches the most recent posts immediately (no waiting for monitoring cycle)
- Does not check if posts were already processed
- Limit: 1-50 posts (default: 10)
- Shows summary of results and sends each matching post
- Useful for immediate results and testing
- Uses current monitoring list to determine what to search for

**Examples:**
```
/force_search limit:10    (search last 10 posts)
/force_search limit:25    (search last 25 posts)
/force_search             (search last 10 posts - default)
```

## How It Works

1. **Pen Database**: The bot maintains a bidirectional mapping between formal pen names and their casual aliases
2. **Fuzzy Matching**: When you specify a pen name, it finds the best match even if you don't type the exact name
3. **Dynamic Monitoring**: Add or remove pens from monitoring in real-time through Discord
4. **Search Terms**: Each pen generates multiple search terms (formal name + all aliases) used for Reddit monitoring

## Example Workflow

1. Check what pens are available: `/list_aliases`
2. Add multiple pens to monitoring: `/add_monitoring pen_names:pilot custom 74, vanishing point, lamy 2000`
3. Check what's being monitored: `/show_monitoring`
4. **Force search recent posts immediately**: `/force_search limit:20`
5. Add more aliases if needed: `/add_aliases pen_name:pilot custom 74 new_aliases:pc74, custom74`
6. Remove some pens from monitoring: `/remove_monitoring pen_names:lamy 2000, vanishing point`

## Pre-loaded Pens

The bot comes pre-loaded with popular fountain pens including:
- **Pilot Vanishing Point** (aliases: vp, pilot vp, vanishing point, pilot vanishing)
- **Pilot Custom 74** (aliases: custom 74, pc74, pilot custom, custom74)
- **Pilot Custom Heritage 92** (aliases: custom 92, ch92, heritage 92, pilot ch92)
- **Sailor Pro Gear** (aliases: pro gear, sailor pro, progear)
- **Sailor 1911** (aliases: 1911, sailor 1911)
- **Lamy Safari** (aliases: safari, lamy safari)
- **Lamy 2000** (aliases: 2000, lamy 2000, l2k)
- **Montblanc 146** (aliases: 146, mb146, montblanc 146, meisterstuck 146, montblanc, mb)
- **Montblanc 149** (aliases: 149, mb149, montblanc 149, meisterstuck 149, montblanc, mb)
- **Pelikan M800** (aliases: m800, pelikan m800, souveran m800)
- **Pelikan M1000** (aliases: m1000, pelikan m1000, souveran m1000, pelikan)
- **TWSBI Eco** (aliases: eco, twsbi eco, twsbi)
- **Parker Sonnet** (aliases: sonnet, parker sonnet, parker)
- **Kaweco Sport** (aliases: sport, kaweco sport, kaweco)
- **Platinum 3776** (aliases: 3776, platinum 3776, platinum)

## Tips

- **Fuzzy Matching**: You don't need to type exact names. "vp" will find "Pilot Vanishing Point"
- **Case Insensitive**: Commands work with any capitalization
- **One Pen at a Time**: Commands work with single pens for simplicity
- **Aliases vs Monitoring**: Aliases are permanent additions to the database, monitoring is temporary and can be changed anytime

## New Commands

### 10. `/reload_aliases` - Reload pen aliases from file
**Usage:** `/reload_aliases`

Reload the pen aliases database from the `pen_aliases.txt` file. Useful if you manually edited the file and want to update the bot's in-memory data without restarting.

### 11. `/reload_monitoring` - Reload monitoring list from file  
**Usage:** `/reload_monitoring`

Reload the monitoring list from the `monitoring_list.txt` file. Useful if you manually edited the monitoring file and want to update the bot's in-memory data without restarting.

## Command Workflow

### Adding New Pens
1. Use `/add_pen` to add a completely new fountain pen
2. Use `/add_aliases` to add more aliases to existing pens
3. Use `/add_monitoring` to start monitoring the pen

### Managing Monitoring
1. Use `/show_monitoring` to see what's currently monitored
2. Use `/add_monitoring` to add pens (comma-separated for multiple)
3. Use `/remove_monitoring` to remove specific pens or "ALL"
4. Use `/force_search` to immediately check recent posts

### Database Management
1. Use `/list_aliases` to see all pens and their aliases
2. Use `/remove_aliases` to remove unwanted aliases
3. Use `/remove_pen` to completely remove pens
4. Use `/reload_aliases` or `/reload_monitoring` to resync from files

## Technical Details

- **Fuzzy Matching:** Commands use fuzzy text matching, so "vanishing point" will find "Pilot Vanishing Point"
- **Formal Names:** Monitoring stores only formal pen names, but searches use all aliases
- **Search Terms:** Each monitored pen expands to multiple search terms (formal name + all aliases)
- **File Persistence:** All data is stored in `pen_aliases.txt` and `monitoring_list.txt`
- **Manual Editing:** You can manually edit the .txt files and use reload commands to sync changes

## Examples

### Complete Setup Workflow
```
/add_pen formal_name:Pilot Custom Heritage 912 aliases:ch912, custom 912
/add_aliases pen_name:custom heritage new_aliases:heritage 912, pilot 912
/add_monitoring pen_names:custom heritage, vanishing point
/show_monitoring
/force_search limit:20
```

### Multiple Pen Monitoring
```
/add_monitoring pen_names:vanishing point, lamy 2000, sailor pro gear, custom 74
/show_monitoring
/remove_monitoring pen_names:lamy 2000
```

### File Synchronization
```
# After manually editing pen_aliases.txt:
/reload_aliases

# After manually editing monitoring_list.txt:  
/reload_monitoring
``` 