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

config = load_config(config_file_path)
reversed_dft = {v: k for k, v in DiscordFilterType._member_map_.items()}

for webhook_data in config['webhooks'].values():
    for webhook in webhook_data:
        webhook['filter']['filter_type'] = DiscordFilterType[reversed_dft[webhook['filter']['filter_type']]]
        webhook['filter']['filter_data'] = webhook['filter']['filter_data'].split(',')

INTERVAL: int = 15 # modulo update interval in mins
UPDATE_OFFSET: int = 20 # offset to update point in secs

post_handler: PostHandler = PostHandler()

async def main():
    env_update_hour: int = -1 # update twitter settings on each hour change

    i: int = 0
    while True:
        try:
            config = None
            try:
                with open(config_file_path, 'r') as f:
                    config = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError('Config file not found. Please create a config.json file.')

            accounts = {i: v for i, v in enumerate(config['x_accounts'].values())}

            if i == len(accounts.keys()):
                i = 0

            username: str = accounts[i]['username']  # twitter
            email: str = accounts[i]['email']  # twitter
            password: str = accounts[i]['password']  # twitter
            cookies_file: str = os.path.join(os.path.dirname(__file__), f'{accounts[i]['username']}.json')
            client: Client = Client('en-US')

            twitter_ids: list[str] = list(config['x_ids'].values())  # get from here https://ilo.so/twitter-id/
            mirror_discord: bool = config['use_discord']  # discord mirror switch
            webhooks: dict[str: dict[str: str | dict[str, str]]] = config['webhooks']

            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password,
                cookies_file=cookies_file)

            if datetime.now().hour != env_update_hour or not any([twitter_ids, mirror_discord, webhooks]):
                env_update_hour = datetime.now().hour

                post_handler.set_discord_settings(mirroring=mirror_discord, webhooks=webhooks)

            j: int = 0
            while j < len(twitter_ids):
                try:
                    await ask_tweets(client=client, twitter_id=twitter_ids[i], ph=post_handler)
                    sleep(5)
                    j += 1
                except ConnectError:
                    pass

            j = 0
            post_handler.process_msgs()

        except (AccountSuspended, ConnectTimeout, Forbidden, ReadTimeout, TooManyRequests) as e:
            print(f'Error occurred with account {accounts[i]}. Sleeping for 600 seconds. {e}')

        except Unauthorized:
            cookies_path = os.path.join(os.path.dirname(__file__), cookies_file)
            os.remove(cookies_path)

        except Exception as e:
            print(f'Not handled error with account {accounts[i]}: {e}')

        next_update = datetime.now()
        for min in range(1, INTERVAL + 1):
            next_update = datetime.now() + timedelta(minutes=min)
            if next_update.minute % INTERVAL == 0:
                break

        next_update = next_update.replace(second=UPDATE_OFFSET, microsecond=0)

        wait_time = next_update - datetime.now()
        sleep(wait_time.seconds)

        i += 1

async def ask_tweets(client: Client, twitter_id: str, ph: PostHandler):
    tweets: list[Tweet] = await client.get_user_tweets(user_id=twitter_id, tweet_type='Tweets', count=10)

    for tweet in tweets:        
        ph.add_tweet(tweet)

while True:
    print('Started')
    asyncio.run(main())
    print('Finished')

