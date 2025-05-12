from ast import literal_eval
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import ConnectError, ConnectTimeout, ReadTimeout
import json
from os import getenv
import os
from time import sleep
from twikit import Client, Tweet
from twikit.errors import AccountSuspended, Forbidden, TooManyRequests, Unauthorized

from posthandler import PostHandler, DiscordFilterType

if getenv('DEV_VAR') == 'rudizabudi':
    print('DEV MODE')
    config_file = 'config_dev.json'
else:
    config_file = 'config.json'

config_file_path = os.path.join(os.path.dirname(__file__), config_file)
def load_config(config_file_path: str):
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError('Config file not found. Please create a config.json file.')
    
    return config

config = load_config(config_file_path)
reversed_dft = {v: k for k, v in DiscordFilterType._member_map_.items()}

for webbhook_data in config['webhooks'].values():
    for webhook in webbhook_data:
        webhook['filter']['filter_type'] = DiscordFilterType[reversed_dft[webhook['filter']['filter_type']]]
        webhook['filter']['filter_data'] = webhook['filter']['filter_data'].split(',')

INTERVAL: int = 15 #modulo update intervall in mins
UPDATE_OFFSET: int = 20 #offset to update point in secs

USERNAME: str = config['x_account']['username'] #twitter
EMAIL: str = config['x_account']['email'] #twitter
PASSWORD: str = config['x_account']['password'] #twitter
COOKIES_FILE: str = os.path.join(os.path.dirname(__file__), config['x_account']['cookies_file'])

TWITTER_IDS, MIRROR_DISCORD, webhooks = None, None, None


client: Client = Client('en-US')
post_handler: PostHandler = PostHandler()

async def main():
    try:
        env_update_hour: int = -1  #update twitter settings on each hour change

        await client.login(
            auth_info_1 = USERNAME,
            auth_info_2 = EMAIL,
            password = PASSWORD,
            cookies_file = COOKIES_FILE)

        def request_discord_settings() -> tuple[list[str], bool, dict[str: dict[str: str]]]:
            config = load_config(config_file_path)
            TWITTER_IDS: list[str] = list(config['x_ids'].values()) #get from here https://ilo.so/twitter-id/
            MIRROR_DISCORD: bool = config['use_discord'] #discord mirror switch
            webhooks: dict[str: dict[str: str | dict[str, str]]] = config['webhooks']

            return TWITTER_IDS, MIRROR_DISCORD, webhooks

        i: int = 0
        while True:
            if datetime.now().hour != env_update_hour or not any([TWITTER_IDS, MIRROR_DISCORD, webhooks]):
                TWITTER_IDS, MIRROR_DISCORD, webhooks = request_discord_settings()
                env_update_hour = datetime.now().hour

                post_handler.set_discord_settings(mirroring=MIRROR_DISCORD, webhooks=webhooks)

            while i < len(TWITTER_IDS):
                try:
                    await ask_tweets(twitter_id=TWITTER_IDS[i], ph=post_handler)
                    sleep(5)
                    i += 1
                except ConnectError:
                    pass        
            
            i = 0
            post_handler.process_msgs()

            for min in range(1, INTERVAL + 1):
                next_update = datetime.now() + timedelta(minutes=min)
                if next_update.minute % INTERVAL == 0:
                    break

            next_update = next_update.replace(second=UPDATE_OFFSET, microsecond=0)

            wait_time = next_update - datetime.now()
            sleep(wait_time.seconds)

    except (AccountSuspended, ConnectTimeout, Forbidden, ReadTimeout, TooManyRequests) as e:
        print(f'Error occured. Sleeping for 600 seconds. {e}')
        sleep(600)
    
    except Unauthorized:
        cookies_path = os.path.join(os.path.dirname(__file__), COOKIES_FILE)
        os.remove(cookies_path)
        sleep(10)
    sleep(60)

"""     except Exception as e:
        print(f'Not handled error: {e}')
        sleep(600) """
        

async def ask_tweets(twitter_id: str, ph: PostHandler):
    tweets: list[Tweet] = await client.get_user_tweets(user_id=twitter_id, tweet_type='Tweets', count=10)

    for tweet in tweets:        
        ph.add_tweet(tweet)

while True:
    print('Started')
    asyncio.run(main())
    print('Finished')

