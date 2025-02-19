from all_types.myapi_dtypes import ReqGradientColorBasedOnZone
from all_types.response_dtypes import ValidationResult

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
import os 






class ExplanationAgent:
    def __init__(self):
        self.model = self.__getmodel()
        self.template = ChatPromptTemplate.from_messages([
            ("system", "You are an assistant that explains the results of a map feature recoloring request based on the user's prompt."),
            ("human", "User Prompt: {user_prompt}\nResults: {results}")
        ])
        self.chain=self.template|self.model

    def __getmodel(self):
    #key=os.environ["DEEPSEEK_API_KEY"]
      api_key=os.environ["GEMINI_API_KEY"] # YOur API KEY
      base_url="https://generativelanguage.googleapis.com/v1beta"
      client=ChatOpenAI(
          base_url=base_url,
          api_key=api_key,
          model="gemini-2.0-flash-exp"
      )
      return client

    def __call__(self, user_prompt, results):
        response = self.chain.invoke(
            {
              "user_prompt": user_prompt,
              "results": results
            }
        )
        return response

class ReqGradientColorBasedOnZoneAgent:
  def __init__(self):
    self.model=self.__getmodel()
    self.parser=PydanticOutputParser(pydantic_object=ReqGradientColorBasedOnZone)
    self.system_prompt=self.__create_system_prompt()
    self.format_instruction=self.parser.get_format_instructions()
    self.template=ChatPromptTemplate.from_messages(
        [
            ("system",self.system_prompt),
            ("human","{input_text}")
        ]
    )
    self.chain=self.template|self.model

  def __getmodel(self):
    #key=os.environ["DEEPSEEK_API_KEY"]
    api_key=os.environ["GEMINI_API_KEY"]
    base_url="https://generativelanguage.googleapis.com/v1beta"
    client=ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model="gemini-2.0-flash-exp"
    )
    return client
  
  def __create_system_prompt(self):
    """
    Creates a system prompt with dynamic layer information.
    
    Args:
        available_layers: Dictionary of available layers with their IDs and names
        Example: {
            "banks": {"id": "l1d77aec5-0c4c-4733-9297-bb6bc4f2a41a", "name": "SA-RIY-bank"},
            "atms": {"id": "lb578d63c-512e-4852-81a8-0760062c2000", "name": "ATMs"}
        }
    """
    SYSTEM_PROMPT="""
      You are an AI system designed to process natural language requests related to recoloring and filtering map features. Your role is to convert these requests into structured JSON data based on predefined layers and operations.
      STRICT RESPONSE RULES:
      1. If the user's request is **unrelated** to map features, recoloring, or filtering, respond **exactly** with:
        ```
        "sorry i don't understand"
        ```
      2. If the request relates to map features but **cannot be processed** with the available tools, respond **exactly** with:
        ```
        "please word your request differently"
        ```
      3. If the user requests **layers that do not exist** in the available list (see `AVAILABLE LAYERS`), respond **exactly** with:
        ```
        "please select layers correctly"
        ```
      4. If the request is valid and can be processed, return a **JSON object** following the schema provided below.

      ---
      AVAILABLE LAYERS:
      {available_layers}

      SUPPORTED OPERATIONS:
      - Recolor based on distance:
        - Drive time (e.g., "features within X minutes drive time")
        - Radius (e.g., "features within X meters")
      - Recolor based on feature names (e.g., "highlight specific names")
      - Apply color gradients based on ratings or other numeric metrics
      - Filter features by name

      ---
      RULES FOR PROCESSING REQUESTS:
      - Always use hex color codes (e.g., `#FF0000` for red).
      - For drive time-based recoloring:
        - Set `coverage_property` to `"drive_time"`.
        - Specify `coverage_value` in minutes.
      - For radius-based recoloring:
        - Set `coverage_property` to `"radius"`.
        - Specify `coverage_value` in meters.
      - For rating-based recoloring, apply a color gradient.
      - For name-based filtering, set `color_based_on` to `"name"`.
      - Ensure `layer IDs` and `layer names` match exactly with `AVAILABLE LAYERS`.
      - Always return `color_grid_choice` as an array, even if it contains only one color.
      - If a request mentions both a distance (e.g., meters) and a drive-related term (e.g., "drive from"), prioritize coverage_property = "radius" unless the unit explicitly mentions minutes.
      - Use radius when distance units are in meters or kilometers, and drive_time when units are in minutes or hours.
      - For name-based filtering: 
        - `change_lyr_name` and `based_on_lyr_name` must be the same layer.
        - Apply the requested colors only to matching feature names.


      ---
      PREDEFINED COLOR GRADIENTS:
      1. Green to Red: `["#00ff00", "#33cc00", "#669900", "#996600", "#cc3300", "#ff0000"]`
      2. White to Black: `["#ffffff", "#cccccc", "#999999", "#666666", "#333333", "#000000"]`
      3. Blue to Red: `["#0000ff", "#3333cc", "#666699", "#996666", "#cc3333", "#ff0000"]`

      ---
      OUTPUT FORMAT:
      For valid requests, return only a JSON object matching this schema:
      {format_instruction}

      ---
      EXAMPLE REQUEST & RESPONSE:
      User Input:
      > "Recolor ATMs within 100 meters of banks using a green-to-red gradient based on rating."

      Expected JSON Output:
      {{
          "color_grid_choice": ["#00ff00", "#33cc00", "#669900", "#996600", "#cc3300", "#ff0000"],
          "change_lyr_id": "lb578d63c-512e-4852-81a8-0760062c2000",
          "change_lyr_name": "ATMs",
          "based_on_lyr_id": "l1d77aec5-0c4c-4733-9297-bb6bc4f2a41a",
          "based_on_lyr_name": "SA-RIY-bank",
          "coverage_property": "radius",
          "coverage_value": 100,
          "color_based_on": "rating",
          "list_names": []
      }}
      """
    return SYSTEM_PROMPT

  
  def __call__(self,input_text,available_layers):
    output=self.chain.invoke(
          {
              "input_text":input_text,
              "format_instruction":self.format_instruction,
              "available_layers":available_layers
          }
    )
    try:
      
      return self.parser.invoke(output)
    except Exception as e:
      raise Exception(str(output.content))
    



class PromptValidationAgent:
    def __init__(self):
        self.model = self.__getmodel()
        self.template = ChatPromptTemplate.from_messages([
            ("system", self.__create_system_prompt()),
            ("human", "{input_text}")
        ])
        self.parser=PydanticOutputParser(pydantic_object=ValidationResult)
        self.format_instruction=self.parser.get_format_instructions()
        self.chain = self.template | self.model | self.parser
    
    def __getmodel(self):
        api_key = os.environ["GEMINI_API_KEY"]
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        client = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model="gemini-2.0-flash-exp"
        )
        return client
    
    def __create_system_prompt(self):
        SYSTEM_PROMPT = """
        You are an AI system designed to validate user requests related to map feature recoloring and filtering. Your job is to determine if a request is:
        1. Complete (contains all necessary information)
        2. Makes sense (is logically coherent and possible to implement)
        3. Follows the established rules for map feature operations

        VALIDATION RULES:
        1. Request must be related to map features, recoloring, or filtering.
        2. Request must specify at least one layer that should be modified.
        3. Any layer types mentioned in the request MUST EXACTLY match one of the available layers by name (e.g., if user mentions "ATMs", there must be a layer with "ATM" or "atm" in its name).
        4. Layer name matching is case-insensitive but otherwise exact (e.g., "bank" matches "BANK" but not "banking").
        5. Request must specify what kind of operation to perform (recolor, filter, etc.).
        6. For coverage-based operations, must include a measurable value (distance/time).
        7. Color specifications should be clear if mentioned.
        8. For name-based filtering, must specify which names to filter by.
        9. If a request mentions multiple layers, ALL mentioned layers must exist in the available layers list.
        

        AVAILABLE LAYERS:
        {available_layers}

        SUPPORTED OPERATIONS:
        - Recolor based on distance:
          - Drive time (e.g., "features within X minutes drive time")
          - Radius (e.g., "features within X meters")
        - Recolor based on feature names (e.g., "highlight specific names")
        - Apply color gradients based on ratings or other numeric metrics
        - Filter features by name

        ---
        OUTPUT FORMAT:
        You must return a JSON object with the following structure:
        {format_instruction}
        example:
        {{
            "is_valid": boolean,
            "reason": string (only if is_valid is false),
            "suggestions": list of strings (suggestions for improvement if is_valid is false)
        }}

        EXAMPLES:
        
        Valid request:
        > "Recolor ATMs within 100 meters of banks using a green-to-red gradient based on rating."
        {{
            "is_valid": true
        }}
        
        Invalid request:
        > "Show me the weather forecast for tomorrow"
        {{
            "is_valid": false,
            "reason": "Request is unrelated to map features, recoloring, or filtering",
            "suggestions": ["Ask about map recoloring or filtering instead", "Specify which map layers you want to work with"]
        }}
        
        Incomplete request:
        > "Recolor features using a gradient"
        {{
            "is_valid": false,
            "reason": "Request is incomplete - missing which layer to recolor and based on what criteria",
            "suggestions": ["Specify which layer you want to recolor", "Mention if you want to recolor based on distance, rating, or other criteria", "Include any relevant values like distance or time"]
        }}
        """
        return SYSTEM_PROMPT
    
    def __call__(self, input_text: str, available_layers) -> ValidationResult:
        if available_layers is None or available_layers == "":
            return ValidationResult(
                is_valid=False,
                reason="No available layers provided",
                suggestions=["Invalid available_layers"]
            )
        
        if not isinstance(available_layers, dict) or not available_layers:
            return ValidationResult(
                is_valid=False,
                reason="Invalid available_layers",
                suggestions=["Please provide a non-empty dictionary of available layers"]
            )
        try:
          response = self.chain.invoke(
              {
                  "input_text": input_text,
                  "available_layers": available_layers,
                  "format_instruction":self.format_instruction
              }
          )
          return response
        except Exception as e:
            # Fallback in case parsing fails
            return ValidationResult(
                is_valid=False,
                reason=f"Failed to validate request: {str(e)}",
                suggestions=["Please try rephrasing your request"]
            )




class OutputValidationAgent:
    def __init__(self):
        self.model = self.__getmodel()
        self.template = ChatPromptTemplate.from_messages([
            ("system", self.__create_system_prompt()),
            ("human", "User Prompt: {user_prompt}\n\nProcessed Output: {processed_output}\n\nAvailable Layers: {available_layers}")
        ])
        self.parser=PydanticOutputParser(pydantic_object=ValidationResult)
        self.format_instruction=self.parser.get_format_instructions()
        self.chain = self.template | self.model | self.parser
    
    def __getmodel(self):
        api_key = os.environ["GEMINI_API_KEY"]
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        client = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model="gemini-2.0-flash-exp"
        )
        return client
    
    def __create_system_prompt(self):
        SYSTEM_PROMPT = """
        You are an AI system designed to validate whether the processed output from a map feature recoloring request correctly matches the user's intent in their prompt. 

        VALIDATION RULES:
        1. The processed output must correctly identify the layers to be modified based on the user's prompt.
        2. The selected color grid must match any color specifications mentioned in the prompt (e.g., "green to red").
        3. If the prompt specifies a distance/radius/drive time, the coverage_property and coverage_value must match.
        4. If the prompt mentions filtering by feature names, the list_names field must be populated appropriately.
        5. The color_based_on field must correctly reflect what the user wants to base the coloring on (e.g., "rating", "name").
        
        EVALUATIONS TO PERFORM:
        1. Layer Identification: Compare the layers mentioned in the prompt with the change_lyr_name and based_on_lyr_name in the output.
        2. Color Selection: Verify that color_grid_choice aligns with any color specifications in the prompt.
        3. Coverage Type: Check if coverage_property (radius/drive_time) matches what the user requested.
        4. Coverage Value: Ensure the coverage_value is appropriate for the mentioned distance/time.
        5. Coloring Basis: Confirm color_based_on field correctly represents the user's intent.
        
        OUTPUT FORMAT:
        You must return a JSON object with the following structure:
        {format_instruction}

        example:
        {{
            "is_valid": boolean,
            "reason": string (only if is_valid is false),
            "suggestions": list of strings (suggestions for improvement if is_valid is false)
        }}

        EXAMPLES:
        
        Valid match:
        User Prompt: "Recolor ATMs within 100 meters of banks using a green-to-red gradient based on rating."
        Output: {{
            "color_grid_choice": ["#00ff00", "#33cc00", "#669900", "#996600", "#cc3300", "#ff0000"],
            "change_lyr_name": "ATMs",
            "based_on_lyr_name": "banks",
            "coverage_property": "radius",
            "coverage_value": 100,
            "color_based_on": "rating",
            "list_names": []
        }}
        Response: {{
            "is_valid": true
        }}
        
        Invalid match (wrong coverage property):
        User Prompt: "Recolor ATMs within 10 minutes drive time from banks using a blue gradient."
        Output: {{
            "color_grid_choice": ["#0000ff", "#3333cc", "#666699", "#996666", "#cc3333", "#ff0000"],
            "change_lyr_name": "ATMs",
            "based_on_lyr_name": "banks",
            "coverage_property": "radius",
            "coverage_value": 600,
            "color_based_on": "distance",
            "list_names": []
        }}
        Response: {{
            "is_valid": false,
            "reason": "Coverage property doesn't match user intent - user specified drive time but output uses radius",
            "suggestions": ["Change coverage_property to 'drive_time'", "Adjust coverage_value to be in minutes (10) instead of meters"]
        }}
        
        Be very thorough in your evaluation, but also consider reasonable interpretations of the user's intent. If the output is a reasonable interpretation of an ambiguous prompt, consider it valid.
        """
        return SYSTEM_PROMPT
    
    def __call__(self, user_prompt: str, processed_output: ReqGradientColorBasedOnZone, available_layers) -> ValidationResult:
        # Validate the output
        try:
            response = self.chain.invoke(
            {
                "user_prompt": user_prompt,
                "format_instruction": self.format_instruction,
                "processed_output": processed_output,
                "available_layers": available_layers
            })
            return response
        except Exception as e:
            # Fallback in case parsing fails
            return ValidationResult(
                is_valid=False,
                reason=f"Failed to validate output: {str(e)}",
                suggestions=["Please check the output format manually"]
            )