from ast import literal_eval
import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from httpx import ConnectError, ConnectTimeout, ReadTimeout
from itertools import cycle
import json
from os import getenv
import os
import sys
from time import sleep
import traceback
from twikit import Client, Tweet
from twikit.errors import AccountSuspended, Forbidden, TooManyRequests, Unauthorized
from twikit.utils import Result

from posthandler import PostHandler, DiscordFilterType

if getenv('DEV_VAR') == 'rudizabudi':
    print('DEV MODE')
    config_file = 'config_dev.json'
else:
    config_file = 'config.json'

config_file_path = os.path.join(os.path.dirname(__file__), config_file)

INTERVAL: int = 15 # modulo update interval in mins
UPDATE_OFFSET: int = 20 # offset to update point in secs

post_handler: PostHandler = PostHandler()
tweet_cursor: defaultdict[str, str] = defaultdict(str)


async def main():
    env_update_hour: int = -1 # update twitter settings on each hour change

    def get_clients() -> dict[int, dict[str, str | Client]]:

        clients: dict[int, dict[str, str | Client]] = {}
        for i, v in enumerate(config['x_accounts'].values()):
            clients[i] = {
                'username': v['username'],
                'email': v['email'],
                'password': v['password'],
                'cookies_file': os.path.join(os.path.dirname(__file__), f'{v['username']}.json'),
                'client': Client('en-US')
            }

        return clients

    client_counter: int = 0
    while True:
        config = None
        try:
            with open(config_file_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError('Config file not found. Please create a config.json file.')


        twitter_ids: list[str] = list(config['x_ids'].values())  # get from here https://ilo.so/twitter-id/
        mirror_discord: bool = config['use_discord']  # discord mirror switch
        webhooks: dict[str: dict[str: str | dict[str, str]]] = config['webhooks']

        reversed_dft = {v: k for k, v in DiscordFilterType._member_map_.items()}

        for webhook_data in webhooks.values():
            for webhook in webhook_data:
                if not isinstance(webhook['filter']['filter_type'], DiscordFilterType):
                    webhook['filter']['filter_type'] = DiscordFilterType[reversed_dft[webhook['filter']['filter_type']]]
                if not isinstance(webhook['filter']['filter_data'], list):
                    webhook['filter']['filter_data'] = webhook['filter']['filter_data'].split(',')

        if datetime.now().hour != env_update_hour or not any([twitter_ids, mirror_discord, webhooks]):
            env_update_hour = datetime.now().hour

            post_handler.set_discord_settings(mirroring=mirror_discord, webhooks=webhooks)

        clients = get_clients()
        feed_counter: int = 0
        while feed_counter < len(twitter_ids):
            try:
                await clients[client_counter]['client'].login(
                    auth_info_1=clients[client_counter]['username'],
                    auth_info_2=clients[client_counter]['email'],
                    password=clients[client_counter]['password'],
                    cookies_file=clients[client_counter]['cookies_file'])

                print(f'Asking tweets for ID {twitter_ids[feed_counter]} with {clients[client_counter]['username']}.')
                await ask_tweets(client=clients[client_counter]['client'], twitter_id=twitter_ids[feed_counter], ph=post_handler)
                feed_counter += 1

            except ConnectError:
                print('Connect error, retrying...')

            except (AccountSuspended, ConnectTimeout, Forbidden, ReadTimeout, TooManyRequests) as e:
                print(f'Error occurred with account {clients[client_counter]['username']}: {e}')

            except Unauthorized as e:
                print(f'Not authorized with account {clients[client_counter]['username']}: {e}')
                cookies_path = os.path.join(os.path.dirname(__file__), clients[client_counter]['cookies_file'])
                os.remove(cookies_path)

            except Exception as e:
                print(f'Lazily handled error occurred with account {clients[client_counter]['username']}: {e}')
                traceback.print_exc(file=sys.stdout)

            sleep(5)

            if client_counter == len(clients.keys()) - 1:
                client_counter = 0
            else:
                client_counter += 1

        post_handler.process_msgs()

        next_update = datetime.now()
        for min in range(1, INTERVAL + 1):
            next_update = datetime.now() + timedelta(minutes=min)
            if next_update.minute % INTERVAL == 0:
                break

        next_update = next_update.replace(second=UPDATE_OFFSET, microsecond=0)

        wait_time = next_update - datetime.now()
        sleep(wait_time.seconds)


async def ask_tweets(client: Client, twitter_id: str, ph: PostHandler):
    tweets: Result[Tweet] = await client.get_user_tweets(user_id=twitter_id,
                                                         tweet_type='Tweets',
                                                         count=10,
                                                         cursor=tweet_cursor.get(twitter_id, None))

    for tweet in tweets:        
        ph.add_tweet(tweet)

    tweet_cursor[twitter_id] = tweets.previous_cursor


while True:
    print('Started')
    asyncio.run(main())
    print('Finished')

