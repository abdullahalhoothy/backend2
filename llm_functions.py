from langchain_core.pydantic_v1 import BaseModel, Field, validator
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import StructuredTool
import json
import requests
from config_factory import CONF
from all_types.myapi_dtypes import LLMFetchDataset

def calculate_cost(Request: LLMFetchDataset)->LLMFetchDataset:
    api_requests = [Request.fetch_dataset_request]
    API_ENDPOINT = CONF.cost_calculator
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


Approved_Cities = ["Dubai", "AbuDhabi", "Sharjah", "Toronto", "Vancouver", "Montreal", "Riyadh", "Jedda", "Mecca"]

Approved_Categories = [
    "car_dealer", "car_rental", "car_repair", "car_wash", "electric_vehicle_charging_station", "gas_station", "parking", "rest_stop",
    "art_gallery", "museum", "performing_arts_theater", "library", "preschool", "primary_school", "school", "secondary_school", "university",
    "amusement_center", "amusement_park", "aquarium", "banquet_hall", "bowling_alley", "casino", "community_center", "convention_center",
    "cultural_center", "dog_park", "event_venue", "hiking_area", "historical_landmark", "marina", "movie_rental", "movie_theater",
    "national_park", "night_club", "park", "tourist_attraction", "visitor_center", "wedding_venue", "zoo", "accounting", "atm", "bank",
    "american_restaurant", "bakery", "bar", "barbecue_restaurant", "brazilian_restaurant", "breakfast_restaurant", "brunch_restaurant",
    "cafe", "chinese_restaurant", "coffee_shop", "fast_food_restaurant", "french_restaurant", "greek_restaurant", "hamburger_restaurant",
    "ice_cream_shop", "indian_restaurant", "indonesian_restaurant", "italian_restaurant", "japanese_restaurant", "korean_restaurant",
    "lebanese_restaurant", "meal_delivery", "meal_takeaway", "mediterranean_restaurant", "mexican_restaurant", "middle_eastern_restaurant",
    "pizza_restaurant", "ramen_restaurant", "restaurant", "sandwich_shop", "seafood_restaurant", "spanish_restaurant", "steak_house",
    "sushi_restaurant", "thai_restaurant", "turkish_restaurant", "vegan_restaurant", "vegetarian_restaurant", "vietnamese_restaurant",
    "administrative_area_level_1", "administrative_area_level_2", "country", "locality", "postal_code", "school_district", "city_hall",
    "courthouse", "embassy", "fire_station", "local_government_office", "police", "post_office", "dental_clinic", "dentist", "doctor",
    "drugstore", "hospital", "medical_lab", "pharmacy", "physiotherapist", "spa", "bed_and_breakfast", "campground", "camping_cabin",
    "cottage", "extended_stay_hotel", "farmstay", "guest_house", "hostel", "hotel", "lodging", "motel", "private_guest_room", "resort_hotel",
    "rv_park", "church", "hindu_temple", "mosque", "synagogue", "barber_shop", "beauty_salon", "cemetery", "child_care_agency", "consultant",
    "courier_service", "electrician", "florist", "funeral_home", "hair_care", "hair_salon", "insurance_agency", "laundry", "lawyer",
    "locksmith", "moving_company", "painter", "plumber", "real_estate_agency", "roofing_contractor", "storage", "tailor",
    "telecommunications_service_provider", "travel_agency", "veterinary_care", "auto_parts_store", "bicycle_store", "book_store",
    "cell_phone_store", "clothing_store", "convenience_store", "department_store", "discount_store", "electronics_store",
    "furniture_store", "gift_shop", "grocery_store", "hardware_store", "home_goods_store", "home_improvement_store", "jewelry_store",
    "liquor_store", "market", "pet_store", "shoe_store", "shopping_mall", "sporting_goods_store", "store", "supermarket", "wholesaler",
    "athletic_field", "fitness_center", "golf_course", "gym", "playground", "ski_resort", "sports_club", "sports_complex", "stadium",
    "swimming_pool", "airport", "bus_station", "bus_stop", "ferry_terminal", "heliport", "light_rail_station", "park_and_ride",
    "subway_station", "taxi_stand", "train_station", "transit_depot", "transit_station", "truck_stop"
]

Approved_Countries = ["United Arab Emirates", "Saudi Arabia", "Canada"]

def extract_location_info(Request: LLMFetchDataset) -> LLMFetchDataset:
    """
    Uses an LLM call to extract location-based information from the query.

    Args:
        query (str): The query string to process.

    Returns:
        LLMFetchDataset: An instance of LLMFetchDataset containing extracted information.
    """
    
    if (Request.requestStatus)=="Processed":
        return Request

    system_message = """You are an intelligent assistant that extracts structured data for a location-based search API. Only process queries that specifically request information about places 
                        in a city or country. Add the country name automatically.
                        
                        Reject queries that:
                        1. Do not explicitly mention searching for a place (e.g., "How to dance in Dubai" or "Weather in Paris").
                        2. Are general knowledge or instructional queries (e.g., "History of London" or "How to apply for a visa").
                        3. Contain inappropriate, offensive, illegal, or nonsensical requests.
                        4. Do not belong to the approved categories for places (e.g. tea shops is not an approved category)
                        5. Do not belong to approved cities and countries.
                        6. Contain multiple cities or countries
                        
                        #Approved Categories for Places#
                        {Approved_Categories}
                        # Approved Countries #
                        {Approved_Categories}
                         
                        
                        # Approved Cities #
                        {Approved_Cities} 
                        
                        7. Boolean Query is a string formed by joining all the places in the query by OR

                    """
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.0)
    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message),
        ("human", "{text}"),
    ]
    )

    
    query = Request.query
    chain = prompt | llm.with_structured_output(schema=LLMFetchDataset)
    response = chain.invoke({"text": query})
    
    response.requestStatus = "Processed"
    return response


def process_llm_query_ep(Request: LLMFetchDataset):
    query = Request.query
    text = "User Query = "+Request.query + "\n" + " LLMFetchDataset = " + Request.json() 
    system_message = """
                    You are a helpful assistant for a location based API. Your task is to calculate cost for a user query passed.
                    #Rules to Follow#
                    1. If one tool makes changes to data then use then use there returned value for subsequent calls.
                    
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
        description="Takes query parameter of LLMFetchDataset and parses it to extract data. Returns an LLMFetchDataset Object"
    )
    
    cost_calculation_tool = StructuredTool.from_function(
        func=calculate_cost,
        name="cost_calculation_tool",
        description="Makes an API call to the endpoint for extracting cost information from an LLMFetchDataset object.",
        return_direct = True
    )
    
    
    # Group tools
    tools = [location_info_tool, cost_calculation_tool]
    
    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create the agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    response = agent_executor.invoke({"text": text})
    return response
