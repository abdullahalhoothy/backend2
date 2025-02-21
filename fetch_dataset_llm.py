from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import StructuredTool
import json
import requests
from config_factory import CONF
from all_types.myapi_dtypes import ReqLLMDataset, ResLLMDataset

# Function to fetch Approved_cities, Approved_countries and Approved_Categories

def fetch_approved_data(url: str):
    """
    Sends a GET request to the specified API endpoint.

    :param url: The API URL to call.
    :return: Response JSON or None if the request fails.
    """
    headers = {"accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an error for HTTP failures (4xx, 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None  # Return None if the request fails

def extract_countries_and_cities(data):
    """
    Extracts separate lists of countries and cities from the given data.

    :param data: Dictionary containing countries as keys and city details as values.
    :return: Tuple (countries_list, cities_list)
    """
    if not data:  # Handle None or empty data safely
        return [], []

    countries = list(data.keys())  # Extract country names
    cities = [city["name"] for cities in data.values() for city in cities]  # Extract all city names

    return countries, cities


def calculate_cost(Request: ReqLLMDataset)->ResLLMDataset:
    api_requests = [Request.fetch_dataset_request]
    API_ENDPOINT = CONF.calculate_cost
    responses = []
    total_cost = 0
    
    for api_request in api_requests:
        try:
            payload = {
                "message": "Cost calculation request from LLM",
                "request_info": {},  # Add relevant request info if needed
                "request_body": api_request.dict()
            }
            
            response = requests.post(
                API_ENDPOINT,
                json=payload
            )
            response.raise_for_status()
            total_cost += response.json()["data"]["cost"]
            responses.append(response.json())
        except requests.exceptions.RequestException as e:
            responses.append({"error": f"API request failed for {api_request}: {e}"})
    Request.cost = str(total_cost)

    return Request

def extract_location_info(Request: ReqLLMDataset) -> ResLLMDataset:
    """
    Uses an LLM call to extract location-based information from the query.

    Args:
        query (str): The query string to process.

    Returns:
        ReqLLMDataset: An instance of ReqLLMDataset containing extracted information.
    """
    country_city_data = fetch_approved_data(CONF.country_city)
    category_data = fetch_approved_data(CONF.nearby_categories)
    if country_city_data and "data" in country_city_data:
        Approved_Countries, Approved_Cities = extract_countries_and_cities(country_city_data["data"])
    else:
        Approved_Countries, Approved_Cities = [], []
        print("Warning: Failed to fetch approved countries and cities.")

    if category_data and "data" in category_data:
        Approved_Categories = category_data["data"]
    else:
        Approved_Categories = []
        print("Warning: Failed to fetch approved categories.")

    
    if (Request.requestStatus)=="Processed":
        return Request

    system_message = """You are an intelligent assistant that extracts structured data for a location-based search API. Only process queries that specifically request 
                        information about places in a city or country. Add the country name automatically and try to be consistent.
                        
                        Reject queries that:
                        1. Do not explicitly mention searching for a place (e.g., "How to dance in Dubai" or "Weather in Paris").
                        2. Are general knowledge or instructional queries (e.g., "History of London" or "How to apply for a visa").
                        3. Contain inappropriate, offensive, illegal, or nonsensical requests.
                        4. Do not belong to the approved categories for places (e.g. tea shops is not an approved category)
                        5. Do not belong to approved cities and countries.
                        6. Contain multiple cities or countries
                        7. Do not contain a city name
                        
                        #Approved Categories for Places#
                        {Approved_Categories}
                        # Approved Countries #
                        {Approved_Countries}                     
                        # Approved Cities #
                        {Approved_Cities} 
                        
                        #Formation of Boolean Queries
                        1. Boolean Query is a string formed by joining all the places in the query by 'OR' / 'AND'
                        2. Examine the user query semantically and construct a Boolean Query



                    """
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.0)
    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        ("human", "{text}",),
    ]
    )

    
    query = Request.query
    chain = prompt | llm.with_structured_output(schema=ReqLLMDataset)
    response = chain.invoke({
    "text": query,
    "Approved_Cities": Approved_Cities,
    "Approved_Categories": Approved_Categories,
    "Approved_Countries":Approved_Countries

    })

    
    response.requestStatus = "Processed"
    return response


def process_llm_query(Request: ReqLLMDataset)-> ResLLMDataset:
    query = Request.query
    text = "User Query = "+Request.query + "\n" + " ReqLLMDataset = " + Request.json() 
    system_message = """
                    You are a helpful assistant for a location based API. Your task is to calculate cost for a user query passed.
                    #Rules to Follow#
                    1. Cost tool should not make any changes except 'cost' field.
                    2. It should not modify Boolean Query in any circumstances.
                    3. Validate the input and check that it contains a city name and a place.
                    4. Validate the output also.

                    
                """
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.0)
    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        ("human", "{text}"),
         ("placeholder", "{chat_history}"),
        ("placeholder", "{agent_scratchpad}")
    ]
    )

    location_info_tool = StructuredTool.from_function(
        func=extract_location_info,
        name="extract_location_info",
        description="Takes query parameter of ReqLLMDataset and parses it to extract data. Returns an ReqLLMDataset Object"
    )
    
    cost_calculation_tool = StructuredTool.from_function(
        func=calculate_cost,
        name="cost_calculation_tool",
        description="Makes an API call to the endpoint for extracting cost information from an ReqLLMDataset object.",
        return_direct = True
    )
    
    
    # Group tools
    tools = [location_info_tool, cost_calculation_tool]
    
    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create the agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    response = agent_executor.invoke({"text": text})
    return response["output"]
