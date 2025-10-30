import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_generator import AIGenerator
import google.generativeai as genai


@pytest.fixture
def mock_tool_manager():
    """Create mock tool manager for testing"""
    manager = Mock()
    manager.execute_tool = Mock()
    return manager


@pytest.fixture
def mock_tools():
    """Create mock tool definitions"""
    return [
        {
            "name": "get_course_outline",
            "description": "Get course outline",
            "input_schema": {
                "type": "object",
                "properties": {"course_title": {"type": "string"}},
                "required": [],
            },
        },
        {
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    ]


class TestSequentialToolCalling:
    """Test suite for multi-round tool calling functionality"""

    def test_single_tool_call_terminates_immediately(
        self, mock_tool_manager, mock_tools
    ):
        """Test that a single tool call followed by text response terminates"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Mock first response: tool use
        mock_function_call = Mock()
        mock_function_call.name = "get_course_outline"
        mock_function_call.args = {"course_title": "Python"}

        mock_part_1 = Mock()
        mock_part_1.function_call = mock_function_call

        mock_response_1 = Mock()
        mock_response_1.candidates = [Mock(content=Mock(parts=[mock_part_1]))]

        # Mock second response: final answer (no function call)
        mock_part_2 = Mock(spec=["text"])
        (
            delattr(mock_part_2, "function_call")
            if hasattr(mock_part_2, "function_call")
            else None
        )
        mock_response_2 = Mock()
        mock_response_2.text = "Here is the course outline with 10 lessons..."
        mock_response_2.candidates = [Mock(content=Mock(parts=[mock_part_2]))]

        # Mock chat session
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(side_effect=[mock_response_1, mock_response_2])

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            mock_tool_manager.execute_tool.return_value = (
                "Course: Python\nLessons: 1-10"
            )

            result = ai_gen.generate_response(
                query="What lessons are in Python course?",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
            )

            # Should have made exactly 1 tool call
            assert mock_tool_manager.execute_tool.call_count == 1
            assert "course outline" in result.lower()
            assert mock_chat.send_message.call_count == 2

    def test_two_sequential_tool_calls(self, mock_tool_manager, mock_tools):
        """Test that two sequential tool calls work correctly"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Mock first response: first tool call
        mock_fc_1 = Mock()
        mock_fc_1.name = "get_course_outline"
        mock_fc_1.args = {"course_title": "Python"}

        mock_part_1 = Mock()
        mock_part_1.function_call = mock_fc_1

        mock_response_1 = Mock()
        mock_response_1.candidates = [Mock(content=Mock(parts=[mock_part_1]))]

        # Mock second response: second tool call
        mock_fc_2 = Mock()
        mock_fc_2.name = "search_course_content"
        mock_fc_2.args = {"query": "lesson 5 content"}

        mock_part_2 = Mock()
        mock_part_2.function_call = mock_fc_2

        mock_response_2 = Mock()
        mock_response_2.candidates = [Mock(content=Mock(parts=[mock_part_2]))]

        # Mock third response: final answer
        mock_part_3 = Mock(spec=["text"])
        (
            delattr(mock_part_3, "function_call")
            if hasattr(mock_part_3, "function_call")
            else None
        )

        mock_response_3 = Mock()
        mock_response_3.text = (
            "Lesson 5 covers advanced topics like recursion and dynamic programming."
        )
        mock_response_3.candidates = [Mock(content=Mock(parts=[mock_part_3]))]

        # Mock chat session
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(
            side_effect=[mock_response_1, mock_response_2, mock_response_3]
        )

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            mock_tool_manager.execute_tool.side_effect = [
                "Course: Python\nLesson 5: Advanced Topics",
                "[Python - Lesson 5]\nContent about recursion and dynamic programming...",
            ]

            result = ai_gen.generate_response(
                query="What does lesson 5 of Python course teach?",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
                max_rounds=2,
            )

            # Should have made exactly 2 tool calls
            assert mock_tool_manager.execute_tool.call_count == 2
            assert "advanced topics" in result.lower()

    def test_max_rounds_enforced(self, mock_tool_manager, mock_tools):
        """Test that max_rounds limit is enforced (stops after 2 rounds)"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Mock responses that always want to call tools
        def create_tool_call_response():
            mock_fc = Mock()
            mock_fc.name = "get_course_outline"
            mock_fc.args = {"course_title": "Python"}

            mock_part = Mock()
            mock_part.function_call = mock_fc

            mock_response = Mock()
            mock_response.candidates = [Mock(content=Mock(parts=[mock_part]))]
            mock_response.text = "Analyzing..."
            return mock_response

        # Final response after max rounds
        mock_final_part = Mock(spec=["text"])
        (
            delattr(mock_final_part, "function_call")
            if hasattr(mock_final_part, "function_call")
            else None
        )

        mock_final_response = Mock()
        mock_final_response.text = "Final answer after max rounds"
        mock_final_response.candidates = [Mock(content=Mock(parts=[mock_final_part]))]

        # Mock chat session
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(
            side_effect=[
                create_tool_call_response(),  # Round 1 tool call
                create_tool_call_response(),  # Round 2 tool call
                mock_final_response,  # After round 2 function response
            ]
        )

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            mock_tool_manager.execute_tool.return_value = "Some result"

            result = ai_gen.generate_response(
                query="Complex question",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
                max_rounds=2,
            )

            # Should stop after 2 rounds
            assert mock_tool_manager.execute_tool.call_count == 2
            assert "Final answer after max rounds" in result

    def test_no_tool_call_immediate_answer(self, mock_tool_manager, mock_tools):
        """Test that queries not requiring tools get immediate answers"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Response with no function call (general knowledge)
        mock_part = Mock(spec=["text"])
        (
            delattr(mock_part, "function_call")
            if hasattr(mock_part, "function_call")
            else None
        )

        mock_response = Mock()
        mock_response.text = "Python is a high-level programming language..."
        mock_response.candidates = [Mock(content=Mock(parts=[mock_part]))]

        # Mock chat session
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(return_value=mock_response)

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            result = ai_gen.generate_response(
                query="What is Python?",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
            )

            # Should not have executed any tools
            assert mock_tool_manager.execute_tool.call_count == 0
            assert "programming language" in result.lower()
            assert mock_chat.send_message.call_count == 1

    def test_tool_execution_error_handling(self, mock_tool_manager, mock_tools):
        """Test graceful handling of tool execution errors"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Response with function call
        mock_fc = Mock()
        mock_fc.name = "search_course_content"
        mock_fc.args = {"query": "test"}

        mock_part = Mock()
        mock_part.function_call = mock_fc

        mock_response = Mock()
        mock_response.candidates = [Mock(content=Mock(parts=[mock_part]))]

        # Mock chat session
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(return_value=mock_response)

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            # Tool execution fails
            mock_tool_manager.execute_tool.side_effect = Exception(
                "Database connection failed"
            )

            result = ai_gen.generate_response(
                query="Search for something",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
            )

            # Should return error message
            assert "Error executing tool" in result
            assert "search_course_content" in result
            assert "Database connection failed" in result

    def test_context_preservation_across_rounds(self, mock_tool_manager, mock_tools):
        """Test that context from previous rounds is preserved in chat session"""
        with patch("google.generativeai.configure"):
            ai_gen = AIGenerator(api_key="test_key", model="gemini-1.5-flash")

        # Mock first response: first tool call
        mock_fc_1 = Mock()
        mock_fc_1.name = "get_course_outline"
        mock_fc_1.args = {"course_title": "Python"}

        mock_part_1 = Mock()
        mock_part_1.function_call = mock_fc_1

        mock_response_1 = Mock()
        mock_response_1.candidates = [Mock(content=Mock(parts=[mock_part_1]))]

        # Mock second response: another tool call
        mock_fc_2 = Mock()
        mock_fc_2.name = "search_course_content"
        mock_fc_2.args = {"query": "Advanced Topics"}

        mock_part_2 = Mock()
        mock_part_2.function_call = mock_fc_2

        mock_response_2 = Mock()
        mock_response_2.candidates = [Mock(content=Mock(parts=[mock_part_2]))]

        # Mock final response
        mock_part_3 = Mock(spec=["text"])
        (
            delattr(mock_part_3, "function_call")
            if hasattr(mock_part_3, "function_call")
            else None
        )

        mock_response_3 = Mock()
        mock_response_3.text = "Based on the outline, lesson 5 covers advanced topics."
        mock_response_3.candidates = [Mock(content=Mock(parts=[mock_part_3]))]

        # Mock chat session to verify multiple calls on same object
        mock_chat = MagicMock()
        mock_chat.send_message = Mock(
            side_effect=[mock_response_1, mock_response_2, mock_response_3]
        )

        with patch("google.generativeai.GenerativeModel") as MockGenModel:
            mock_model_instance = Mock()
            mock_model_instance.model_name = "gemini-1.5-flash"
            mock_model_instance.start_chat = Mock(return_value=mock_chat)
            MockGenModel.return_value = mock_model_instance

            mock_tool_manager.execute_tool.side_effect = [
                "Course: Python\nLessons:\n1. Intro\n5. Advanced Topics",
                "Lesson 5 discusses recursion...",
            ]

            result = ai_gen.generate_response(
                query="Multi-step query",
                tools=mock_tools,
                tool_manager=mock_tool_manager,
            )

            # Verify chat.send_message was called multiple times on same chat object
            # (indicating context preservation via chat session)
            assert mock_chat.send_message.call_count == 3
            assert mock_tool_manager.execute_tool.call_count == 2
            assert "based on the outline" in result.lower()
