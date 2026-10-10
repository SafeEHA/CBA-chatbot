import os, json, re, boto3
from botocore.eventstream import EventStream

REGION = os.environ.get("AWS_REGION", "us-east-1")
KB_ID = os.environ["KB_ID"]
GR_ID = os.environ.get("GUARDRAIL_ID")
GR_VER = os.environ.get("GUARDRAIL_VERSION", "DRAFT")
MODEL_ARN = os.environ.get("MODEL_ARN")

client = boto3.client("bedrock-agent-runtime", region_name=REGION)

def reply(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }

def ask(question):
    params = {
        "messages": [{"role": "user", "content": {"text": (
    "Answer only using facts and figures stated explicitly in the sources. "
    "Never calculate or infer totals or prices. If a figure is not stated, say so "
    "and direct the user to https://www.cloudboosta.com/enroll/ or the Academy WhatsApp advisor. "
    "Do not state enrollment deadlines or seat counts. Question: " + question
)}}],
        "retrievers": [{
            "description": "CloudBoosta website content: courses, training, enrollment and services",
            "configuration": {"knowledgeBase": {"knowledgeBaseId": KB_ID}},
        }],
        "agenticRetrieveConfiguration": {
            "foundationModelType": "MANAGED",
            "rerankingModelType": "MANAGED",
        },
        "generateResponse": True,
    }
    if GR_ID:
        params["policyConfiguration"] = {
            "bedrockGuardrailConfiguration": {
                "guardrailId": GR_ID,
                "guardrailVersion": GR_VER,
            }
        }

    response = client.agentic_retrieve_stream(**params)
    stream = next((v for v in response.values() if isinstance(v, EventStream)), None)

    final_answer, parts = None, []
    for e in stream:
        if "responseEvent" in e:
            parts.append(e["responseEvent"].get("text", ""))
        elif "result" in e:
            final_answer = e["result"].get("generatedResponse", {}).get("answer")

    text = final_answer or "".join(parts)
    return re.sub(r"\s*(?:\[\d+\])+", "", text).strip()

def lambda_handler(event, context):
    body = event
    if isinstance(event.get("body"), str):
        try:
            body = json.loads(event["body"])
        except ValueError:
            body = {}

    question = (body.get("question") or "").strip()
    if not question:
        return reply(400, {"error": "Please include a question."})
    if len(question) > 1000:
        return reply(400, {"error": "Question is too long."})

    try:
        return reply(200, {"answer": ask(question)})
    except Exception as ex:
        print("ERROR:", repr(ex))
        return reply(500, {"error": "Something went wrong. Please try again."})