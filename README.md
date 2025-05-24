# Reddit Fountain Pen Monitor Bot

## 📖 Overview

Monitors Reddit (e.g., r/Pen_Swap) for new posts about specific fountain pens and sends notifications to a Discord channel. Uses `asyncpraw` and `discord.py`.

## ✨ Features

*   Monitors subreddits for new posts based on keywords/pen models.
*   Sends Discord notifications for matching posts.
*   Prevents duplicate notifications using a local `shelve` database.
*   Configurable API keys, subreddit, query, and pen models.

## 🛠️ Setup

1.  **Clone**: `git clone <your-repository-url> && cd fountain-pen-bot`
2.  **Venv & Install**: 
    ```bash
    python3 -m venv myenv
    source myenv/bin/activate # or myenv\Scripts\activate on Windows
    pip install -r requirements.txt
    ```
3.  **Configure `main/config.py`**:
    Create `main/config.py` and add your API keys and settings:
    ```python
    # Reddit API Credentials
    REDDIT_CLIENT_ID = "YOUR_REDDIT_CLIENT_ID"
    REDDIT_CLIENT_SECRET = "YOUR_REDDIT_CLIENT_SECRET"
    REDDIT_USER_AGENT = "FountainPenBot/0.1 by YourUsername"

    # Discord Bot Credentials
    DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
    DISCORD_CHANNEL_ID = YOUR_DISCORD_CHANNEL_ID_INT # e.g., 123456789012345678

    TARGET_MODELS = <Pen_1>, <Pen_2>, ...
    ```
    *   Get Reddit API credentials from [Reddit app preferences](https://www.reddit.com/prefs/apps) (create a "script" app).
    *   Get Discord Bot Token and Channel ID from the [Discord Developer Portal](https://discord.com/developers/applications) (create a bot, enable Message Content Intent, and invite it to your server).

## ▶️ Usage

Run from the project root:
```bash
python main/main.py
```
Logs to console and `output.txt`.

## 💻 Technologies

*   Python 3.x
*   asyncpraw, discord.py, TheFuzz, shelve

## 🤝 Contributing

Issues and PRs welcome. Discuss significant changes via an issue first. 