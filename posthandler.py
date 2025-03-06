from datetime import datetime
import pytz
import requests
from time import sleep
from twikit import Tweet

class PostHandler:
    def __init__(self, mirror_discord = False, discord_webhook = None) -> None:
        
        self.mirror_discord: bool = mirror_discord
        if self.mirror_discord and discord_webhook is None:
            raise ValueError('Discord webhook URL required for mirroring')
        self.discord_webhook: str = discord_webhook

        self.new_tweets: list[None | Tweet] = []
        self.post_queue: list[None | Tweet] = []
        self.posted_tweets: list[None | Tweet] = []

        self.first_run: bool = True

    def add_tweet(self, tweet: Tweet) -> None:
        self.new_tweets.append(tweet)
    
    def process_tweets(self) -> None:
        while self.new_tweets:
            if self.new_tweets[-1] not in self.posted_tweets:
                self.post_queue.append(self.new_tweets[-1])
            self.new_tweets.pop(-1)

        self.sort_tweets()
        for post in self.post_queue:
            post_name: str = get_name(post)
            
            terminal_post_string: str = f'{get_post_time(post):<12} - \033[1m{post_name:>15}\33[0m: {post.text}'

            self.terminal_post_tweet(post_string = terminal_post_string)

            if self.mirror_discord and (self.first_run and post == self.post_queue[-1] or not self.first_run):
                #discord_post_string: str = f'{get_post_time(post):<12} - **{post_name:>15}** : {post.text}'
                discord_post_string: str = f'{get_post_time(post):<12} : {post.text}'

                self.discord_post_tweet(post_string = discord_post_string, twitterer= post_name)
            
            self.posted_tweets.append(post)
        
        self.first_run = False
        self.post_queue = []
    
    def sort_tweets(self) -> None:
        self.post_queue = sorted(self.post_queue, key=lambda tweet: datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y'))
    
    def terminal_post_tweet(self, post_string) -> None:
            print(post_string)
            print('\n')

    def discord_post_tweet(self, post_string, twitterer='Alfred der Botler') -> None:
        data: dict[str, str] = {'content': post_string, 'username': twitterer} 
        response: requests.models.response = requests.post(self.discord_webhook, json=data)

        if response.status_code == 429:
            sleep(30)
            self.discord_post_tweet(post_string)
        elif response.status_code not in (200, 204):
            raise Warning(f'Discord webhook returned status code {response.status_code}')
        
def get_post_time(tweet: Tweet, output_format: str = '%d%b%y %H:%M', output_timezone: pytz.timezone = pytz.timezone('Europe/Berlin')) -> str:
    #output_format: str = '%H:%M %Z %d%b%y'
    creation_time: datetime = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y').astimezone(output_timezone)
    return creation_time.strftime(output_format)

def get_name(Tweet) -> str:
    return Tweet._data['core']['user_results']['result']['legacy']['name']

