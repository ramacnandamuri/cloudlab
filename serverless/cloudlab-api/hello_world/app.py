import json
import boto3
import uuid
import os
from datetime import datetime

# DynamoDB connection
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def create_item(event, context):
    """Create a new item"""
    try:
        body = json.loads(event['body'])
        item = {
            'id': str(uuid.uuid4()),
            'name': body['name'],
            'description': body.get('description', ''),
            'created_at': datetime.now().isoformat()
        }
        table.put_item(Item=item)
        return {
            'statusCode': 201,
            'body': json.dumps(item)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def list_items(event, context):
    """List all items"""
    try:
        result = table.scan()
        return {
            'statusCode': 200,
            'body': json.dumps(result['Items'])
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_item(event, context):
    """Get a single item by ID"""
    try:
        item_id = event['pathParameters']['id']
        result = table.get_item(Key={'id': item_id})
        if 'Item' not in result:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Item not found'})
            }
        return {
            'statusCode': 200,
            'body': json.dumps(result['Item'])
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }