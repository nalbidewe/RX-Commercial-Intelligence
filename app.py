"""
This script implements a Chainlit application for generating various types of content
(Web/App, Lifecycle, Policy) for Riyadh Air using Azure OpenAI models.
It includes features like user authentication, chat profiles, dynamic form generation
based on JSON files, file uploads (PDF, DOCX), text extraction, and interaction
with Azure Key Vault and MongoDB.
"""
import chainlit as cl
import os
import re
import json
import logging
import base64
import io

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from langchain_openai import AzureChatOpenAI
import tiktoken # For token counting
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from pypdf import PdfReader # For PDF processing
import docx    # For DOCX processing

from azure.keyvault.secrets import SecretClient # For Azure Key Vault interaction
from azure.identity import ClientSecretCredential # For Azure authentication
from cryptography.fernet import Fernet # For decrypting secrets
import urllib.parse # For encoding MongoDB credentials
from pymongo import MongoClient # For MongoDB interaction

# Import system prompts and templates from utility files
from utils.prompt_generate import USER_INPUT, CONTENT_GEN_SYS_PROMPT, REFINE_SYS_PROMPT
from utils.prompt_arabic_generate import ARABIC_TRANSLATION_SYS_PROMPT, ARABIC_TRANSLATION_WITHIN_TOOL_SYS_PROMPT
from utils.prompt_generate_lifecycle import (
    USER_INPUT_LIFECYCLE,
    SYSTEM_LIFECYCLE_PROMPT,
    EMAIL_TEMPLATE
)
from utils.prompt_rx_policy import RX_POLICY_SYS_MSG, welcome_message


# Configure logging to output informational messages
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')

# Load environment variables from a .env file, overriding existing ones if present
load_dotenv(override=True)
# Retrieve encrypted Azure credentials from environment variables
en_tenant_id = os.getenv('OAUTH_AZURE_AD_TENANT_ID')
en_client_id = os.getenv('SP_CLIENT_ID')
en_client_secret = os.getenv('SP_CLIENT_SECRET')

def init_key_vault_client(tenant_id, en_client_id, en_client_secret):
    """
    Initializes and returns an Azure Key Vault SecretClient.

    Decrypts the client ID and secret using Fernet encryption before authenticating.

    Args:
        tenant_id (str): The Azure AD tenant ID.
        en_client_id (str): The encrypted service principal client ID.
        en_client_secret (str): The encrypted service principal client secret.

    Returns:
        SecretClient: An authenticated client for interacting with Azure Key Vault.
    """
    # Initialize Fernet with the encryption key from environment variables
    fernet = Fernet(os.getenv('ENCRYPTION_KEY'))

    # Decrypt client ID and secret
    client_id = fernet.decrypt(en_client_id).decode("utf-8")
    client_secret = fernet.decrypt(en_client_secret).decode("utf-8")

    # Get Key Vault name and construct the URL
    key_vault_name = os.getenv('KEYVAULT_NAME')
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    # Create credentials using the decrypted client ID and secret
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    # Initialize the SecretClient
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    return client

def get_secret_value(secretName, client):
    """
    Retrieves the value of a secret from Azure Key Vault.

    Args:
        secretName (str): The name of the secret to retrieve.
        client (SecretClient): The authenticated Key Vault client.

    Returns:
        str: The value of the retrieved secret.
    """
    retrieved_secret = client.get_secret(secretName)
    return retrieved_secret.value

# Initialize the Key Vault client
client = init_key_vault_client(en_tenant_id, en_client_id, en_client_secret)

# Retrieve Azure OpenAI and other necessary secrets from Key Vault
azure_chat_model_name_mini = get_secret_value("azure-openai-4o-mini-global", client) # Model name (mini)
azure_chat_model_name = get_secret_value("azure-openai-4o-global", client) # Model name (standard)
azure_embeddings_model_name = get_secret_value("azure-openai-embedding-small", client) # Embeddings model name
openai_api_version = get_secret_value("azure-openai-api-version", client) # API version
azure_openai_endpoint= get_secret_value("azure-openai-endpoint", client) # API endpoint
azure_openai_api_key = get_secret_value("azure-openai-api-key", client) # API key

# Retrieve MongoDB connection details from Key Vault
server = get_secret_value("mongodb-url", client)
username = get_secret_value("mongodb-user", client)
password = get_secret_value("mongodb-pass", client)

# Construct the MongoDB connection string, URL-encoding the username and password
CONNECTION_STRING = "mongodb+srv://"+urllib.parse.quote_plus(username)+":" + urllib.parse.quote_plus(password) + f"@{server}/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
# Connect to Azure Cosmos MongoDB using the constructed connection string
client = MongoClient(CONNECTION_STRING)

# Access the specific database and collection for user authentication
db = client["AIContentGenApp"]
collection = db["Users"]

def read_pdf(file) -> str:
    """
    Extracts text content from a PDF file object.

    Args:
        file: A file-like object (e.g., opened file or BytesIO) containing PDF data.

    Returns:
        str: The concatenated text extracted from all pages of the PDF.
           Returns an empty string if the PDF cannot be read or has no text.
    """
    try:
        reader = PdfReader(file)
        text = ""
        for page_num in range(len(reader.pages)):
            page_text = reader.pages[page_num].extract_text()
            if page_text: # Append text only if extraction was successful for the page
                text += page_text
        return text
    except Exception as e:
        logging.error(f"Error reading PDF: {e}")
        return "" # Return empty string on error

def read_docx(file) -> str:
    """
    Extracts text content from a DOCX file object, handling paragraphs and tables.

    Args:
        file: A file-like object (e.g., opened file or BytesIO) containing DOCX data.

    Returns:
        str: The concatenated text extracted from paragraphs and tables in the DOCX.
           Returns an empty string if the DOCX cannot be read.
    """
    try:
        doc = docx.Document(file)
        full_text = []
        # Iterate through elements in the document body (paragraphs and tables)
        for element in doc.element.body:
            if element.tag.endswith('p'): # Check if the element is a paragraph
                p = docx.text.paragraph.Paragraph(element, doc)
                full_text.append(p.text)
            elif element.tag.endswith('tbl'): # Check if the element is a table
                table = docx.table.Table(element, doc)
                table_text = []
                # Iterate through rows and cells in the table
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells]
                    table_text.append(" | ".join(row_text)) # Join cell text with '|'
                full_text.append("\n".join(table_text)) # Join rows with newline
        return "\n".join(full_text) # Join all extracted text parts
    except Exception as e:
        logging.error(f"Error reading DOCX: {e}")
        return "" # Return empty string on error

def num_tokens(text: str, model: str = 'gpt-4o-mini') -> int:
    """
    Calculates the number of tokens in a given text string using tiktoken
    for a specified OpenAI model.

    Args:
        text (str): The input text string.
        model (str): The target OpenAI model name (e.g., 'gpt-4o-mini', 'gpt-4').
                     Defaults to 'gpt-4o-mini'.

    Returns:
        int: The estimated number of tokens in the text for the specified model.
    """
    try:
        # Get the encoding for the specified model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to a common encoding if the model name is not recognized
        logging.warning(f"Model '{model}' not found for token counting. Using 'cl100k_base'.")
        encoding = tiktoken.get_encoding('cl100k_base')
    # Encode the text and return the number of tokens
    return len(encoding.encode(text))

def _process_question_recursive(question_data):
    """
    Recursively processes a question dictionary or list, mapping 'sub_questions'
    to 'subQuestions' and ensuring necessary keys are present.
    """
    processed_questions = []
    if isinstance(question_data, list):
        items_to_process = question_data
    elif isinstance(question_data, dict) and "questions" in question_data:
         # Handle structure like lifecycle JSON root
        items_to_process = question_data["questions"]
    elif isinstance(question_data, dict):
         # Handle structure like web_app JSON root (dict of questions)
         # Convert dict to list of dicts first
         items_to_process = []
         for q_text, details in question_data.items():
             # Ensure it looks like a question definition
             if isinstance(details, dict) and ("type" in details or "abbrev" in details):
                 # Add the question text back into the details dict
                 details["question"] = q_text
                 items_to_process.append(details)
             else:
                 logging.warning(f"Skipping non-question item in dict structure: {q_text}")
    else:
        logging.error(f"Unexpected data type for recursive processing: {type(question_data)}")
        return [] # Return empty list for unexpected types

    for details in items_to_process:
        if not isinstance(details, dict):
            logging.warning(f"Skipping non-dictionary item in question list: {details}")
            continue

        question_id = details.get("questionId", details.get("abbrev"))
        if not question_id:
            logging.warning(f"Skipping question due to missing 'questionId' or 'abbrev': {details.get('question')}")
            continue

        processed_q = {
            "questionId": question_id,
            "question": details.get("question", ""),
            "type": details.get("type", "options"),
            "options": details.get("value", []),
            "selected": "",
            "isOther": False,
            # Recursively process sub_questions if they exist
            "subQuestions": {} # Initialize as empty dict
        }

        raw_sub_questions = details.get("sub_questions")
        if raw_sub_questions and isinstance(raw_sub_questions, dict):
            processed_subs = {}
            for key, sub_list in raw_sub_questions.items():
                # Recursively process the list of sub-questions for this key
                processed_subs[key] = _process_question_recursive(sub_list)
            processed_q["subQuestions"] = processed_subs

        processed_questions.append(processed_q)

    return processed_questions

def load_questions(filename="utils/questions_generate_webapp.json"):
    """
    Loads questions from a specified JSON file and formats them recursively
    for the Chainlit CustomElement frontend component, ensuring consistent
    use of 'subQuestions' key.

    Args:
        filename (str): The path to the JSON file containing the questions.

    Returns:
        list: A list of dictionaries, where each dictionary represents a question
              formatted for the frontend with nested 'subQuestions'. Returns an
              empty list on error.
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error(f"Question file not found: {filename}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {filename}")
        return []

    # Start the recursive processing
    questions = _process_question_recursive(data)
    return questions

def extract_text_from_file_data(file_data):
    """
    Extracts text content from file data provided in a dictionary format,
    typically received from the frontend after a file upload within a form.

    Handles base64 decoding and text extraction for PDF and DOCX types.

    Args:
        file_data (dict): A dictionary containing file information, expected keys:
                          'content' (base64 encoded string with optional data URL prefix)
                          'type' (MIME type string, e.g., 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    Returns:
        str: The extracted text content from the file. Returns an empty string
             if the file type is unsupported or an error occurs during processing.
    """
    try:
        file_content = file_data["content"]
        file_type = file_data["type"]

        # Remove the data URL prefix (e.g., "data:application/pdf;base64,") if present
        content_parts = file_content.split(',', 1)
        if len(content_parts) > 1:
            base64_content = content_parts[1]
        else:
            base64_content = content_parts[0] # Assume no prefix if split fails

        # Decode the base64 content into bytes
        decoded_content = base64.b64decode(base64_content)
        # Create a file-like object from the decoded bytes
        file_buffer = io.BytesIO(decoded_content)

        # Extract text based on the file type (case-insensitive check)
        extracted_text = ""
        if "pdf" in file_type.lower():
            extracted_text = read_pdf(file_buffer)
        elif "docx" in file_type.lower() or "wordprocessingml.document" in file_type.lower():
            extracted_text = read_docx(file_buffer)
        else:
            logging.warning(f"Unsupported file type for text extraction: {file_type}")

        return extracted_text
    except KeyError as e:
        logging.error(f"Missing expected key in file_data: {e}")
        return ""
    except base64.binascii.Error as e:
        logging.error(f"Base64 decoding error: {e}")
        return ""
    except Exception as e:
        logging.error(f"Error extracting text from file data: {e}")
        return ""

@cl.cache # Cache the initialized chain for performance
def rx_content_creator(sys_msg: str = CONTENT_GEN_SYS_PROMPT):
    """
    Initializes and returns a Langchain Runnable sequence (chain) for
    Web & App content creation.

    Uses AzureChatOpenAI (gpt-4o) with a specific system prompt.

    Args:
        sys_msg (str): The system prompt to configure the LLM. Defaults to
                       CONTENT_GEN_SYS_PROMPT from utils.

    Returns:
        Runnable: The initialized Langchain chain.
    """
    # Define the prompt template including a placeholder for chat history
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}") # Placeholder for user input
    ])
    # Initialize the Azure OpenAI chat model
    llm = AzureChatOpenAI(model=azure_chat_model_name, # Use the standard gpt-4o model
                           temperature=0.5, # Moderate temperature for creative but grounded output
                            api_key=azure_openai_api_key,
                            api_version=openai_api_version,
                            azure_endpoint=azure_openai_endpoint)
    # Use a simple string output parser
    output_parser = StrOutputParser()
    # Combine prompt, LLM, and parser into a chain
    chain = prompt | llm | output_parser
    return chain

@cl.cache # Cache the initialized chain
def rx_copywriter(sys_msg: str = REFINE_SYS_PROMPT):
    """
    Initializes and returns a Langchain Runnable sequence (chain) for
    content refinement (copywriting).

    Uses AzureChatOpenAI (gpt-4o) with a specific system prompt for refinement tasks.

    Args:
        sys_msg (str): The system prompt to configure the LLM. Defaults to
                       REFINE_SYS_PROMPT from utils.

    Returns:
        Runnable: The initialized Langchain chain.
    """
    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    # Initialize the Azure OpenAI chat model
    llm = AzureChatOpenAI(model=azure_chat_model_name, # Use the standard gpt-4o model
                           temperature=0, # Low temperature for more deterministic refinement
                           api_key=azure_openai_api_key,
                           api_version=openai_api_version,
                           azure_endpoint=azure_openai_endpoint)
    # Use a simple string output parser
    output_parser = StrOutputParser()
    # Combine into a chain
    chain = prompt | llm | output_parser
    return chain

@cl.cache # Cache the initialized chain
def rx_lifecycle_creator():
    """
    Initializes and returns a Langchain Runnable sequence (chain) for
    Lifecycle content creation.

    Uses AzureChatOpenAI (gpt-4o). The system prompt is passed dynamically during invocation.

    Returns:
        Runnable: The initialized Langchain chain.
    """
    # Define the prompt template, note the system message is also a variable
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{sys_msg}"), # System prompt provided at runtime
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    # Initialize the Azure OpenAI chat model
    llm = AzureChatOpenAI(model=azure_chat_model_name, # Use the standard gpt-4o model
                           temperature=0.5, # Moderate temperature
                           api_key=azure_openai_api_key,
                           api_version=openai_api_version,
                           azure_endpoint=azure_openai_endpoint)
    # Use a simple string output parser
    output_parser = StrOutputParser()
    # Combine into a chain
    chain = prompt | llm | output_parser
    return chain

@cl.cache # Cache the initialized chain
def rx_policy_gen(sys_msg: str = RX_POLICY_SYS_MSG):
    """
    Initializes and returns a Langchain Runnable sequence (chain) for
    RX Policy generation.

    Uses AzureChatOpenAI (gpt-4o) with a specific system prompt for policy generation.

    Args:
        sys_msg (str): The system prompt to configure the LLM. Defaults to
                       RX_POLICY_SYS_MSG from utils.

    Returns:
        Runnable: The initialized Langchain chain.
    """
    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    # Initialize the Azure OpenAI chat model
    llm = AzureChatOpenAI(model=azure_chat_model_name, temperature=0, api_key=azure_openai_api_key, api_version=openai_api_version, azure_endpoint=azure_openai_endpoint)
    # Use a simple string output parser
    output_parser = StrOutputParser()
    # Combine into a chain
    chain = prompt | llm | output_parser
    return chain

@cl.cache # Cache the initialized chain
def rx_translator(sys_msg: str = ARABIC_TRANSLATION_SYS_PROMPT):
    """
    Initializes and returns a Langchain Runnable sequence (chain) for
    content translator.

    Uses AzureChatOpenAI (gpt-4o) with a specific system prompt for refinement tasks.

    Args:
        sys_msg (str): The system prompt to configure the LLM. Defaults to
                       ARABIC_TRANSLATION_SYS_PROMPT from utils.

    Returns:
        Runnable: The initialized Langchain chain.
    """
    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", sys_msg),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])
    # Initialize the Azure OpenAI chat model
    llm = AzureChatOpenAI(model=azure_chat_model_name, # Use the standard gpt-4o model
                           temperature=0, # Low temperature for more deterministic refinement
                           api_key=azure_openai_api_key,
                           api_version=openai_api_version,
                           azure_endpoint=azure_openai_endpoint)
    # Use a simple string output parser
    output_parser = StrOutputParser()
    # Combine into a chain
    chain = prompt | llm | output_parser
    return chain

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """
    Chainlit authentication callback. Verifies user credentials against
    the MongoDB 'Users' collection.

    Args:
        username (str): The username entered by the user.
        password (str): The password entered by the user.

    Returns:
        cl.User | None: A Chainlit User object with metadata if authentication
                       is successful, otherwise None.
    """
    # Find the user in the MongoDB collection
    user = collection.find_one({"username": username})

    # Check if user exists and the password matches
    if user and user["password"] == password:
        # Return a Chainlit User object with metadata from the database
        return cl.User(
            identifier=username,
            metadata={
                "role": user.get("role", "user"), # Default role to 'user' if not found
                "provider": user.get("provider", "db") # Default provider to 'db'
            }
        )
    # Return None if authentication fails
    return None

@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    """
    Defines the available chat profiles (modes) for the application.

    The available profiles might depend on the authenticated user's role in future implementations,
    but currently, it returns a fixed list.

    Args:
        current_user (cl.User): The currently authenticated Chainlit user object.
                                (Currently unused but available for role-based logic).

    Returns:
        list[cl.ChatProfile]: A list of ChatProfile objects defining the available modes.
    """
    user_role = current_user.metadata.get("role") # Get user role
    return [
        cl.ChatProfile(
            name="Web & App Content Creation",
            markdown_description="Generate Web & App content for Riyadh Air.",
            icon="/public/content.svg", # Icon displayed in the UI
        ),
         cl.ChatProfile(
            name="Lifecycle Content Creation",
            markdown_description="Generate Lifecycle content for Riyadh Air.",
            icon="/public/lifecycle.svg"
        ),
        # cl.ChatProfile(
        #     name="RX Policy Generation",
        #     markdown_description="Generate policy documents for Riyadh Air.",
        #     icon="/public/policy.svg"
        # ),
        cl.ChatProfile(
            name="Content Refinement",
            markdown_description="Refine existing content for Riyadh Air.",
            icon="/public/refine.svg",
            # Define starter prompts for this profile
            starters=[
                cl.Starter(
                    label="Usage Instructions",
                    message="How can I use this tool?",
                    icon="/public/help.svg",
                ),
            ]
        ),

        cl.ChatProfile(
            name="Content Translation",
            markdown_description="Translate existing Riyadh Air content to arabic.",
            icon="/public/translator.svg",
            # Define starter prompts for this profile
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
    """
    Fills a template (provided as a list of lines) with user responses.

    Only includes lines from the template where all placeholders ({key})
    within that line have a corresponding entry in the responses dictionary.

    Args:
        template_lines (list[str]): A list of strings representing the template lines.
                                    Lines can contain placeholders like "{placeholder_key}".
        responses (dict): A dictionary mapping placeholder keys to user-provided values.

    Returns:
        str: The filled template as a single string, with lines joined by newlines.
             Lines where placeholders couldn't be filled are omitted.
    """
    filled_lines = []
    for line in template_lines:
        # Find all placeholders (e.g., {key}) in the current line
        placeholders = re.findall(r"\{(.*?)\}", line)
        # Check if all found placeholders exist as keys in the responses dictionary
        if all(placeholder in responses for placeholder in placeholders):
            # If all placeholders are present, format the line using the responses
            try:
                filled_lines.append(line.format(**responses))
            except KeyError as e:
                # This should theoretically not happen due to the 'all' check, but added for safety
                logging.warning(f"KeyError during template formatting (should have been caught): {e} in line '{line}'")
        # else: line is skipped if any placeholder is missing in responses
    # Join the successfully filled lines with newlines
    return "\n".join(filled_lines)

@cl.on_chat_start
async def on_chat_start():
    """
    Handles the initialization logic when a new chat session starts.

    Identifies the selected chat profile and sets up the corresponding
    Langchain chain, chat history, and initial UI elements (like forms).
    """
    # Get the selected chat profile from the user session
    chat_profile = cl.user_session.get("chat_profile")
    logging.info(f"Chat started with profile: {chat_profile}")

    # --- Web & App Content Creation Profile ---
    if chat_profile == "Web & App Content Creation":
        # Initialize or retrieve the cached chain
        rx_content_create = rx_content_creator()
        # Store the chain and an empty chat history in the user session
        cl.user_session.set("rx_content_creator", rx_content_create)
        cl.user_session.set("chat_history_content_creator", []) # Initialize history

        # Load questions specific to this profile
        questions = load_questions("utils/questions_generate_webapp.json")

        # Create the custom UI element for displaying questions
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions", # Matches the frontend component name
            props={
                "questions": questions,
                "submitActionName": "submit_selections", # Action name triggered on submit
                "enableHierarchy": False # Disable hierarchical display for this profile
            }
        )
        # Create a message containing the form element
        form_msg = cl.Message(content="Please answer the following questions:", elements=[multi_select_element])
        # Store the form message in the session (to remove it later)
        cl.user_session.set("form_msg", form_msg)
        # Send the form message to the user
        await form_msg.send()

    # --- Content Refinement Profile ---
    elif chat_profile == "Content Refinement":
        # Initialize or retrieve the cached chain
        rx_copywrite = rx_copywriter()
        # Store the chain and an empty chat history
        cl.user_session.set("rx_copywriter", rx_copywrite)
        cl.user_session.set("chat_history_copywriter", []) # Initialize history
        # No initial form is sent for this profile

    # --- Lifecycle Content Creation Profile ---
    elif chat_profile == "Lifecycle Content Creation":
        # Initialize or retrieve the cached chain
        rx_lifecycle_create = rx_lifecycle_creator()
        # Store the chain and an empty chat history
        cl.user_session.set("rx_lifecycle_creator", rx_lifecycle_create)
        cl.user_session.set("chat_history_lifecycle_creator", []) # Initialize history

        # Load questions specific to this profile
        questions = load_questions("utils/question_generate_lifecycle.json")

        # Create the custom UI element
        multi_select_element = cl.CustomElement(
            name="MultiSelectQuestions",
            props={
                "questions": questions,
                "submitActionName": "submit_lifecycle_selections", # Specific action name
                "enableHierarchy": True # Enable hierarchical display
            }
        )
        # Create and send the form message
        form_msg = cl.Message(content="Please answer the following questions for lifecycle content:", elements=[multi_select_element])
        cl.user_session.set("lifecycle_form_msg", form_msg) # Store form message
        await form_msg.send()

    # --- RX Policy Generation Profile ---
    elif chat_profile == "RX Policy Generation":
        # Initialize session state variables for this profile
        cl.user_session.set("welcome_msg_removed", False) # Flag to track if welcome message was removed
        cl.user_session.set("chat_history", []) # Initialize history
        # Initialize or retrieve the cached chain
        rx_policy = rx_policy_gen()
        cl.user_session.set("rx_policy", rx_policy)
        # Create the initial welcome message
        welcome_msg = cl.Message(content=welcome_message, author="Riyadh Air")
        cl.user_session.set("welcome_msg", welcome_msg) # Store welcome message
        # Send the welcome message
        await welcome_msg.send()

    elif chat_profile == "Content Translation":
        # Initialize or retrieve the cached chain
        rx_translation = rx_translator()
        # Store the chain and an empty chat history
        cl.user_session.set("rx_translation", rx_translation)
        cl.user_session.set("chat_history_translator", []) # Initialize history
        # No initial form is sent for this profile


@cl.action_callback("submit_selections") # Decorator for Web/App form submission
async def on_submit_selections(action: cl.Action):
    """
    Handles the submission of the form from the 'Web & App Content Creation' profile.

    Processes user selections and attached files, formats them into a prompt,
    sends the prompt to the LLM, and streams the response back to the user.

    Args:
        action (cl.Action): The action object containing the payload from the form.
                           Payload includes 'selections' (list of question answers)
                           and 'files' (dictionary of uploaded file data).
    """
    # Retrieve and remove the original form message from the UI
    form_msg = cl.user_session.get("form_msg")
    if form_msg:
        await form_msg.remove()

    # Extract selections and file data from the action payload
    selections = action.payload.get("selections", [])
    files_data = action.payload.get("files", {}) # {questionId: fileData}
    # Build a mapping: questionId -> answer (only if answer is non-empty)
    mapping = {}
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer: # Only include questions with answers
            mapping[q["questionId"]] = answer

            # Check if this question has an associated file upload
            if q["questionId"] in files_data:
                try:
                    # Extract text from the uploaded file
                    extracted_text = extract_text_from_file_data(files_data[q["questionId"]])
                    # Add extracted text to the mapping with a special key
                    mapping[f"{q['questionId']}_content"] = extracted_text
                    logging.info(f"Extracted text for questionId '{q['questionId']}'")
                except Exception as e:
                    logging.error(f"Error processing file for questionId '{q['questionId']}': {e}")
                    await cl.Message(content=f"Error processing the attached file for question '{q.get('question', q['questionId'])}'. Please try again.").send()
                    # Decide if you want to return here or continue without file content
                    # return # Option: Stop processing if file extraction fails

    # If no selections were made, inform the user and stop.
    if not mapping:
        logging.warning("Form submitted with no selections.")
        await cl.Message(content="Please make at least one selection before submitting.").send()
        # Resend the form (optional, might be complex to handle state)
        # await on_chat_start() # Be careful with re-triggering chat start
        return

    # Retrieve the prompt template structure from utils
    prompt_template = USER_INPUT["content_gen_prompt"] # Expected to be a list of strings

    # Separate header lines (no placeholders) from lines requiring user input.
    header_lines = []
    selection_lines = []

    for line in prompt_template:
        # Find placeholders ({key}) in the line
        placeholders = re.findall(r'\{(.+?)\}', line)
        if placeholders:
            # Check if all placeholders in this line have corresponding answers in the mapping
            if all(ph in mapping for ph in placeholders):
                # Clean potential leading numbering (e.g., "1. ", "2. ") from the template line
                clean_line = re.sub(r'^\s*\d+\.\s*', '', line)
                selection_lines.append(clean_line)
            # else: Skip line if any placeholder is missing an answer
        else:
            # Lines without placeholders (headers, instructions) are always included.
            header_lines.append(line)

    # Renumber the selected lines sequentially.
    numbered_lines = []
    for i, line in enumerate(selection_lines, start=1):
        try:
            # Format the line using the collected answers
            formatted_line = line.format(**mapping)
            numbered_lines.append(f"{i}. {formatted_line}")
        except KeyError as e:
            logging.error(f"KeyError formatting line '{line}': {e}. Mapping: {mapping}")
            # Handle error, maybe skip the line or show an error message

    # Combine header (if any) and the numbered selection lines into the final prompt start.
    if header_lines:
        filled_prompt = "\n".join(header_lines) + "\n" + "\n".join(numbered_lines)
    else:
        filled_prompt = "\n".join(numbered_lines)

    # Send a confirmation message to the user showing their selections (excluding the initial header)
    # The `[12:]` slice likely aims to remove a generic header like "User Input:"
    await cl.Message(content=f"You have selected the following options:\n{filled_prompt[12:]}").send()

    # Append extracted file contents to the prompt, if any exist.
    file_contents_section = []
    for key, value in mapping.items():
        # Check for keys ending with '_content' which hold extracted text
        if key.endswith("_content") and value and value.strip():
            original_key = key.replace("_content", "")
            # Find the original question text/answer associated with this file
            question_identifier = mapping.get(original_key, original_key) # Use answer or key as identifier
            file_contents_section.append(f"\n--- Content from attached file for '{question_identifier}' ---\n{value}\n--- End of attached content ---")

    if file_contents_section:
        filled_prompt += "\n" + "\n".join(file_contents_section)
        logging.info("Appended extracted file content to the prompt.")

    # specify language preference and provide neccessary instructions
    language_preference = mapping.get("language_preference", "")
    logging.info(f"Language selected: {language_preference}")

    if language_preference == "Arabic only":
        langauge_output_instruction = f"\n\n{ARABIC_TRANSLATION_WITHIN_TOOL_SYS_PROMPT}" + "Output an Arabic version (following the provided lexicon and tone of voice)."

    elif language_preference == "Both English and Arabic":
        langauge_output_instruction = f"\n\n{ARABIC_TRANSLATION_WITHIN_TOOL_SYS_PROMPT}" + "Output both an English and Arabic version (each following the provided lexicon and tone of voice)." 

    else:
        langauge_output_instruction =  "Output an English version (following the provided lexicon and tone of voice)." 
        
        # Append the Arabic system prompt to guide the model for Arabic content generation
    filled_prompt += f"\n{langauge_output_instruction}"

    # Retrieve the chain and chat history from the session
    rx_content_create = cl.user_session.get("rx_content_creator")
    chat_history_content_creator = cl.user_session.get("chat_history_content_creator")

    # Prepare the query for the Langchain chain
    query = {"chat_history": chat_history_content_creator, "input": filled_prompt}

    # Create a message object to stream the LLM response into
    msg_contentgen = cl.Message(content="", author="Riyadh Air")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            full_msg = ""
            # Stream the response from the Langchain chain
            async for chunk in rx_content_create.astream(query):
                await msg_contentgen.stream_token(chunk) # Append chunk to the message UI
                full_msg += chunk # Accumulate the full response

            # Update the chat history with the user prompt and the full AI response
            chat_history_content_creator.append(HumanMessage(content=filled_prompt))
            chat_history_content_creator.append(AIMessage(content=full_msg))
            cl.user_session.set("chat_history_content_creator", chat_history_content_creator)

            # Finalize the streamed message (though stream_token might handle this)
            await msg_contentgen.send()
            logging.info("Successfully generated and streamed response for Web/App content.")
            return # Exit after successful generation

        except Exception as e:
            logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during LLM call for Web/App content: {e}")
            if attempt == max_retries - 1: # If last retry failed
                await msg_contentgen.update(content=f"Sorry, I encountered an error after {max_retries} attempts. Please try again later.")
            # Optional: Add a small delay before retrying
            # await cl.sleep(1) # Requires `import chainlit as cl` if not already done

@cl.action_callback("submit_lifecycle_selections") # Decorator for Lifecycle form submission
async def on_submit_lifecycle_selections(action: cl.Action):
    """
    Handles the submission of the form from the 'Lifecycle Content Creation' profile.

    Processes user selections and files, potentially adjusts the system prompt based
    on selections (e.g., adding an email template), sends the prompt to the LLM,
    and streams the response.

    Args:
        action (cl.Action): The action object containing the payload ('selections', 'files').
    """
    # Retrieve and remove the original form message
    form_msg = cl.user_session.get("lifecycle_form_msg")
    if form_msg:
        await form_msg.remove()

    # Extract selections and file data
    selections = action.payload.get("selections", [])
    files_data = action.payload.get("files", {})

    # Build a mapping of questionId -> answer and extract file contents
    user_responses = {}
    file_contents = []
    for q in selections:
        answer = q.get("selected", "").strip()
        if answer:
            user_responses[q["questionId"]] = answer
            # Process associated file if present
            if q["questionId"] in files_data:
                try:
                    extracted_text = extract_text_from_file_data(files_data[q["questionId"]])
                    # Format file content for inclusion in the prompt
                    file_contents.append(f"\n--- Content from attached file for '{answer}' ---\n{extracted_text}\n--- End of attached content ---")
                    logging.info(f"Extracted text for lifecycle questionId '{q['questionId']}'")
                except Exception as e:
                    logging.error(f"Error processing file for lifecycle questionId '{q['questionId']}': {e}")
                    await cl.Message(content=f"Error processing the attached file for question '{q.get('question', q['questionId'])}'. Please try again.").send()
                    # return # Option: Stop if file processing fails

    # Check if any selections were made
    if not user_responses:
        logging.warning("Lifecycle form submitted with no selections.")
        await cl.Message(content="Please make at least one selection before submitting.").send()
        return

    try:
        # Format the user input part of the prompt using the selected answers
        # Uses adjust_template to only include lines where all placeholders are filled
        filled_prompt = adjust_template(USER_INPUT_LIFECYCLE["content_gen_prompt"], user_responses)

        # Send confirmation message (again, slicing might remove a generic header)
        await cl.Message(content=f"You have selected the following options:\n{filled_prompt[12:]}").send()

        # Append extracted file contents to the user prompt part
        if file_contents:
            filled_prompt += "\n" + "\n".join(file_contents)
            logging.info("Appended extracted file content to the lifecycle prompt.")

        # Store the formatted user input prompt in the session (might not be strictly needed)
        cl.user_session.set("filled_prompt", filled_prompt)

        # --- Dynamic System Prompt Adjustment ---
        # Check if a specific email template should be added based on the 'content_purpose' selection
        selected_purpose = user_responses.get("content_purpose", "")
        email_template = EMAIL_TEMPLATE.get(selected_purpose, "") # Get template from utils dict
        prompt_email_template_addition = ""
        if email_template: # Check if a template exists for the selected purpose
            prompt_email_template_addition = f"\n\n--- Relevant Email Template for '{selected_purpose}' ---\n{email_template}\n--- End of Email Template ---"
            logging.info(f"Adding email template for purpose: {selected_purpose}")

        # Combine the base system prompt with the potential email template addition
        final_system_prompt = SYSTEM_LIFECYCLE_PROMPT + prompt_email_template_addition

        # Retrieve the chain and chat history
        rx_lifecycle_create = cl.user_session.get("rx_lifecycle_creator")
        chat_history_lifecycle_creator = cl.user_session.get("chat_history_lifecycle_creator")

        # Prepare the query, including the potentially modified system prompt
        query = {
            "chat_history": chat_history_lifecycle_creator,
            "sys_msg": final_system_prompt, # Pass the combined system prompt
            "input": filled_prompt # The formatted user input
        }

        # Create message object for streaming response
        msg_contentgen = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Stream the response
                async for chunk in rx_lifecycle_create.astream(query):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                # Update chat history
                chat_history_lifecycle_creator.append(HumanMessage(content=filled_prompt))
                # Store the AI message, potentially including the specific system prompt used?
                # For simplicity, just storing the content now.
                chat_history_lifecycle_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_lifecycle_creator", chat_history_lifecycle_creator)

                await msg_contentgen.send()
                logging.info("Successfully generated and streamed response for Lifecycle content.")
                return # Exit after success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during LLM call for Lifecycle content: {e}")
                if attempt == max_retries - 1:
                    await msg_contentgen.update(content=f"Sorry, I encountered an error after {max_retries} attempts generating lifecycle content. Please try again later.")
                # await cl.sleep(1)

    except Exception as e:
        # Catch errors during prompt formatting or other logic before the LLM call
        logging.error(f"Error processing lifecycle selections: {e}")
        await cl.Message(content="An error occurred while processing your lifecycle selections. Please check the logs and try again.").send()

@cl.on_message
async def on_message(message: cl.Message):
    """
    Handles incoming user messages after the initial setup or form submission.

    Routes the message to the appropriate Langchain chain based on the
    active chat profile and continues the conversation. Handles file attachments
    in the message for relevant profiles (Refinement, Policy).

    Args:
        message (cl.Message): The message object from the user, potentially
                              containing text content and file elements.
    """
    chat_profile = cl.user_session.get("chat_profile")
    user_msg = message.content # The text part of the user's message
    logging.info(f"Received message for profile '{chat_profile}': '{user_msg[:50]}...'") # Log truncated message

    # --- Route based on Chat Profile ---

    # --- Web & App Content Creation Follow-up ---
    if chat_profile == "Web & App Content Creation":
        rx_content_create = cl.user_session.get("rx_content_creator")
        chat_history_content_creator = cl.user_session.get("chat_history_content_creator")
        # Check if the initial form was submitted (history should not be empty)
        if not chat_history_content_creator:
            logging.warning("Received follow-up message in Web/App profile before initial form submission.")
            await cl.Message(content="Please fill and submit the questions above to start generating content.").send()
            return

        # Prepare query and config for the chain
        query = {"chat_history": chat_history_content_creator, "input": user_msg}
        # Config for potential stateful operations (though memory saver isn't used here)
        config = {"configurable": {"thread_id": message.thread_id}}

        # Create message for streaming response
        msg_contentgen = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Stream response
                async for chunk in rx_content_create.astream(query, config=config):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                # Update history
                chat_history_content_creator.append(HumanMessage(content=user_msg))
                chat_history_content_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_content_creator", chat_history_content_creator)

                await msg_contentgen.send()
                logging.info("Successfully generated and streamed follow-up response for Web/App content.")
                return # Exit on success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during follow-up LLM call for Web/App content: {e}")
                if attempt == max_retries - 1:
                    await msg_contentgen.update(content=f"Sorry, I encountered an error after {max_retries} attempts. Please try again later.")
                # await cl.sleep(1)

    # --- Content Refinement Interaction ---
    elif chat_profile == "Content Refinement":
        rx_copywriter = cl.user_session.get("rx_copywriter")
        chat_history_copywriter = cl.user_session.get("chat_history_copywriter")
        config = {"configurable": {"thread_id": message.thread_id}}

        # Check for file attachments in the message
        if message.elements:
            # Assuming only one file attachment is handled per message here
            file_element = message.elements[0]
            file_path = file_element.path # Chainlit provides the path to the temp file
            file_name = file_element.name
            extracted_doc_content = ""
            try:
                # Open the file from the path provided by Chainlit
                with open(file_path, "rb") as f:
                    if file_name.lower().endswith('.docx'):
                        extracted_doc_content = read_docx(f)
                        file_type_desc = "Word document"
                    elif file_name.lower().endswith('.pdf'):
                        extracted_doc_content = read_pdf(f)
                        file_type_desc = "PDF document"
                    else:
                        file_type_desc = "attached file" # Generic fallback
                        logging.warning(f"Received unsupported file type in Content Refinement: {file_name}")

                # If text was extracted, prepend it to the user message
                if extracted_doc_content:
                    user_msg = (
                        f"{user_msg}\n\n--- Content from attached {file_type_desc} ('{file_name}') ---\n"
                        f"{extracted_doc_content}\n"
                        f"--- End of attached content ---"
                    )
                    logging.info(f"Added content from attached file '{file_name}' to refinement prompt.")
                else:
                     logging.warning(f"Could not extract text from attached file: {file_name}")
                     # Optionally inform the user:
                     # await cl.Message(content=f"Could not extract text from the attached file: {file_name}").send()

            except FileNotFoundError:
                 logging.error(f"File not found at path provided by Chainlit: {file_path}")
                 await cl.Message(content=f"Error accessing the attached file: {file_name}. Please try attaching it again.").send()
            except Exception as e:
                 logging.error(f"Error processing attached file '{file_name}' in Content Refinement: {e}")
                 await cl.Message(content=f"Error processing the attached file: {file_name}. Please try again.").send()


        # Prepare query and message for streaming
        query = {"chat_history": chat_history_copywriter, "input": user_msg}
        msg_copywriter = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Stream response
                async for chunk in rx_copywriter.astream(query, config=config):
                    await msg_copywriter.stream_token(chunk)
                    full_msg += chunk

                # Update history
                chat_history_copywriter.append(HumanMessage(content=user_msg)) # User message potentially includes file content
                chat_history_copywriter.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_copywriter", chat_history_copywriter)

                await msg_copywriter.send()
                logging.info("Successfully generated and streamed response for Content Refinement.")
                return # Exit on success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during LLM call for Content Refinement: {e}")
                if attempt == max_retries - 1:
                    await msg_copywriter.update(content=f"Sorry, I encountered an error after {max_retries} attempts refining content. Please try again later.")
                # await cl.sleep(1)
    
    # --- Arabic Content Translation Interaction ---
    elif chat_profile == "Content Translation":
        rx_translation = cl.user_session.get("rx_translation")
        chat_history_translator = cl.user_session.get("chat_history_translator")
        config = {"configurable": {"thread_id": message.thread_id}}

        # Check for file attachments in the message
        if message.elements:
            # Assuming only one file attachment is handled per message here
            file_element = message.elements[0]
            file_path = file_element.path # Chainlit provides the path to the temp file
            file_name = file_element.name
            extracted_doc_content = ""
            try:
                # Open the file from the path provided by Chainlit
                with open(file_path, "rb") as f:
                    if file_name.lower().endswith('.docx'):
                        extracted_doc_content = read_docx(f)
                        file_type_desc = "Word document"
                    elif file_name.lower().endswith('.pdf'):
                        extracted_doc_content = read_pdf(f)
                        file_type_desc = "PDF document"
                    else:
                        file_type_desc = "attached file" # Generic fallback
                        logging.warning(f"Received unsupported file type in Content Translation: {file_name}")

                # If text was extracted, prepend it to the user message
                if extracted_doc_content:
                    user_msg = (
                        f"{user_msg}\n\n--- Content from attached {file_type_desc} ('{file_name}') ---\n"
                        f"{extracted_doc_content}\n"
                        f"--- End of attached content ---"
                    )
                    logging.info(f"Added content from attached file '{file_name}' to translate prompt.")
                else:
                     logging.warning(f"Could not extract text from attached file: {file_name}")
                     # Optionally inform the user:
                     # await cl.Message(content=f"Could not extract text from the attached file: {file_name}").send()

            except FileNotFoundError:
                 logging.error(f"File not found at path provided by Chainlit: {file_path}")
                 await cl.Message(content=f"Error accessing the attached file: {file_name}. Please try attaching it again.").send()
            except Exception as e:
                 logging.error(f"Error processing attached file '{file_name}' in Content Translator: {e}")
                 await cl.Message(content=f"Error processing the attached file: {file_name}. Please try again.").send()


        # Prepare query and message for streaming
        query = {"chat_history": chat_history_translator, "input": user_msg}
        msg_translator = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Stream response
                async for chunk in rx_translation.astream(query, config=config):
                    await msg_translator.stream_token(chunk)
                    full_msg += chunk

                # Update history
                chat_history_translator.append(HumanMessage(content=user_msg)) # User message potentially includes file content
                chat_history_translator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_translator", chat_history_translator)

                await msg_translator.send()
                logging.info("Successfully generated and streamed response for Content Translator.")
                return # Exit on success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during LLM call for Content Translator: {e}")
                if attempt == max_retries - 1:
                    await msg_translator.update(content=f"Sorry, I encountered an error after {max_retries} attempts to translate content. Please try again later.")
                # await cl.sleep(1)

    # --- Lifecycle Content Creation Follow-up ---
    elif chat_profile == "Lifecycle Content Creation":
        rx_lifecycle_create = cl.user_session.get("rx_lifecycle_creator")
        chat_history_lifecycle_creator = cl.user_session.get("chat_history_lifecycle_creator")
        # Check if initial form was submitted
        if not chat_history_lifecycle_creator:
            logging.warning("Received follow-up message in Lifecycle profile before initial form submission.")
            await cl.Message(content="Please start a new chat or submit the form to generate lifecycle content.").send()
            return

        # Prepare query - Note: This uses the *original* base system prompt,
        # not necessarily one adjusted with email templates from the initial submission.
        # If context from the initial selections (like email template) is needed for follow-ups,
        # the system prompt logic might need adjustment here or history management.
        query = {
            "chat_history": chat_history_lifecycle_creator,
            "sys_msg": SYSTEM_LIFECYCLE_PROMPT, # Using the base system prompt for follow-ups
            "input": user_msg
        }
        config = {"configurable": {"thread_id": message.thread_id}}

        # Create message for streaming
        msg_contentgen = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Stream response
                async for chunk in rx_lifecycle_create.astream(query, config=config):
                    await msg_contentgen.stream_token(chunk)
                    full_msg += chunk

                # Update history
                chat_history_lifecycle_creator.append(HumanMessage(content=user_msg))
                chat_history_lifecycle_creator.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history_lifecycle_creator", chat_history_lifecycle_creator)

                await msg_contentgen.send()
                logging.info("Successfully generated and streamed follow-up response for Lifecycle content.")
                return # Exit on success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during follow-up LLM call for Lifecycle content: {e}")
                if attempt == max_retries - 1:
                    await msg_contentgen.update(content=f"Sorry, I encountered an error after {max_retries} attempts. Please try again later.")
                # await cl.sleep(1)

    # --- RX Policy Generation Interaction ---
    elif chat_profile == "RX Policy Generation":
        # Check for and process file attachments, similar to Content Refinement
        if message.elements:
            file_element = message.elements[0]
            file_path = file_element.path
            file_name = file_element.name
            extracted_doc_content = ""
            try:
                with open(file_path, "rb") as f:
                    if file_name.lower().endswith('.docx'):
                        extracted_doc_content = read_docx(f)
                        file_type_desc = "Word document"
                    elif file_name.lower().endswith('.pdf'):
                        extracted_doc_content = read_pdf(f)
                        file_type_desc = "PDF document"
                    else:
                        file_type_desc = "attached file"
                        logging.warning(f"Received unsupported file type in Policy Generation: {file_name}")

                if extracted_doc_content:
                    user_msg = (
                        f"{user_msg}\n\n--- Content from attached {file_type_desc} ('{file_name}') ---\n"
                        f"{extracted_doc_content}\n"
                        f"--- End of attached content ---"
                    )
                    logging.info(f"Added content from attached file '{file_name}' to policy prompt.")
                else:
                    logging.warning(f"Could not extract text from attached file: {file_name}")
                    # await cl.Message(content=f"Could not extract text from the attached file: {file_name}").send()

            except FileNotFoundError:
                 logging.error(f"File not found at path provided by Chainlit: {file_path}")
                 await cl.Message(content=f"Error accessing the attached file: {file_name}. Please try attaching it again.").send()
            except Exception as e:
                 logging.error(f"Error processing attached file '{file_name}' in Policy Generation: {e}")
                 await cl.Message(content=f"Error processing the attached file: {file_name}. Please try again.").send()


        # Retrieve history and chain
        chat_history = cl.user_session.get("chat_history")
        rx_policy = cl.user_session.get("rx_policy")

        # Remove the initial welcome message if it hasn't been removed yet
        welcome_msg = cl.user_session.get("welcome_msg")
        if not cl.user_session.get("welcome_msg_removed") and welcome_msg:
            await welcome_msg.remove()
            cl.user_session.set("welcome_msg_removed", True)
            logging.info("Removed welcome message for Policy Generation.")

        # Prepare query and config
        query = {"chat_history": chat_history, "input": user_msg}
        config = {"configurable": {"thread_id": message.thread_id}}

        # Create message for streaming
        msg = cl.Message(content="", author="Riyadh Air")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_msg = ""
                # Use a Chainlit Step for better UI grouping/visibility during generation
                async with cl.Step(name="Generating Policy Content", show_input=False) as step: # Renamed step
                    step.input = user_msg # Optionally show user input in the step details
                    # Stream response within the step
                    async for chunk in rx_policy.astream(query, config=config):
                        await msg.stream_token(chunk)
                        full_msg += chunk
                    step.output = full_msg # Set the final output for the step

                # Update history
                chat_history.append(HumanMessage(content=user_msg)) # User message potentially includes file content
                chat_history.append(AIMessage(content=full_msg))
                cl.user_session.set("chat_history", chat_history)

                await msg.send()
                logging.info("Successfully generated and streamed response for Policy Generation.")
                return # Exit on success

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{max_retries}: Error during LLM call for Policy Generation: {e}")
                if attempt == max_retries - 1:
                    # Update the message content directly on error
                    await msg.update(content=f"Sorry, I encountered an error after {max_retries} attempts generating the policy. Please try again later.")
                # await cl.sleep(1)
    else:
        # Handle cases where the chat profile is unknown or not set
        logging.error(f"Received message but chat profile '{chat_profile}' is not recognized or handled.")
        await cl.Message(content="Sorry, I'm not sure how to handle this request in the current mode. Please select a valid chat profile.").send()