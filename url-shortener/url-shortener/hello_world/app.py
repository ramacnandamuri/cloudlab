import json
import boto3
import os
import string
import random
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def generate_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def get_base_url(event):
    """Construct base URL from the incoming request"""
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    return f"https://{domain}/{stage}"

def create_short_url(event, context):
    try:
        body = json.loads(event['body'])
        long_url = body.get('url')

        if not long_url:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'url is required'})
            }

        # Check if URL already exists
        existing = table.scan(
            FilterExpression='long_url = :url',
            ExpressionAttributeValues={':url': long_url}
        )

        if existing['Items']:
            existing_code = existing['Items'][0]['code']
            base_url = get_base_url(event)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'short_url': f"{base_url}/{existing_code}",
                    'long_url': long_url,
                    'code': existing_code,
                    'existing': True
                })
            }

        # Generate new code
        code = generate_code()

        table.put_item(Item={
            'code': code,
            'long_url': long_url,
            'created_at': datetime.now().isoformat(),
            'clicks': 0
        })

        base_url = get_base_url(event)
        short_url = f"{base_url}/{code}"

        return {
            'statusCode': 201,
            'body': json.dumps({
                'short_url': short_url,
                'long_url': long_url,
                'code': code,
                'existing': False
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def redirect_url(event, context):
    """GET /{code} — redirect to the original long URL"""
    try:
        code = event['pathParameters']['code']

        # Look up code in DynamoDB
        result = table.get_item(Key={'code': code})

        if 'Item' not in result:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Short URL not found'})
            }

        long_url = result['Item']['long_url']

        # Update click count
        table.update_item(
            Key={'code': code},
            UpdateExpression='SET clicks = clicks + :val',
            ExpressionAttributeValues={':val': 1}
        )

        # Return 301 redirect
        return {
            'statusCode': 301,
            'headers': {
                'Location': long_url
            },
            'body': ''
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }