import boto3

def lambda_handler(event, context):
    client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
    return {
        "boto3_version": boto3.__version__,
        "has_agentic_api": hasattr(client, "agentic_retrieve_stream"),
    }