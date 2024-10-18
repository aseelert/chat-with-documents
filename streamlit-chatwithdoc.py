import streamlit as st
import sqlite3
import requests

# Database setup for storing API key and deployment URL
def init_db():
    conn = sqlite3.connect("api_data.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            deployment_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_credentials():
    conn = sqlite3.connect("api_data.db")
    c = conn.cursor()
    c.execute("SELECT api_key, deployment_url FROM credentials ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def save_credentials(api_key, deployment_url):
    conn = sqlite3.connect("api_data.db")
    c = conn.cursor()
    c.execute("INSERT INTO credentials (api_key, deployment_url) VALUES (?, ?)", (api_key, deployment_url))
    conn.commit()
    conn.close()

# IBM Cloud token retrieval function
def get_ibm_token(api_key):
    token_url = 'https://iam.cloud.ibm.com/identity/token'
    data = {
        "apikey": api_key,
        "grant_type": 'urn:ibm:params:oauth:grant-type:apikey'
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("Failed to retrieve token")
        return None

# Function to perform a search query to the GenAI model
def perform_search(search_query, token, deployment_url):
    header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}

    # Example payload for search functionality
    messages = [{"role": "user", "content": search_query}]  # Search query is passed as the message

    # Payload for the search use case
    payload = {
        "input_data": [
            {
                "fields": ["Search", "access_token"],  # Adjust based on your API's expected fields
                "values": [messages, [token]]  # Pass messages as search query and token if needed
            }
        ]
    }

    # Log the payload for debugging
    #st.write(f"Payload being sent: {payload}")

    response = requests.post(deployment_url, json=payload, headers=header)

    if response.status_code == 200:
        try:
            return response.json()  # Adjust parsing based on your API's response structure
        except IndexError as e:
            st.error(f"Error parsing response: {e}")
            st.error(response.json())  # Show raw response for further debugging
            return None
    else:
        st.error(f"Error fetching search results: {response.status_code} - {response.text}")
        return None

# Function to display search results in Streamlit chat style
def display_results(results):
    predictions = results['predictions'][0]

    # Extract the proximity search results and the generated response
    proximity_results = predictions['values'][0]
    generated_response = predictions['values'][1]

    # Display the generated response in markdown format
    st.write(f"**Generated Response:**\n\n{generated_response}")

    # Optionally display the proximity search results
    st.markdown("**Proximity Search Results:**")
    for result in proximity_results:
        metadata = result['metadata']
        score = result['score']
        st.write(f"Asset: {metadata['asset_name']} (Score: {score:.2f})")
        st.write(f"Range: {metadata['from']} - {metadata['to']}")
        #st.write(f"[View Document]({metadata['url']})")
        st.write("---")  # Line separator for better readability

# Initialize the database
init_db()

# Fetch stored credentials or use defaults
credentials = get_credentials()
default_api_key = "gVmN-c15p93uhLy"  # Replace with your default API key or make this empty
default_deployment_url = "https://us-south.ml.cloud.ibm.com/ml/v4/deployments/02f00442-5529-4f26-beaa-f7db8e3dfe40/predictions?version=2021-05-01"

if credentials:
    default_api_key, default_deployment_url = credentials

# Streamlit UI
st.title("Search with IBM GenAI Model")

# Input fields for API key and deployment URL
api_key = st.text_input("Enter your API key", value=default_api_key, type="password")
deployment_url = st.text_input("Enter deployment URL", value=default_deployment_url)

# Save API key and deployment URL if entered for the first time
if st.button("Save API Key and URL"):
    if api_key and deployment_url:
        save_credentials(api_key, deployment_url)
        st.success("API Key and URL saved!")

# Input text from the user
search_query = st.chat_input("Enter your search query")


if search_query:
        # Get IBM token
    token = get_ibm_token(api_key)

    if token:
        # Perform the search query using the provided deployment
        search_response = perform_search(search_query, token, deployment_url)

        # Display the response in a formatted way
        if search_response:
            display_results(search_response)
else:
    st.warning("Please enter a search query before sending.")
