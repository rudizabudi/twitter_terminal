from ast import literal_eval
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from httpx import ConnectError
from os import getenv
from time import sleep
from twikit import Client, Tweet

from posthandler import PostHandler

if getenv('DEV_VAR') == 'rudizabudi':
    load_dotenv('.env.dev')
else:
    load_dotenv('.env')

USERNAME: str = getenv('USERNAME')
EMAIL: str = getenv('EMAIL')
PASSWORD: str = getenv('PASSWORD')
TWITTER_IDS: dict[str, str] = getenv('twitter_ids').split(',')

MIRROR_DISCORD: bool = bool(getenv('MIRROR_DISCORD'))
webhooks: dict[str: list[str]] = literal_eval(getenv('WEBHOOKS'))

client: Client = Client('en-US')
post_handler: PostHandler = PostHandler(mirror_discord=MIRROR_DISCORD, webhooks=webhooks)

async def main():
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
        post_handler.process_tweets()
        sleep(60)        

async def ask_tweets(twitter_id: str, ph: PostHandler):
    tweets: list[Tweet] = await client.get_user_tweets(user_id=twitter_id, tweet_type='Tweets', count=20)
    for tweet in tweets:
        ph.add_tweet(tweet)


asyncio.run(main())




