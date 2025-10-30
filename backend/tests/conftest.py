"""
Shared pytest fixtures for the RAG system tests.
This module provides common test fixtures and utilities used across all test files.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from typing import List, Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_config():
    """Create a mock configuration object for testing"""
    config = Mock()
    config.GOOGLE_API_KEY = "test_api_key"
    config.GEMINI_MODEL = "gemini-1.5-flash"
    config.MAX_ROUNDS = 2
    config.CHROMA_PATH = "./test_chroma_db"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    return config


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    rag = Mock()

    # Mock session manager
    session_manager = Mock()
    session_manager.create_session = Mock(return_value="test-session-123")
    session_manager.clear_session = Mock()
    rag.session_manager = session_manager

    # Mock query method to return a response with sources
    def mock_query(query: str, session_id: str):
        return (
            "This is a test answer from the RAG system.",
            [
                {
                    "text": "Source: Python Course - Lesson 1",
                    "course_link": "https://example.com/python",
                    "lesson_link": "https://example.com/python/lesson1"
                }
            ]
        )

    rag.query = Mock(side_effect=mock_query)

    # Mock course analytics
    rag.get_course_analytics = Mock(return_value={
        "total_courses": 3,
        "course_titles": ["Python Programming", "JavaScript Basics", "Data Science 101"]
    })

    # Mock add_course_folder for startup
    rag.add_course_folder = Mock(return_value=(3, 150))

    return rag


@pytest.fixture
def test_app(mock_rag_system, mock_config):
    """
    Create a test FastAPI app without static file mounting.
    This avoids issues where ../frontend directory doesn't exist in test environment.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app with same configuration as main app
    app = FastAPI(title="Course Materials RAG System", root_path="")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models (same as main app)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceInfo(BaseModel):
        text: str
        course_link: Optional[str] = None
        lesson_link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceInfo]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API Endpoints (same as main app, but using mock_rag_system)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)


@pytest.fixture
def mock_tool_manager():
    """Create mock tool manager for AI generator testing"""
    manager = Mock()
    manager.execute_tool = Mock()
    return manager


@pytest.fixture
def mock_tools():
    """Create mock tool definitions for AI generator testing"""
    return [
        {
            "name": "get_course_outline",
            "description": "Get course outline",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {"type": "string"}
                },
                "required": []
            }
        },
        {
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    ]


@pytest.fixture
def sample_query_requests():
    """Sample query requests for testing"""
    return {
        "simple": {
            "query": "What is Python?",
            "session_id": None
        },
        "with_session": {
            "query": "Tell me about lesson 5",
            "session_id": "existing-session-456"
        },
        "complex": {
            "query": "What are the advanced topics in the Python course?",
            "session_id": None
        }
    }


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "courses": [
            {"title": "Python Programming", "lessons": 10},
            {"title": "JavaScript Basics", "lessons": 8},
            {"title": "Data Science 101", "lessons": 12}
        ],
        "total_chunks": 150
    }
