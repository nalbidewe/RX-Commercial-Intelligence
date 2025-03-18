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
from utils.prompt_generate_lifecycle import (
    USER_INPUT_LIFECYCLE, 
    USER_SELECTION_MSG_LIFECYCLE, 
    SYSTEM_LIFECYCLE_PROMPT, 
    EMAIL_TEMPLATE
)


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

def load_questions():
    # Load questions from the JSON file.
    with open("utils/questions_generate.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = []
    for question_text, details in data.items():
        questions.append({
            "questionId": details["abbrev"],
            "question": question_text,
            "type": details["type"],      # All questions are of type "options" by default.
            "options": details["value"],
            "selected": "",
            "isOther": False              # Extra flag to track if "Other" was selected.
        })
    return questions

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

@cl.cache
def rx_lifecycle_creator():

    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{sys_msg}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    llm = AzureChatOpenAI(model=azure_chat_model_name, temperature=0.5, api_key=azure_openai_api_key, api_version=openai_api_version, azure_endpoint=azure_openai_endpoint)
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
    return [
        cl.ChatProfile(
            name="Web & App Content Creation",
            markdown_description="Generate Web & App content for Riyadh Air.",
            icon="/public/content.svg",
        ),
         cl.ChatProfile(
            name="Lifecycle Content Creation",
            markdown_description="Generate Lifecycle content for Riyadh Air.",
            icon="/public/lifecycle.svg" # cuz h.h doesn't want a symbolic 'lifestyle' butterfly
        ),
        cl.ChatProfile(
            name="Content Refinement",
            markdown_description="Refine existing content for Riyadh Air.",
            icon="/public/refine.svg",
            starters=[
                cl.Starter(
                    label="Usage Instructions",
                    message="How can I use this tool?",
                    icon="/public/help.svg",
                ),
            ]
        )
    ]

async def process_sub_questions(sub_questions_list):
    responses = {}
    for sub_question in sub_questions_list:
        actions = [
            cl.Action(name=value, payload={"value": value}, label=value)
            for value in sub_question["value"]
        ]
        res = await cl.AskActionMessage(
            content=sub_question["question"],
            actions=actions,
            timeout=300,
            raise_on_timeout=True
        ).send()
        
        if res and res.get("payload"):
            answer = res["payload"].get("value")
            if answer in ["Other (Enter your own)", "Yes, add additional info"]:
                res = await cl.AskUserMessage(
                    content=f"{sub_question['question']}\nPlease type your answer in the chat box below:",
                    timeout=300,
                    raise_on_timeout=True
                ).send()
                answer = res["output"]
            
            # Use a key for this sub-question
            key = sub_question.get("abbrev")
            responses[key] = answer
            
            # If this sub_question has further nested sub_questions, process them recursively.
            if "sub_questions" in sub_question:
                nested_responses = await process_sub_questions(sub_question["sub_questions"][answer])
                responses.update(nested_responses)
            else:
                continue
    return responses

def adjust_template(template_lines, responses):
    filled_lines = []
    for line in template_lines:
        # Find placeholders in the line
        placeholders = re.findall(r"\{(.*?)\}", line)
        # Only include the line if every placeholder is present in responses
        if all(placeholder in responses for placeholder in placeholders):
            filled_lines.append(line.format(**responses))
    return "\n".join(filled_lines)
       
@cl.on_chat_start
async def on_chat_start():
    chat_profile = cl.user_session.get("chat_profile")
    if chat_profile == "Web & App Content Creation":
        rx_content_create = rx_content_creator()
        cl.user_session.set("rx_content_creator", rx_content_create)
        chat_history_content_creator = []
        cl.user_session.set("chat_history_content_creator", chat_history_content_creator)
        # Dynamically load questions from the JSON file.
        questions = load_questions()
        # Create the custom element with the questions.
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions",
            props={"questions": questions}
        )
        form_msg = cl.Message(content="Please answer the following questions:", elements=[multi_select_element])
        cl.user_session.set("form_msg", form_msg)
        await form_msg.send()
    
    elif chat_profile == "Content Refinement":
        rx_copywrite = rx_copywriter()
        cl.user_session.set("rx_copywriter", rx_copywrite)
        chat_history_copywriter = []
        cl.user_session.set("chat_history_copywriter", chat_history_copywriter)
    
    elif chat_profile == "Lifecycle Content Creation":
        questions = load_questions("utils/question_generate_lifecycle.json")
        rx_lifecycle_create = rx_lifecycle_creator()
        cl.user_session.set("rx_lifecycle_creator", rx_lifecycle_create)
        chat_history_lifecycle_creator = []
        cl.user_session.set("chat_history_lifecycle_creator", chat_history_lifecycle_creator)

        try:
            user_responses = {}  # To store all user responses
            for details in questions['questions']:
                actions = [
                    cl.Action(
                        name=value,
                        payload={"value": value},
                        label=value
                    ) for value in details['value']
                ]

                res = await cl.AskActionMessage(
                    content=details["question"],
                    actions=actions,
                    timeout=300,
                    raise_on_timeout=True
                ).send()
                
                if res and res.get("payload"):
                    answer = res["payload"].get("value")
                    if answer in ["Other (Enter your own)", "Yes, add additional info"]:
                        res = await cl.AskUserMessage(
                            content=f'{details["question"]}\nPlease type your answer in the chat box below.',
                            timeout=300,
                            raise_on_timeout=True
                        ).send()
                        selected_value = res["output"]
                    else:
                        selected_value = res["payload"].get("value")

                    # If the user selects "Skip", do not store a response
                    if selected_value == "Skip⏩":
                        continue

                    abbrev = details.get("abbrev")
                    user_responses[abbrev] = selected_value
                
                if "sub_questions" in details:
                    sub_resp = await process_sub_questions(details["sub_questions"].get(selected_value, []))
                    user_responses.update(sub_resp)

            class DefaultDict(dict):
                def __missing__(self, key):
                    return "N/A"
                
            filled_prompt = adjust_template(USER_INPUT_LIFECYCLE["content_gen_prompt"], user_responses)
            filled_user_selections = adjust_template(USER_SELECTION_MSG_LIFECYCLE["selections"], user_responses)
        
            cl.user_session.set("filled_prompt", filled_prompt)

            email_template = EMAIL_TEMPLATE.get(user_responses.get("content_purpose", ""),  "")

            prompt_email_template = ""
            if len(email_template) > 0:
                prompt_email_template = f"\nEmail Template for {user_responses.get('content_purpose', '')}"
                prompt_email_template += "\n\n" + email_template

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
            query = {"chat_history": chat_history_lifecycle_creator,
                     "sys_msg": SYSTEM_LIFECYCLE_PROMPT + prompt_email_template,
                     "input": filled_prompt}
            config = {"configurable": {"thread_id": "rx_contentgen"}}
            msg_id = str(uuid.uuid4())
            msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research", id=msg_id)
            for attempt in range(max_retries):
                try:
                    full_msg = ""
                    async for chunk in rx_lifecycle_create.astream(
                        query,
                        config=config
                    ):
                        await msg_contentgen.stream_token(chunk)
                        full_msg += chunk

                    chat_history_lifecycle_creator.append(HumanMessage(content=filled_prompt))
                    chat_history_lifecycle_creator.append(AIMessage(content=full_msg))
                    cl.user_session.set("chat_history_lifecycle_creator", chat_history_lifecycle_creator)
                    await msg_contentgen.send()
                    return

                except Exception as e:
                    logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")
        else:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return
        
       
@cl.action_callback("submit_selections")
async def on_submit_selections(action):
    form_msg = cl.user_session.get("form_msg")
    await form_msg.remove()
    # Extract the selections payload and store it for later use.
    selections = action.payload.get("selections", [])
    
    # Build a mapping: questionId -> answer (only if answer is non-empty)
    mapping = {}
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer:
            mapping[q["questionId"]] = answer

    # If no selections were made, inform the user.
    if not mapping:
        await cl.Message(content="Please make at least one selection before submitting.").send()
        return

    # Retrieve the prompt template (a list of lines)
    prompt_template = USER_INPUT["content_gen_prompt"]

    # We'll separate header lines (which have no placeholders) from selection lines.
    header_lines = []
    selection_lines = []
    
    for line in prompt_template:
        # Find placeholders in the line (things within {})
        placeholders = re.findall(r'\{(.+?)\}', line)
        if placeholders:
            # Only include the line if every placeholder in it has an answer.
            if all(ph in mapping for ph in placeholders):
                # Remove any existing numbering at the beginning (e.g., "1. ", "2. ", etc.)
                clean_line = re.sub(r'^\s*\d+\.\s*', '', line)
                selection_lines.append(clean_line)
        else:
            # Lines without placeholders (e.g., a header) are always included.
            header_lines.append(line)
    
    # Now, renumber the selection lines sequentially.
    numbered_lines = []
    for i, line in enumerate(selection_lines, start=1):
        # Format the line with the mapping values.
        formatted_line = line.format(**mapping)
        numbered_lines.append(f"{i}. {formatted_line}")
    
    # Combine header (if any) and the numbered selection lines.
    if header_lines:
        filled_prompt = "\n".join(header_lines) + "\n" + "\n".join(numbered_lines)
    else:
        filled_prompt = "\n".join(numbered_lines)
    
    await cl.Message(content=f"You have selected the following options:\n{filled_prompt[12:]}").send()
    rx_content_create = cl.user_session.get("rx_content_creator")
    chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
    max_retries = 3
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

@cl.on_message
async def on_message(message: cl.Message):
    chat_profile = cl.user_session.get("chat_profile")
    user_msg = message.content
    
    if chat_profile == "Web & App Content Creation":
        rx_content_create = cl.user_session.get("rx_content_creator")
        chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
        if len(chat_history_content_creator) == 0:
            await cl.Message(content="Please fill and submit the questions above to start").send()
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
            if message.elements[0].name.endswith('.docx'):
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

    elif chat_profile == "Lifecycle Content Creation":
        rx_lifecycle_create = cl.user_session.get("rx_lifecycle_creator")
        chat_history_lifecycle_creator = cl.user_session.get("chat_history_lifecycle_creator")
        if len(chat_history_lifecycle_creator) == 0:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return
        query = {"chat_history": chat_history_lifecycle_creator,
                "sys_msg": SYSTEM_LIFECYCLE_PROMPT,
                "input": user_msg}
        # query = {"chat_history": chat_history_lifecycle_creator, "input": user_msg}
        config = {"configurable": {"thread_id": message.thread_id}}
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_lifecycle_create.astream(
                    query,
                    config=config
                ):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                chat_history_lifecycle_creator.append(HumanMessage(content=user_msg))
                chat_history_lifecycle_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_lifecycle_creator", chat_history_lifecycle_creator)
                await msg_contentgen.send()
                return

            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")
    
