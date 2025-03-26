import chainlit as cl
import os
import re
import json
import logging
import uuid
import base64
import io

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
from utils.prompt_generate_social_media import USER_SELECTION_SOCIAL_MEDIA, USER_INPUT_SOCIAL_MEDIA, SOCIAL_MEDIA_CONTENT_GEN_SYS_PROMPT
from utils.prompt_generate import USER_INPUT, USER_SELECTION_MSG, CONTENT_GEN_SYS_PROMPT, REFINE_SYS_PROMPT
from utils.prompt_generate_lifecycle import (
    USER_INPUT_LIFECYCLE, 
    USER_SELECTION_MSG_LIFECYCLE, 
    SYSTEM_LIFECYCLE_PROMPT, 
    EMAIL_TEMPLATE
)
from utils.prompt_rx_policy import RX_POLICY_SYS_MSG, welcome_message


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

def load_questions(filename="utils/questions_generate_webapp.json"):
    """Loads questions from a JSON file into the format expected by the frontend."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Question file not found: {filename}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {filename}")
        return []

    questions = []
    
    # Check for the structure used in lifecycle/social_media JSONs
    if "questions" in data and isinstance(data["questions"], list):
        for details in data["questions"]:
            # Ensure mandatory fields exist or provide defaults
            question_id = details.get("questionId", details.get("abbrev")) # Use questionId or fallback to abbrev
            if not question_id:
                 logging.warning(f"Skipping question due to missing 'questionId' or 'abbrev' in {filename}: {details.get('question')}")
                 continue
                 
            questions.append({
                "questionId": question_id,
                "question": details.get("question", ""),
                "type": details.get("type", "options"), # Default to options if missing
                "options": details.get("value", []),
                "selected": "", # Initialize frontend state fields
                "isOther": False, # Initialize frontend state fields
                "subQuestions": details.get("sub_questions", {})
                # Removed toolType assignment
            })
    # Check for the structure used in web_app JSON
    elif isinstance(data, dict):
        # Filter out non-question keys like 'tool_type' if they still exist
        question_items = {k: v for k, v in data.items() if isinstance(v, dict) and ("type" in v or "abbrev" in v)}
        for question_text, details in question_items.items():
            question_id = details.get("questionId", details.get("abbrev")) # Use questionId or fallback to abbrev
            if not question_id:
                 logging.warning(f"Skipping question due to missing 'questionId' or 'abbrev' in {filename}: {question_text}")
                 continue
                 
            questions.append({
                "questionId": question_id,
                "question": question_text, # The key is the question text in this format
                "type": details.get("type", "options"),
                "options": details.get("value", []),
                "selected": "", # Initialize frontend state fields
                "isOther": False, # Initialize frontend state fields
                "subQuestions": details.get("sub_questions", {}) # Handle potential subquestions even in this format
                 # Removed toolType assignment
            })
    else:
        logging.error(f"Unknown JSON structure in file: {filename}")

    return questions

def extract_text_from_file_data(file_data):
    """
    Extract text from attached file data in base64 format.
    
    Args:
        file_data (dict): Dictionary containing file content and type
        
    Returns:
        str: Extracted text from the file
    """
    file_content = file_data["content"]
    file_type = file_data["type"]
    
    # Remove the data URL prefix
    content_parts = file_content.split(',', 1)
    if len(content_parts) > 1:
        base64_content = content_parts[1]
    else:
        base64_content = content_parts[0]
    
    # Decode base64 content
    decoded_content = base64.b64decode(base64_content)
    file_buffer = io.BytesIO(decoded_content)
    
    # Extract text based on file type
    extracted_text = ""
    if "pdf" in file_type.lower():
        extracted_text = read_pdf(file_buffer)
    elif "docx" in file_type.lower() or "document" in file_type.lower():
        extracted_text = read_docx(file_buffer)
        
    return extracted_text

@cl.cache
def rx_content_creator(sys_msg: str = CONTENT_GEN_SYS_PROMPT):
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    llm = AzureChatOpenAI(model=azure_chat_model_name,
                           temperature=0.5,
                            api_key=azure_openai_api_key,
                            api_version=openai_api_version,
                            azure_endpoint=azure_openai_endpoint)
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
    llm = AzureChatOpenAI(model=azure_chat_model_name,
                           temperature=0,
                           api_key=azure_openai_api_key,
                           api_version=openai_api_version,
                           azure_endpoint=azure_openai_endpoint)
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
    llm = AzureChatOpenAI(model=azure_chat_model_name,
                           temperature=0.5,
                           api_key=azure_openai_api_key,
                           api_version=openai_api_version,
                           azure_endpoint=azure_openai_endpoint)
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser
    return chain

@cl.cache
def rx_social_media_creator(sys_msg: str = SOCIAL_MEDIA_CONTENT_GEN_SYS_PROMPT):

    
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
def rx_policy_gen(sys_msg: str = RX_POLICY_SYS_MSG):
    """Generate a policy generation chain with prompt, LLM, and output parser."""
    
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
    return [
        cl.ChatProfile(
            name="Web & App Content Creation",
            markdown_description="Generate Web & App content for Riyadh Air.",
            icon="/public/content.svg",
        ),
         cl.ChatProfile(
            name="Lifecycle Content Creation",
            markdown_description="Generate Lifecycle content for Riyadh Air.",
            icon="/public/lifecycle.svg"
        ),
        # cl.ChatProfile(
        #     name="Social Media Content Creation",
        #     markdown_description="Refine existing content for Riyadh Air.",
        #     icon="/public/user_circle.svg"
        # ),
        # cl.ChatProfile(
        #     name="RX Policy Generation",
        #     markdown_description="Generate policy documents for Riyadh Air.",
        #     icon="/public/policy.svg"
        # ),
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

    # --- Web & App Content Creation ---
    if chat_profile == "Web & App Content Creation":
        rx_content_create = rx_content_creator()
        cl.user_session.set("rx_content_creator", rx_content_create)
        cl.user_session.set("chat_history_content_creator", [])
        
        questions = load_questions("utils/questions_generate_webapp.json") # Specify file
        
        # *** Pass submitActionName and enableHierarchy ***
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions",
            props={
                "questions": questions,
                "submitActionName": "submit_selections", # Action for this profile
                "enableHierarchy": False                # No hierarchy for this profile
            }
        )
        form_msg = cl.Message(content="Please answer the following questions:", elements=[multi_select_element])
        cl.user_session.set("form_msg", form_msg)
        await form_msg.send()

    # --- Content Refinement ---
    elif chat_profile == "Content Refinement":
        rx_copywrite = rx_copywriter()
        cl.user_session.set("rx_copywriter", rx_copywrite)
        cl.user_session.set("chat_history_copywriter", [])
        # No form needed for this profile based on original code

    # --- Lifecycle Content Creation ---
    elif chat_profile == "Lifecycle Content Creation":
        rx_lifecycle_create = rx_lifecycle_creator()
        cl.user_session.set("rx_lifecycle_creator", rx_lifecycle_create)
        cl.user_session.set("chat_history_lifecycle_creator", [])

        questions = load_questions("utils/question_generate_lifecycle.json") # Specify file
        
        # *** Pass submitActionName and enableHierarchy ***
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions",
            props={
                "questions": questions,
                "submitActionName": "submit_lifecycle_selections", # Action for this profile
                "enableHierarchy": True                           # Hierarchy enabled
            }
        )
        form_msg = cl.Message(content="Please answer the following questions for lifecycle content:", elements=[multi_select_element])
        cl.user_session.set("lifecycle_form_msg", form_msg)
        await form_msg.send()

    # --- Social Media Content Creation ---
    elif chat_profile == "Social Media Content Creation":
        rx_social_media_create = rx_social_media_creator()
        cl.user_session.set("rx_social_media_creator", rx_social_media_create)
        cl.user_session.set("chat_history_social_media_creator", [])
        
        questions = load_questions("utils/question_social_media.json") # Specify file
        
        # *** Pass submitActionName and enableHierarchy ***
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions",
            props={
                "questions": questions,
                "submitActionName": "submit_social_media_selections", # Action for this profile
                "enableHierarchy": True                              # Hierarchy enabled
            }
        )
        form_msg = cl.Message(content="Please answer the following questions for social media content:", elements=[multi_select_element])
        cl.user_session.set("social_media_form_msg", form_msg)
        await form_msg.send()

    # --- RX Policy Generation ---
    elif chat_profile == "RX Policy Generation":
        cl.user_session.set("welcome_msg_removed", False)
        cl.user_session.set("chat_history", [])
        rx_policy = rx_policy_gen()
        cl.user_session.set("rx_policy", rx_policy)
        welcome_msg = cl.Message(content=welcome_message, author="Riyadh Air AI Policy Generator")
        cl.user_session.set("welcome_msg", welcome_msg)
        await welcome_msg.send()

@cl.action_callback("submit_selections")
async def on_submit_selections(action):
    form_msg = cl.user_session.get("form_msg")
    await form_msg.remove()
    # Extract the selections payload and store it for later use.
    selections = action.payload.get("selections", [])
    
    # Extract files from payload
    files_data = action.payload.get("files", {})
    
    # Build a mapping: questionId -> answer (only if answer is non-empty)
    mapping = {}
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer:
            mapping[q["questionId"]] = answer
            
            # Process file content if this question has an attached file
            if q["questionId"] in files_data:
                extracted_text = extract_text_from_file_data(files_data[q["questionId"]])
                # Add extracted text to the mapping with a special key
                mapping[f"{q['questionId']}_content"] = extracted_text

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
    # Add file contents to the prompt if any
    file_contents = []
    for key, value in mapping.items():
        if key.endswith("_content") and value.strip():
            original_key = key.replace("_content", "")
            if original_key in mapping:
                file_contents.append(f"\n--- Content from attached file for '{mapping[original_key]}' ---\n{value}\n")
    
    if file_contents:
        filled_prompt += "\n" + "\n".join(file_contents)
    
    rx_content_create = cl.user_session.get("rx_content_creator")
    chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
    max_retries = 3
    query = {"chat_history": chat_history_content_creator, "input": filled_prompt}
    msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")
    for attempt in range(max_retries):
        try:
            full_msg = ""
            async for chunk in rx_content_create.astream(
                query
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

@cl.action_callback("submit_lifecycle_selections")
async def on_submit_lifecycle_selections(action):
    form_msg = cl.user_session.get("lifecycle_form_msg")
    await form_msg.remove()
    
    # Extract the selections payload
    selections = action.payload.get("selections", [])
    
    # Extract files from payload
    files_data = action.payload.get("files", {})
    
    # Build a mapping of answers
    user_responses = {}
    file_contents = []
    
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer:
            user_responses[q["questionId"]] = answer
            
            # Process file content if this question has an attached file
            if q["questionId"] in files_data:
                extracted_text = extract_text_from_file_data(files_data[q["questionId"]])
                file_contents.append(f"\n--- Content from attached file for '{answer}' ---\n{extracted_text}\n")
    
    # If no selections were made, inform the user
    if not user_responses:
        await cl.Message(content="Please make at least one selection before submitting.").send()
        return
    
    try:
        # Process the selections to create the prompt
        filled_prompt = adjust_template(USER_INPUT_LIFECYCLE["content_gen_prompt"], user_responses)
        
        await cl.Message(content=f"You have selected the following options:\n{filled_prompt[12:]}").send()
        # Add file contents to the prompt if any
        if file_contents:
            filled_prompt += "\n" + "\n".join(file_contents)
        
        cl.user_session.set("filled_prompt", filled_prompt)
        
        # Handle email template if applicable
        email_template = EMAIL_TEMPLATE.get(user_responses.get("content_purpose", ""), "")
        prompt_email_template = ""
        if len(email_template) > 0:
            prompt_email_template = f"\nEmail Template for {user_responses.get('content_purpose', '')}"
            prompt_email_template += "\n\n" + email_template
        
        rx_lifecycle_create = cl.user_session.get("rx_lifecycle_creator")
        chat_history_lifecycle_creator = cl.user_session.get("chat_history_lifecycle_creator")
        
        query = {
            "chat_history": chat_history_lifecycle_creator,
            "sys_msg": SYSTEM_LIFECYCLE_PROMPT + prompt_email_template,
            "input": filled_prompt
        }
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_lifecycle_create.astream(
                    query
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
    except Exception as e:
        logging.error(f"Error processing lifecycle selections: {e}")
        await cl.Message(content="An error occurred processing your selections. Please try again.").send()

@cl.action_callback("submit_social_media_selections")
async def on_submit_social_media_selections(action):
    form_msg = cl.user_session.get("social_media_form_msg")
    await form_msg.remove()
    
    # Extract the selections payload
    selections = action.payload.get("selections", [])
    
    # Extract files from payload
    files_data = action.payload.get("files", {})
    
    # Build a mapping of answers
    user_responses = {}
    file_contents = []
    
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer:
            user_responses[q["questionId"]] = answer
            
            # Process file content if this question has an attached file
            if q["questionId"] in files_data:
                extracted_text = extract_text_from_file_data(files_data[q["questionId"]])
                file_contents.append(f"\n--- Content from attached file for '{answer}' ---\n{extracted_text}\n")
    
    # If no selections were made, inform the user
    if not user_responses:
        await cl.Message(content="Please make at least one selection before submitting.").send()
        return
    
    try:
        # Process the selections to create the prompt
        filled_prompt = adjust_template(USER_INPUT_SOCIAL_MEDIA["content_gen_prompt"], user_responses)
        await cl.Message(content=f"You have selected the following options:\n{filled_prompt[12:]}").send()
        
        # Add file contents to the prompt if any
        if file_contents:
            filled_prompt += "\n" + "\n".join(file_contents)
        
        cl.user_session.set("filled_prompt", filled_prompt)
        
        rx_social_media_create = cl.user_session.get("rx_social_media_creator")
        chat_history_social_media_creator = cl.user_session.get("chat_history_social_media_creator")
        
        query = {
            "chat_history": chat_history_social_media_creator,
            "input": filled_prompt
        }
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_social_media_create.astream(
                    query
                ):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk
                
                chat_history_social_media_creator.append(HumanMessage(content=filled_prompt))
                chat_history_social_media_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_social_media_creator", chat_history_social_media_creator)
                await msg_contentgen.send()
                return
            
            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")
    except Exception as e:
        logging.error(f"Error processing lifecycle selections: {e}")
        await cl.Message(content="An error occurred processing your selections. Please try again.").send()

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
    
    elif chat_profile == "Social Media Content Creation":
        rx_social_media_create = cl.user_session.get("rx_social_media_creator")
        chat_history_social_media_creator = cl.user_session.get("chat_history_social_media_creator")
        if len(chat_history_social_media_creator) == 0:
            await cl.Message(content="Please start a new chat to generate content.").send()
            return
        query = {"chat_history": chat_history_social_media_creator,
                "input": user_msg}

        config = {"configurable": {"thread_id": message.thread_id}}
        msg_contentgen = cl.Message(content="", author="Riyadh Air AI Web Research")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async for chunk in rx_social_media_create.astream(
                    query,
                    config=config
                ):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                chat_history_social_media_creator.append(HumanMessage(content=user_msg))
                chat_history_social_media_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_social_media_creator", chat_history_social_media_creator)
                await msg_contentgen.send()
                return

            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")

    elif chat_profile == "RX Policy Generation":
        
        if message.elements:
            if message.elements[0].name.endswith('.docx'):
                file_element = message.elements[0]
                path = file_element.path
                doc_content = read_docx(path)
                user_msg = (
                        f"{user_msg}:\n\nThe following is content from an attached word document, use it to "
                        f"supplement your answer:\n\n{doc_content}")
            elif message.elements[0].name.endswith('.pdf'):
                file_element = message.elements[0]
                path = file_element.path
                doc_content = read_pdf(path)
                user_msg = (
                        f"{user_msg}:\n\nThe following is content from an attached PDF document, use it to "
                        f"supplement your answer:\n\n{doc_content}")

        chat_history = cl.user_session.get("chat_history")
        welcome_msg = cl.user_session.get("welcome_msg")
        
        if not cl.user_session.get("welcome_msg_removed"):
            await welcome_msg.remove()
            cl.user_session.set("welcome_msg_removed", True)

        rx_policy = cl.user_session.get("rx_policy")
        query = {"chat_history": chat_history, "input": user_msg}
        msg = cl.Message(content="", author="Riyadh Air AI Policy Generator")
        config = {"configurable": {"thread_id": message.thread_id}}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                async with cl.Step("Riyadh Air AI Policy Generator", show_input=False) as step:
                    step.input = user_msg
                    async for chunk in rx_policy.astream(
                        query,
                        config=config
                    ):
                        await msg.stream_token(chunk)
                        full_msg += chunk

                    chat_history.append(HumanMessage(content=user_msg))
                    chat_history.append(AIMessage(content=full_msg))
                    cl.user_session.set("chat_history", chat_history)
                await msg.send()
                return

            except Exception as e:
                logging.error(f"Error faced while running the agent. Error: {e}... Retrying attempt {attempt}....")