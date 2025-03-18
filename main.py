from ast import literal_eval
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from httpx import ConnectError, ConnectTimeout, ReadTimeout
from os import getenv
from time import sleep
from twikit import Client, Tweet
from twikit.errors import TooManyRequests, AccountSuspended

from posthandler import PostHandler

if getenv('DEV_VAR') == 'rudizabudi':
    print('DEV MODE')
    load_dotenv('.env.dev')
else:
    load_dotenv('.env')

INTERVAL: int = 15 #modulo update intervall in mins
UPDATE_OFFSET: int = 20 #offset to update point in secs

USERNAME: str = getenv('USERNAME') #twitter
EMAIL: str = getenv('EMAIL') #twitter
PASSWORD: str = getenv('PASSWORD') #twitter
TWITTER_IDS: dict[str, str] = getenv('twitter_ids').split(',') #get from here https://ilo.so/twitter-id/

MIRROR_DISCORD: bool = bool(getenv('MIRROR_DISCORD')) #discord mirror switch
webhooks: dict[str: list[str]] = literal_eval(getenv('WEBHOOKS'))

client: Client = Client('en-US')
post_handler: PostHandler = PostHandler(mirror_discord=MIRROR_DISCORD, webhooks=webhooks)

async def main():
    try:
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD,
            cookies_file='cookies.json')

        i: int = 0
        while True:
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

    except (TooManyRequests, ConnectTimeout, ReadTimeout, AccountSuspended) as e:
        print(f'Error occured. Sleeping for 600 seconds. {e}')
        sleep(600)
        await main()        

async def ask_tweets(twitter_id: str, ph: PostHandler):
    tweets: list[Tweet] = await client.get_user_tweets(user_id=twitter_id, tweet_type='Tweets', count=10)
    for tweet in tweets:
        ph.add_tweet(tweet)


asyncio.run(main())




