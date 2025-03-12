import chainlit as cl
import os
import re
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

from pypdf import PdfReader
import docx    # For DOCX processing

from azure.keyvault.secrets import SecretClient
from azure.identity import ClientSecretCredential
from cryptography.fernet import Fernet
import urllib.parse
from pymongo import MongoClient

# Import your system prompt
from utils.prompt_generate import USER_INPUT, USER_SELECTION_MSG, CONTENT_GEN_SYS_PROMPT, REFINE_SYS_PROMPT

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

azure_chat_model_name_mini = get_secret_value("azure-openai-4o-mini-global", client)
azure_chat_model_name = get_secret_value("azure-openai-4o-global", client)
azure_embeddings_model_name = get_secret_value("azure-openai-embedding-small", client)
openai_api_version = get_secret_value("azure-openai-api-version", client)
azure_openai_endpoint= get_secret_value("azure-openai-endpoint", client)
azure_openai_api_key = get_secret_value("azure-openai-api-key", client)

# MongoDB connection
server = get_secret_value("mongodb-url", client)
username = get_secret_value("mongodb-user", client)
password = get_secret_value("mongodb-pass", client)

CONNECTION_STRING = "mongodb+srv://"+urllib.parse.quote_plus(username)+":" + urllib.parse.quote_plus(password) + f"@{server}/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
# Connect to Azure Cosmos MongoDB
client = MongoClient(CONNECTION_STRING)

db = client["AIContentGenApp"]
collection = db["Users"]


# Load JSON from file
def load_questions(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_pdf(file) -> str:
    """
    Extract text from a PDF file.

    Args:
        file: A file-like object containing PDF data.

    Returns:
        str: The extracted text.
    """
    reader = PdfReader(file)
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
def rx_content_creator(sys_msg: str = CONTENT_GEN_SYS_PROMPT):
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    llm = AzureChatOpenAI(model=azure_chat_model_name, temperature=0.5, api_key=azure_openai_api_key, api_version=openai_api_version, azure_endpoint=azure_openai_endpoint)
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser
    return chain

@cl.cache
def rx_copywriter(sys_msg: str = REFINE_SYS_PROMPT):

    
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    llm = AzureChatOpenAI(model=azure_chat_model_name, temperature=0, api_key=azure_openai_api_key, api_version=openai_api_version, azure_endpoint=azure_openai_endpoint)
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
async def chat_profile(current_user: cl.User):
    user_role = current_user.metadata.get("role")
    print(f"User role: {user_role}")
    return [
        cl.ChatProfile(
            name="Content Creation",
            markdown_description="Generate content for Riyadh Air.",
            icon="/public/create_2.svg",
        ),
        cl.ChatProfile(
            name="Content Refinement",
            markdown_description="Refine existing content for Riyadh Air.",
            icon="/public/refine_3.svg",
            starters=[
                cl.Starter(
                    label="Usage Instructions",
                    message="How can I use this tool?",
                    icon="/public/help.svg",
                ),
            ]
        )
    ]

@cl.on_chat_start
async def on_chat_start():
    chat_profile = cl.user_session.get("chat_profile")
    if chat_profile == "Content Creation":
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
                    timeout=120,
                    raise_on_timeout=True
                ).send()

                if res and res.get("payload"):
                    selected_value = res["payload"].get("value")
                    # If the user selects "Other (Enter your own)", ask for input
                    if selected_value == "Other (Enter your own)":
                        res = await cl.AskUserMessage(
                            content=f"{question}\nPlease type your answer in the chat box below.",
                            timeout=120,
                            raise_on_timeout=True
                        ).send()
                        selected_value = res["output"]

                    # If the user selects "Skip", do not store a response
                    if selected_value == "Skip⏩":
                        continue

                    abbrev = details.get("abbrev")
                    user_responses[abbrev] = selected_value

            # Function to filter and fill template lines only if all placeholders exist
            def fill_template(template_lines, responses):
                filled_lines = []
                for line in template_lines:
                    # Find placeholders in the line
                    placeholders = re.findall(r"\{(.*?)\}", line)
                    # Only include the line if every placeholder is present in responses
                    if all(placeholder in responses for placeholder in placeholders):
                        filled_lines.append(line.format(**responses))
                return "\n".join(filled_lines)

            # Build the final prompt template and user selection messages
            filled_prompt = fill_template(USER_INPUT["content_gen_prompt"], user_responses)
            filled_user_selections = fill_template(USER_SELECTION_MSG["selections"], user_responses)
        
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
            msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")
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
    
    elif chat_profile == "Content Refinement":
        rx_copywrite = rx_copywriter()
        cl.user_session.set("rx_copywriter", rx_copywrite)
        chat_history_copywriter = []
        cl.user_session.set("chat_history_copywriter", chat_history_copywriter)

@cl.on_message
async def on_message(message: cl.Message):
    chat_profile = cl.user_session.get("chat_profile")
    user_msg = message.content
    
    if chat_profile == "Content Creation":
        rx_content_create = cl.user_session.get("rx_content_creator")
        chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
        if len(chat_history_content_creator) == 0:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return
        query = {"chat_history": chat_history_content_creator, "input": user_msg}
        config = {"configurable": {"thread_id": message.thread_id}}
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")
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
    
    elif chat_profile == "Content Refinement":

        rx_copywriter = cl.user_session.get("rx_copywriter")
        chat_history_copywriter = cl.user_session.get("chat_history_copywriter")
        config = {"configurable": {"thread_id": message.thread_id}}
        msg_copywriter = cl.Message(content="", author="Riyadh Air AI Web Research")
        max_retries = 3
        if message.elements:
            print('element detected')
            if message.elements[0].name.endswith('.docx'):
            #if "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in message.elements[0].mime:
                file_element = message.elements[0]
                path = file_element.path
                doc_content = read_docx(path)
                user_msg = (
                        f"{user_msg}:\n\nThe following is content from an attached word document, use it to "
                        f"supplement your answer:\n\n{doc_content}"
                    )
            elif message.elements[0].name.endswith('.pdf'):
                file_element = message.elements[0]
                path = file_element.path
                doc_content = read_pdf(path)
                user_msg = (
                        f"{user_msg}:\n\nThe following is content from an attached PDF document, use it to "
                        f"supplement your answer:\n\n{doc_content}"
                    )
        print(user_msg)
        query = {"chat_history": chat_history_copywriter, "input": user_msg}
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_copywriter.astream(
                    query,
                    config=config
                ):
                    await msg_copywriter.stream_token(chunk)
                    full_msg += chunk

                chat_history_copywriter.append(HumanMessage(content=user_msg))
                chat_history_copywriter.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_copywriter", chat_history_copywriter)
                await msg_copywriter.send()
                return

            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")