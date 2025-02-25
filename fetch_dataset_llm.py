from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, model_validator
import requests
from all_types.response_dtypes import ResLLMFetchDataset
from all_types.myapi_dtypes import ReqLLMFetchDataset
from cost_calculator import calculate_cost
from config_factory import CONF


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
    model = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.0)

    parser = PydanticOutputParser(pydantic_object=ResLLMFetchDataset)
    
    prompt = PromptTemplate(
        template="{system_message}.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    # And a query intended to prompt a language model to populate the data structure.
    prompt_and_model = prompt | model
    output = prompt_and_model.invoke({"query": req.query,"system_message":system_message})
    outputResponse = parser.invoke(output)
    if outputResponse.fetch_dataset_request is None:
        return outputResponse
    else:
        costData = await calculate_cost(outputResponse.fetch_dataset_request)
        outputResponse.cost = str(costData.cost)
        return (outputResponse)
    