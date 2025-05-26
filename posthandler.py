from datetime import datetime
from enum import StrEnum
import html
import pytz
import requests
from time import sleep
from twikit import Tweet

class PostHandler:
    def __init__(self) -> None:
        self.new_tweets: list[None | Tweet] = []
        self.post_queue: list[None | Tweet] = []
        self.posted_tweets: list[None | Tweet] = []

        self.first_run: bool = True

    def set_discord_settings(self, mirroring: bool = False, webhooks: dict[str: list[str]] = None):
        self.mirror_discord = mirroring
        if self.mirror_discord and webhooks is None:
            raise ValueError('Discord webhook URL required for mirroring')
    
        """ self.default_webhooks: dict[str: dict[str: list[str]]] = {k: v for k, v in webhooks.items() if v['filter'] == '*'}
        if len(self.default_webhooks) != 1:
            raise ImportError('Exactly one default/catch-all webhook required') """
        
        """ self.default_webhooks: list[str] = self.default_webhooks[list(self.default_webhooks.keys())[0]]['urls']
        self.rest_webhooks: dict[str: dict[str: list[str]]]= {k: v for k, v in webhooks.items() if v['filter']!= '*'}   
        """

        self.webhooks = webhooks

    def add_tweet(self, tweet: Tweet) -> None:
        self.new_tweets.append(tweet)
    
    def process_msgs(self) -> None:
        print(f'{len(self.new_tweets)=}')
        while self.new_tweets:
            if self.new_tweets[-1] not in self.posted_tweets:
                self.post_queue.append(self.new_tweets[-1])
            self.new_tweets.pop(-1)
        print(f'{len(self.post_queue)=}')

        self.sort_tweets()

        print(f'{self.posted_tweets=}')
        print(f'{self.post_queue=}')
        for post in self.post_queue:
            post_name: str = get_name(post)
            #post_text: str = html.unescape(post.text)
            post_text: str = html.unescape(post.full_text) # 'Show more' text

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
        self.post_queue = sorted(self.post_queue, key = lambda tweet: datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y'))

    @staticmethod
    def terminal_post_tweet(post_string) -> None:
        print(post_string)
        print('\n')

    def get_webhook_old(self, post_string: str) -> list[str]:
        webhooks: list[str] = None
        for v in self.rest_webhooks.values():
            if isinstance(v['filter'], list):
                for filter_word in v['filter']:
                    if filter_word in post_string:
                        webhooks = v['urls']
                        break
            elif isinstance(v['filter'], str):
                if v['filter'] in post_string:
                    webhooks = v['urls']
                    break
            else:
                raise TypeError('Filter must be str or list')

        if webhooks is None:
            webhooks = self.default_webhooks

        return webhooks
    
    def get_webhooks(self, post_data: dict[str, str]) -> str:

        post_webhooks: list[str] = []
        for server, webhooks in self.webhooks.items():
            post_webhook: str = None
            catch_all_webhook = list(filter(lambda x: x['filter']['filter_type'] == DiscordFilterType.CATCH_ALL, webhooks))

            for webhook_data in webhooks:
                filter_type: DiscordFilterType = webhook_data['filter']['filter_type']

                if filter_type == DiscordFilterType.FILTER_NAME:
                    filter_data: str | list[str] = webhook_data['filter']['filter_data']
                    if isinstance(filter_data, str):
                        filter_data = filter_data.split(',')
                elif filter_type == DiscordFilterType.FILTER_TEXT:
                    filter_data: str | list[str] = webhook_data['filter']['filter_data']
                    if isinstance(filter_data, str):
                        filter_data = filter_data.split(',')
               
                match filter_type:
                    case DiscordFilterType.FILTER_NAME:
                        if any([filter_word in post_data['username'] for filter_word in filter_data]):
                            post_webhook = webhook_data['webhook']
                    case DiscordFilterType.FILTER_TEXT:
                        if any([filter_word in post_data['content'] for filter_word in filter_data]):
                            post_webhook = webhook_data['webhook']

            if post_webhook is None and len(catch_all_webhook) > 0:
                post_webhook = catch_all_webhook[0]['webhook']

            if post_webhook is not None:
                post_webhooks.append(post_webhook)

        return post_webhooks


    def discord_post_tweet(self, post_string, twitterer='Alfred der Botler', avatar = '') -> None:
        data: dict[str: str] = {'content': post_string,
                                'username': twitterer,
                                'avatar_url': avatar} 


        i: int = 0
        webhooks: list[str] = self.get_webhooks(post_data = data)
        print(f'Length webhooks: {len(webhooks)}.')
        while i != len(webhooks):
            while True:
                response: requests.models.Response = requests.post(webhooks[i], json = data)

                #Response codes: https://discord.com/developers/docs/topics/opcodes-and-status-codes#http
                if response.status_code == 429: # 429 (TOO MANY REQUESTS)	
                    sleep(30)
                else:
                    if response.status_code not in (200, 204): # (200 (OK), 204 (NO CONTENT))
                        print(f'Discord webhook returned status code {response.status_code}')
                        print(f'DEBUG: Json request data: {data}')
                    i += 1
                    break # sucessfully sent
        
def get_post_time(tweet: Tweet, output_format: str = '%d%b%y %H:%M', output_timezone: pytz.timezone = pytz.timezone('Europe/Berlin')) -> str:
    #output_format: str = '%H:%M %Z %d%b%y'
    creation_time: datetime = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y').astimezone(output_timezone)
    return creation_time.strftime(output_format)

def get_name(tweet: Tweet) -> str:
    return tweet._data['core']['user_results']['result']['legacy']['name']

def get_profile_image(tweet: Tweet) -> str:
    return tweet._data['core']['user_results']['result']['legacy']['profile_image_url_https']

class DiscordFilterType(StrEnum):
    FILTER_NAME: str = 'filter_name'
    FILTER_TEXT: str = 'filter_text'
    CATCH_ALL: str = 'catch_all'


