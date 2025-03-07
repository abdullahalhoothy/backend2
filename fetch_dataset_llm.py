from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, model_validator
import requests
from all_types.response_dtypes import ResLLMFetchDataset
from all_types.myapi_dtypes import ReqLLMFetchDataset
from cost_calculator import calculate_cost
from config_factory import CONF
#baseurl = "http://37.27.195.216:8000"

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

async def process_llm_query(req:ReqLLMFetchDataset):
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

    system_message = """You are an intelligent assistant that extracts structured data for a location-based search API. 
    Your primary function is to process location-based search queries and format them appropriately.
    # CRITICAL REQUIREMENTS
    - MUST HAVE: Exactly one approved city name in the query from Approved Cities:{Approved_Cities}
    - MUST NOT HAVE: Multiple city names in the same query
    - These requirements are non-negotiable - immediately reject any query that violates them
    # QUERY PROCESSING RULES
    - Only process queries that explicitly request information about places within a single approved city.
    - Automatically add the corresponding country name to maintain consistency.
    - Ensure consistent results for identical queries by following a deterministic analysis process.
    # REJECTION CRITERIA
    Reject queries that:
    1. Do not contain an approved city name
    2. Contain multiple city names
    3. Do not explicitly seek physical places/venues (e.g., "Weather in Paris" or "History of London")
    4. Are general knowledge or instructional in nature (e.g., "How to apply for a visa in Singapore")
    5. Contain inappropriate, offensive, illegal, or nonsensical content
    6. Reference place categories not in the approved list: {Approved_Categories}
    7. Mention countries not in the approved list: {Approved_Countries}
    - 
    # Boolean Query Construction
    - The boolean query must only contain approved category terms connected by 'AND' and 'OR' operators
    - Analyze the semantic relationship between place categories in the query:
    - Use 'OR' for alternatives (e.g., "restaurants or cafes" → "RESTAURANT OR CAFE")
    - Use 'AND' for combinations (e.g., "hotels with restaurants" → "HOTEL AND RESTAURANT")
    - For complex queries with both independent and combined categories:
    - Group related terms with parentheses
    - Example: "ATMs and supermarkets with ATMs" → "ATM OR (SUPERMARKET AND ATM)"
    - Always use the standardized category names from the approved list
    For invalid queries, politely explain why the query cannot be processed, specifically mentioning the requirement for exactly one approved city name.
    """
    model = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.0)

    parser = PydanticOutputParser(pydantic_object=ResLLMFetchDataset)
    
    prompt = PromptTemplate(
        template="{system_message}.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    prompt_and_model = prompt | model
    output = prompt_and_model.invoke({"query": req.query,"system_message":system_message})
    outputResponse = parser.invoke(output)
    if outputResponse.body is None:
        return outputResponse
    else:
        costData = await calculate_cost(outputResponse.body)
        outputResponse.cost = str(costData.cost)
        return (outputResponse)
    