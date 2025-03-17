from datetime import datetime
import html
import pytz
import requests
from time import sleep
from twikit import Tweet

class PostHandler:
    def __init__(self, mirror_discord = False, webhooks = None) -> None:
        
        self.mirror_discord: bool = mirror_discord
        if self.mirror_discord and webhooks is None:
            raise ValueError('Discord webhook URL required for mirroring')
        
        self.default_webhooks: dict[str: dict[str]] = {k: v for k, v in webhooks.items() if v['filter'] == '*'}
        if len(self.default_webhooks) != 1:
            raise ImportError('Exactly one default/catch-all webhook required')
        
        self.default_webhooks: list[str] = self.default_webhooks[list(self.default_webhooks.keys())[0]]['urls']
        self.rest_webhooks = {k: v for k, v in webhooks.items() if v['filter']!= '*'}

        self.new_tweets: list[None | Tweet] = []
        self.post_queue: list[None | Tweet] = []
        self.posted_tweets: list[None | Tweet] = []

        self.first_run: bool = True

    def add_tweet(self, tweet: Tweet) -> None:
        self.new_tweets.append(tweet)
    
    def process_msgs(self) -> None:
        while self.new_tweets:
            if self.new_tweets[-1] not in self.posted_tweets:
                self.post_queue.append(self.new_tweets[-1])
            self.new_tweets.pop(-1)

        self.sort_tweets()
        for post in self.post_queue:
            post_name: str = get_name(post)
            post_text: str = html.unescape(post.text)

            terminal_post_string: str = f'{get_post_time(post):<12} - \033[1m{post_name:>15}\33[0m: {post_text}'

            self.terminal_post_tweet(post_string = terminal_post_string)

            if self.mirror_discord and (self.first_run and post == self.post_queue[-1] or not self.first_run):
                #discord_post_string: str = f'{get_post_time(post):<12} - **{post_name:>15}** : {post_text}'
                discord_post_string: str = f'{get_post_time(post):<12} : {post_text}'
                discord_avatar: str = get_profile_image(post)
                self.discord_post_tweet(post_string = discord_post_string, twitterer = post_name, avatar = discord_avatar)
            
            self.posted_tweets.append(post)
        
        self.first_run = False
        self.post_queue = []
    
    def sort_tweets(self) -> None:
        self.post_queue = sorted(self.post_queue, key=lambda tweet: datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y'))
    
    def terminal_post_tweet(self, post_string) -> None:
        print(post_string)
        print('\n')

    def discord_post_tweet(self, post_string, twitterer='Alfred der Botler', avatar = '') -> None:
        data: dict[str: str] = {'content': post_string,
                                 'username': twitterer,
                                 'avatar_url': avatar} 
        
        for _, v in self.rest_webhooks.items():
            if v['filter'] in post_string:
                webhooks = v['urls']
                break
        else:
            webhooks = self.default_webhooks
        
        i: int = 0
        while i != len(webhooks):
            response: requests.models.response = requests.post(webhooks[i], json=data)

            if response.status_code == 429:
                sleep(30)
            elif response.status_code not in (200, 204):
                raise Warning(f'Discord webhook returned status code {response.status_code}')
            else:
                i += 1
        
def get_post_time(tweet: Tweet, output_format: str = '%d%b%y %H:%M', output_timezone: pytz.timezone = pytz.timezone('Europe/Berlin')) -> str:
    #output_format: str = '%H:%M %Z %d%b%y'
    creation_time: datetime = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y').astimezone(output_timezone)
    return creation_time.strftime(output_format)

def get_name(tweet: Tweet) -> str:
    return tweet._data['core']['user_results']['result']['legacy']['name']

def get_profile_image(tweet: Tweet) -> str:
    return tweet._data['core']['user_results']['result']['legacy']['profile_image_url_https']

