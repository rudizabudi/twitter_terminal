
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from httpx import ConnectError
from os import getenv
from time import sleep
from twikit import Client, Tweet

from posthandler import PostHandler

load_dotenv('.env')

USERNAME: str = getenv('USERNAME')
EMAIL: str = getenv('EMAIL')
PASSWORD: str = getenv('PASSWORD')
TWITTER_IDS: dict[str, str] = getenv('twitter_ids').split(',')

client: Client = Client('en-US')
post_handler: PostHandler = PostHandler()

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




