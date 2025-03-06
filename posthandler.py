from datetime import datetime
import pytz
from twikit import Tweet

class PostHandler:
    def __init__(self):
        self.new_tweets: list[None | Tweet] = []
        self.post_queue: list[None | Tweet] = []
        self.posted_tweets: list[None | Tweet] = []

    def add_tweet(self, tweet: Tweet) -> None:
        self.new_tweets.append(tweet)
    
    def process_tweets(self) -> None:
        while self.new_tweets:
            if self.new_tweets[-1] not in self.posted_tweets:
                self.post_queue.append(self.new_tweets[-1])
            self.new_tweets.pop(-1)

        self.sort_tweets()
        self.post_tweets()
    
    def sort_tweets(self) -> None:
        self.post_queue = sorted(self.post_queue, key=lambda tweet: datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y'))
    
    def post_tweets(self) -> None:
        for post in self.post_queue:
            post_name: str = get_name(post)
            
            post_string: str = f'{get_post_time(post):<12} - \033[1m{post_name:>15}\33[0m: {post.text}'
            print(post_string)
            print('\n')
        
        self.post_queue = []

def get_post_time(tweet: Tweet, output_format: str = '%d%b%y %H:%M', output_timezone: pytz.timezone = pytz.timezone('Europe/Berlin')) -> str:
    #output_format: str = '%H:%M %Z %d%b%y'
    creation_time: datetime = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y').astimezone(output_timezone)
    return creation_time.strftime(output_format)

def get_name(Tweet) -> str:
    return Tweet._data['core']['user_results']['result']['legacy']['name']

