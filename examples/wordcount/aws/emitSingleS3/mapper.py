from user_map import user_map
import mapreduce as mr

def lambda_handler(event, context):
    text = event['text']
    bucket = event['destination']

    mr.destinationBucket = bucket

    user_map(text)

    return {
        "bucket": mr.destinationBucket,
        "numReducer": mr.numReducer
    }

if __name__ == '__main__':
    event={'text': """Autocorrect can go straight to he’ll Autocorrect can go straight to he’ll 
    Q: Why did the computer show up at work late? A: It had a hard drive. 
    I saw a driver texting and driving. It made me so mad I threw my beer at him. 
    You know you're texting too much when you say LOL in real life, instead of just laughing. 
    Instagram is just Twitter for people who go outside. 
    I can still remember a time when I knew more than my phone. 
    """,
    'destination': 'mybucket'}
    lambda_handler(event, None)