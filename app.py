import chainlit as cl
import os
import json
import logging
import uuid

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from langchain.tools import StructuredTool
from langchain_openai import AzureChatOpenAI
import tiktoken
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

import PyPDF2  # For PDF processing
import docx    # For DOCX processing

from azure.keyvault.secrets import SecretClient
from azure.identity import ClientSecretCredential
from cryptography.fernet import Fernet
import urllib.parse
from pymongo import MongoClient

# Import your system prompt
from utils.prompt_generate import SYSTEM_PROMPT_GENERATE, USER_INPUT, USER_SELECTION_MSG, NEW_SYS_PROMPT, NEW_SYS_PROMPT_TWO

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')

# Load environment variables
load_dotenv(override=True)
en_tenant_id = os.getenv('OAUTH_AZURE_AD_TENANT_ID')
en_client_id = os.getenv('SP_CLIENT_ID')
en_client_secret = os.getenv('SP_CLIENT_SECRET')

def init_key_vault_client(tenant_id, en_client_id, en_client_secret):
    
    fernet = Fernet(os.getenv('ENCRYPTION_KEY'))

    client_id = fernet.decrypt(en_client_id).decode("utf-8")
    client_secret = fernet.decrypt(en_client_secret).decode("utf-8")

    key_vault_name = os.getenv('KEYVAULT_NAME')
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    return client

def get_secret_value(secretName, client):

    retrieved_secret = client.get_secret(secretName)
    return retrieved_secret.value

client = init_key_vault_client(en_tenant_id, en_client_id, en_client_secret)

azure_chat_model_name_mini = get_secret_value("AZURE-CHAT-MODEL-NAME-PROD-MINI-GLOBAL", client)
azure_chat_model_name = get_secret_value("AZURE-CHAT-MODEL-NAME-PROD", client)
azure_embeddings_model_name = get_secret_value("AZURE-EMBEDDINGS-MODEL-NAME-PROD", client)
openai_api_version = get_secret_value("OPENAI-API-VERSION", client)
azure_openai_endpoint= get_secret_value("AZURE-OPENAI-ENDPOINT-PROD", client)
azure_openai_api_key = get_secret_value("AZURE-OPENAI-API-KEY-PROD", client)
server = get_secret_value("mongodb-url", client)
username = get_secret_value("mongodb-user", client)
password = get_secret_value("mongodb-pass", client)

CONNECTION_STRING = "mongodb+srv://"+urllib.parse.quote_plus(username)+":" + urllib.parse.quote_plus(password) + f"@{server}/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
# Connect to Azure Cosmos MongoDB
client = MongoClient(CONNECTION_STRING)

db = client["AIPolicyApps"]
collection = db["Users"]


# Load JSON from file
def load_questions(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

def read_pdf(file) -> str:
    """
    Extract text from a PDF file.

    Args:
        file: A file-like object containing PDF data.

    Returns:
        str: The extracted text.
    """
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page_num in range(len(reader.pages)):
        text += reader.pages[page_num].extract_text()
    return text


def read_docx(file) -> str:
    """
    Extract text from a DOCX file.

    Args:
        file: A file-like object containing DOCX data.

    Returns:
        str: The extracted text.
    """
    doc = docx.Document(file)
    full_text = []
    for element in doc.element.body:
        if element.tag.endswith('p'):
            p = docx.text.paragraph.Paragraph(element, doc)
            full_text.append(p.text)
        elif element.tag.endswith('tbl'):
            table = docx.table.Table(element, doc)
            table_text = []
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells]
                table_text.append(" | ".join(row_text))
            full_text.append("\n".join(table_text))
    return "\n".join(full_text)

def num_tokens(text: str, model: str = 'gpt-4o-mini') -> int:
    """
    Return the number of tokens in a given text for a specified model.

    Args:
        text (str): The input text to count tokens for.
        model (str): The model for which tokenization is done.

    Returns:
        int: The number of tokens in the text.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback if model not recognized
        encoding = tiktoken.get_encoding('cl100k_base')
    return len(encoding.encode(text))


@cl.cache
def rx_content_creator(sys_msg: str = NEW_SYS_PROMPT_TWO):
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    llm = AzureChatOpenAI(model=azure_chat_model_name_mini, temperature=1, api_key=azure_openai_api_key, api_version=openai_api_version, azure_endpoint=azure_openai_endpoint)
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser
    return chain

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Authenticate user based on credentials stored in MongoDB."""

    user = collection.find_one({"username": username})  # Fetch user from DB

    if user and user["password"] == password:
        return cl.User(
            identifier=username,
            metadata={
                "role": user["role"],
                "provider": user["provider"]
            }
        )
    return None
    
@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="RX Content Creator",
            markdown_description="The underlying LLM model is **GPT-3.5**.",
            #icon="https://picsum.photos/200",
        )
    ]

@cl.on_chat_start
async def on_chat_start():
    chat_profile = cl.user_session.get("chat_profile")
    if chat_profile == "RX Content Creator":
        questions = load_questions("utils/questions_generate.json")
        rx_content_create = rx_content_creator()
        cl.user_session.set("rx_content_creator", rx_content_create)
        chat_history_content_creator = []
        cl.user_session.set("chat_history_content_creator", chat_history_content_creator)

        try:
            user_responses = {}  # To store all user responses
            for question, details in questions.items():
                actions = [
                    cl.Action(
                        name=value,
                        payload={"value": value},
                        label=value
                    ) for value in details['value']
                ]

                res = await cl.AskActionMessage(
                    content=question,
                    actions=actions,
                    timeout=300,
                    raise_on_timeout=True
                ).send()

                if res and res.get("payload"):
                    if res["payload"].get("value") == "Other (Enter your own)":
                        res = await cl.AskUserMessage(
                            content=f"{question}\nPlease type your answer in the chat box below.",
                            timeout=300,
                            raise_on_timeout=True
                        ).send()
                        selected_value = res["output"]
                    else:
                        selected_value = res["payload"].get("value")
                    abbrev = details.get("abbrev")
                    user_responses[abbrev] = selected_value

            # Send all collected responses to the user or save them
            #await cl.Message(content=f"Responses collected: {user_responses}").send()
            prompt_template = "\n".join(USER_INPUT["content_gen_prompt"])
            user_selections = "\n".join(USER_SELECTION_MSG["selections"])
        
            # Use string formatting with the responses collected
            filled_prompt = prompt_template.format(
                content_purpose=user_responses.get("content_purpose", "N/A"),
                target_audience=user_responses.get("target_audience", "N/A"),
                key_message=user_responses.get("key_message", "N/A"),
                content_platform=user_responses.get("content_platform", "N/A"),
                content_length=user_responses.get("content_length", "N/A")
            )
            filled_user_selections = user_selections.format(
                content_purpose=user_responses.get("content_purpose", "N/A"),
                target_audience=user_responses.get("target_audience", "N/A"),
                key_message=user_responses.get("key_message", "N/A"),
                content_platform=user_responses.get("content_platform", "N/A"),
                content_length=user_responses.get("content_length", "N/A")
            )
            #await cl.Message(content=filled_prompt).send()
            cl.user_session.set("filled_prompt", filled_prompt)
            res = await cl.AskActionMessage(
                content=filled_user_selections,
                actions=[
                    cl.Action(
                        name="Yes",
                        payload={"value": "Yes"},
                        label="✅ Yes"
                    ),
                    cl.Action(
                        name="No",
                        payload={"value": "No"},
                        label="❌ No"
                    )
                ]
            ).send()
        except Exception as e:
            logging.error(f"Timed out, responses not entered in time. Error: {e}...")
            await cl.Message(content="Timed out, responses not entered in time. Please start a new chat.").send()
            return

        max_retries = 3
        if res and res.get("payload").get("value") == "Yes":
            query = {"chat_history": chat_history_content_creator, "input": filled_prompt}
            config = {"configurable": {"thread_id": "rx_contentgen"}}
            msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research", id=str(uuid.uuid4()))
            for attempt in range(max_retries):
                try:
                    full_msg = ""
                    async for chunk in rx_content_create.astream(
                        query,
                        config=config
                    ):
                        await msg_contentgen.stream_token(chunk)
                        full_msg += chunk

                    chat_history_content_creator.append(HumanMessage(content=filled_prompt))
                    chat_history_content_creator.append(AIMessage(content=full_msg))
                    cl.user_session.set("chat_history_content_creator", chat_history_content_creator)
                    await msg_contentgen.send()
                    return

                except Exception as e:
                    logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")
        else:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return

@cl.on_message
async def on_message(message: cl.Message):
    chat_profile = cl.user_session.get("chat_profile")
    user_msg = message.content
    
    if chat_profile == "RX Content Creator":
        rx_content_create = cl.user_session.get("rx_content_creator")
        chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
        if len(chat_history_content_creator) == 0:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return
        query = {"chat_history": chat_history_content_creator, "input": user_msg}
        config = {"configurable": {"thread_id": "rx_contentgen"}}
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research", id=str(uuid.uuid4()))
        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_content_create.astream(
                    query,
                    config=config
                ):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                chat_history_content_creator.append(HumanMessage(content=user_msg))
                chat_history_content_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_content_creator", chat_history_content_creator)
                await msg_contentgen.send()
                return

            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")