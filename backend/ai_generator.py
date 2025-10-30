import google.generativeai as genai
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Google's Gemini API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for both searching course content and retrieving course outlines.

Tool Usage Guidelines:

**Multi-Round Tool Calling**:
- You can make up to 2 rounds of tool calls per user query
- After seeing results from the first round, you can make additional tool calls if needed
- Use this for complex queries requiring multiple searches, comparisons, or multi-part questions

**Course Outline Tool** (get_course_outline):
- Use for questions about course structure, available lessons, or course organization
- Returns: course title, course link, complete lesson list with numbers and titles
- Examples: "What lessons are in X course?", "Show me the outline of Y", "What courses are available?"

**Content Search Tool** (search_course_content):
- Use for questions about specific course content or detailed educational materials
- Returns: relevant content excerpts from lessons
- Examples: "What does lesson 3 teach about X?", "Explain concept Y from the course"

**Multi-Step Query Examples**:
- "Search for a course discussing the same topic as lesson 4 of course X"
  → First: get_course_outline for course X to identify lesson 4 title
  → Second: search_course_content using that title to find related courses

- "Compare the teaching approach between course A lesson 2 and course B lesson 3"
  → First: search_course_content for course A lesson 2
  → Second: search_course_content for course B lesson 3

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: Use outline tool, then present the information clearly
- **Course content questions**: Use search tool(s), then answer based on results
- **Complex queries**: Make multiple tool calls across rounds as needed
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the search results" or "I used the outline tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": 0,
                "max_output_tokens": 800,
            },
        )

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with multi-round tool usage support via chat sessions.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool-calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build prompt with system instructions and conversation history
        full_prompt = self.SYSTEM_PROMPT

        if conversation_history:
            full_prompt += f"\n\nPrevious conversation:\n{conversation_history}"

        full_prompt += f"\n\nUser: {query}\nAssistant:"

        # Handle tools if provided
        if tools and tool_manager:
            # Convert Anthropic-style tools to Gemini function declarations
            gemini_tools = self._convert_tools_to_gemini_format(tools)

            # Create model with tools
            model_with_tools = genai.GenerativeModel(
                model_name=self.model.model_name,
                generation_config={
                    "temperature": 0,
                    "max_output_tokens": 800,
                },
                tools=gemini_tools,
            )

            # Start chat session with tools
            chat = model_with_tools.start_chat(history=[])

            # Send initial prompt
            response = chat.send_message(full_prompt)

            # Sequential tool calling loop (max 2 rounds)
            for round_num in range(max_rounds):
                # Check if this response contains function calls
                function_calls = self._extract_function_calls(response)

                if not function_calls:
                    # No tool calls - this is the final answer
                    return response.text

                # Execute all function calls in this round
                function_responses = []
                for fc in function_calls:
                    try:
                        result = tool_manager.execute_tool(fc.name, **dict(fc.args))
                        function_responses.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fc.name, response={"result": result}
                                )
                            )
                        )
                    except Exception as e:
                        # Tool execution failed - return error message
                        return f"Error executing tool {fc.name}: {str(e)}"

                # Send function responses back to chat session
                # This will get the AI's next response (either another tool call or final answer)
                response = chat.send_message(function_responses)

            # Max rounds reached - return whatever response we have
            # (either final answer or we hit the limit)
            return response.text

        # Generate response without tools
        response = self.model.generate_content(full_prompt)
        return response.text

    def _convert_schema_type(self, type_str: str):
        """Convert JSON schema type string to Gemini Type enum"""
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "integer": genai.protos.Type.INTEGER,
            "number": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "object": genai.protos.Type.OBJECT,
            "array": genai.protos.Type.ARRAY,
        }
        return type_mapping.get(type_str, genai.protos.Type.STRING)

    def _convert_schema_properties(self, properties: Dict) -> Dict:
        """Recursively convert schema properties to Gemini format"""
        converted_props = {}
        for prop_name, prop_schema in properties.items():
            converted_prop = {}

            # Convert type
            if "type" in prop_schema:
                converted_prop["type"] = self._convert_schema_type(prop_schema["type"])

            # Copy description if present
            if "description" in prop_schema:
                converted_prop["description"] = prop_schema["description"]

            # Handle nested properties for objects
            if prop_schema.get("type") == "object" and "properties" in prop_schema:
                converted_prop["properties"] = self._convert_schema_properties(
                    prop_schema["properties"]
                )

            # Handle array items
            if prop_schema.get("type") == "array" and "items" in prop_schema:
                items_schema = prop_schema["items"]
                converted_items = {}
                if "type" in items_schema:
                    converted_items["type"] = self._convert_schema_type(
                        items_schema["type"]
                    )
                if "description" in items_schema:
                    converted_items["description"] = items_schema["description"]
                converted_prop["items"] = genai.protos.Schema(**converted_items)

            converted_props[prop_name] = genai.protos.Schema(**converted_prop)

        return converted_props

    def _convert_tools_to_gemini_format(self, anthropic_tools: List[Dict]) -> List:
        """
        Convert Anthropic-style tool definitions to Gemini function declarations.

        Args:
            anthropic_tools: List of tools in Anthropic format

        Returns:
            List of Gemini function declarations
        """
        gemini_functions = []

        for tool in anthropic_tools:
            if tool.get("type") == "function" or "name" in tool:
                # Get the input schema and convert it properly
                input_schema = tool.get("input_schema", {})

                # Convert properties recursively
                converted_properties = self._convert_schema_properties(
                    input_schema.get("properties", {})
                )

                # Create schema dict
                schema_dict = {
                    "type": genai.protos.Type.OBJECT,
                    "properties": converted_properties,
                }

                # Add required fields if present
                if "required" in input_schema:
                    schema_dict["required"] = input_schema["required"]

                function_decl = genai.protos.FunctionDeclaration(
                    name=tool.get("name"),
                    description=tool.get("description", ""),
                    parameters=genai.protos.Schema(**schema_dict),
                )
                gemini_functions.append(function_decl)

        return gemini_functions

    def _extract_function_calls(self, response) -> List:
        """
        Extract function calls from a Gemini response.

        Args:
            response: Gemini API response object

        Returns:
            List of function_call objects, or empty list if none found
        """
        function_calls = []

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        function_calls.append(part.function_call)

        return function_calls
