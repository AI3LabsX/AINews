# AI3 Daily News Bot

AI3 Daily News Bot is a unique bot with an adjustable personality designed to deliver news updates. It integrates with
OpenAI and Telegram to provide a seamless experience for users.

## Getting Started

Follow these instructions to get the bot up and running on your local machine.

### Prerequisites

- **Python**
- **Pipenv**

### Installation

1. **Clone the repository:**
    ``` cmd
   git clone https://github.com/AI3LabsX/AINews.git
   ```

2. **Navigate to the project directory:**
    ```cmd
   cd ai3labsnews
    ```

3. **Install the required dependencies using Pipenv:**
    ```cmd
   pipenv install
   ```

### Configuration

Before running the bot, you need to set up the necessary environment variables:

1. **Set the OpenAI API key:**
    ``` cmd
   set OPENAI_API_KEY='your_openai_api_key'
   ```

2. **Set the Telegram Bot token:**
    ``` cmd
   set BOT_TOKEN='your_telegram_bot_token'
   ```

3. **Set the database URL:**
    ``` cmd
    set DATABASE_URL='your_database_url'
   ```

### Usage

After setting up the environment variables, you can run the bot.

Make sure to change the Telegram channel to `@ai3daily`:

```python
TELEGRAM_CHANNEL = '@ChannelName'
```

### Features

- News Delivery: The bot delivers daily news updates to the specified Telegram channel.
- Adjustable Personality: Customize the bot's personality to fit your audience's preferences.
- Integration with OpenAI: Leverage the power of OpenAI to make the bot more intelligent and responsive.

### Contributing

If you'd like to contribute to the project, please submit a pull request or open an issue to discuss the changes.

### License
This project is licensed under the MIT License. See the LICENSE file for details.
