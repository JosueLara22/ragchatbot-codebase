"""
API endpoint tests for the Course Materials RAG System.

These tests verify the FastAPI endpoints handle requests/responses correctly,
including proper error handling and data validation.
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for POST /api/query endpoint"""

    def test_query_without_session_creates_new_session(self, test_client):
        """Test that querying without session_id creates a new session"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify new session was created
        assert data["session_id"] == "test-session-123"
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)

    def test_query_with_existing_session(self, test_client):
        """Test querying with an existing session_id"""
        session_id = "existing-session-456"

        response = test_client.post(
            "/api/query",
            json={
                "query": "Tell me about lesson 5",
                "session_id": session_id
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the existing session_id is preserved
        assert data["session_id"] == session_id
        assert data["answer"]
        assert len(data["sources"]) > 0

    def test_query_returns_sources_with_links(self, test_client):
        """Test that query response includes source information with links"""
        response = test_client.post(
            "/api/query",
            json={"query": "What are Python basics?"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify sources structure
        assert len(data["sources"]) > 0
        source = data["sources"][0]

        assert "text" in source
        assert "course_link" in source
        assert "lesson_link" in source

        # Verify link format
        assert source["course_link"] is None or source["course_link"].startswith("http")
        assert source["lesson_link"] is None or source["lesson_link"].startswith("http")

    def test_query_with_empty_string_fails(self, test_client):
        """Test that empty query string is handled properly"""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # The endpoint may accept empty query or return 422 validation error
        # depending on implementation - both are valid
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_query_with_missing_query_field_fails(self, test_client):
        """Test that request without query field returns validation error"""
        response = test_client.post(
            "/api/query",
            json={"session_id": "test-123"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_with_invalid_json_fails(self, test_client):
        """Test that invalid JSON payload returns error"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_response_model_validation(self, test_client):
        """Test that response matches the QueryResponse model"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate all required fields are present and correct types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Validate source structure
        for source in data["sources"]:
            assert isinstance(source["text"], str)
            assert source["course_link"] is None or isinstance(source["course_link"], str)
            assert source["lesson_link"] is None or isinstance(source["lesson_link"], str)

    def test_query_handles_special_characters(self, test_client):
        """Test querying with special characters"""
        special_query = "What is Python's @decorator & <syntax>?"

        response = test_client.post(
            "/api/query",
            json={"query": special_query}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"]

    def test_query_handles_long_input(self, test_client):
        """Test querying with very long input"""
        long_query = "What is Python? " * 100  # 1800+ characters

        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for GET /api/courses endpoint"""

    def test_get_courses_returns_stats(self, test_client):
        """Test that courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

    def test_courses_response_structure(self, test_client):
        """Test that course response has correct data types"""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify total_courses matches course_titles length
        assert data["total_courses"] == len(data["course_titles"])

    def test_courses_titles_are_strings(self, test_client):
        """Test that all course titles are strings"""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)
            assert len(title) > 0

    def test_courses_endpoint_no_parameters(self, test_client):
        """Test that courses endpoint works without parameters"""
        response = test_client.get("/api/courses?extra=param")

        assert response.status_code == status.HTTP_200_OK

    def test_courses_idempotent(self, test_client):
        """Test that multiple calls to courses endpoint return consistent results"""
        response1 = test_client.get("/api/courses")
        response2 = test_client.get("/api/courses")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Results should be identical
        assert response1.json() == response2.json()


@pytest.mark.api
class TestSessionEndpoint:
    """Test suite for DELETE /api/session/{session_id} endpoint"""

    def test_clear_session_success(self, test_client):
        """Test successful session clearing"""
        session_id = "test-session-789"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "message" in data
        assert data["status"] == "success"
        assert session_id in data["message"]

    def test_clear_session_with_special_characters(self, test_client):
        """Test clearing session with special characters in ID"""
        session_id = "session-with-dash_underscore.dot"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == status.HTTP_200_OK

    def test_clear_nonexistent_session(self, test_client):
        """Test clearing a nonexistent session"""
        # Most implementations should handle this gracefully
        response = test_client.delete("/api/session/nonexistent-session")

        # Should either succeed (idempotent) or return error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_clear_session_empty_id(self, test_client):
        """Test that empty session ID is handled correctly"""
        # Empty ID in URL path should result in 404 or 405
        response = test_client.delete("/api/session/")

        # Either Not Found or Method Not Allowed (due to route mismatch)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_clear_session_multiple_times(self, test_client):
        """Test that clearing same session multiple times is idempotent"""
        session_id = "idempotent-session"

        response1 = test_client.delete(f"/api/session/{session_id}")
        response2 = test_client.delete(f"/api/session/{session_id}")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK


@pytest.mark.api
class TestCORSAndMiddleware:
    """Test suite for CORS and middleware configuration"""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present in responses"""
        response = test_client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_post(self, test_client):
        """Test that CORS allows POST requests"""
        response = test_client.post(
            "/api/query",
            json={"query": "test"},
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.api
class TestEndpointIntegration:
    """Integration tests for multiple endpoints working together"""

    def test_query_then_clear_session_workflow(self, test_client, mock_rag_system):
        """Test complete workflow: query with session, then clear it"""
        # Step 1: Create query with new session
        query_response = test_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert query_response.status_code == status.HTTP_200_OK
        session_id = query_response.json()["session_id"]

        # Step 2: Clear the session
        clear_response = test_client.delete(f"/api/session/{session_id}")

        assert clear_response.status_code == status.HTTP_200_OK

        # Verify clear_session was called on the RAG system
        mock_rag_system.session_manager.clear_session.assert_called_with(session_id)

    def test_multiple_queries_same_session(self, test_client):
        """Test multiple queries using the same session"""
        # First query creates session
        response1 = test_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        session_id = response1.json()["session_id"]

        # Second query uses same session
        response2 = test_client.post(
            "/api/query",
            json={
                "query": "Tell me more",
                "session_id": session_id
            }
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["session_id"] == session_id

    def test_query_and_courses_endpoints_independent(self, test_client):
        """Test that query and courses endpoints work independently"""
        # Get courses
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == status.HTTP_200_OK

        # Make query
        query_response = test_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )
        assert query_response.status_code == status.HTTP_200_OK

        # Get courses again - should be unchanged
        courses_response2 = test_client.get("/api/courses")
        assert courses_response2.status_code == status.HTTP_200_OK
        assert courses_response.json() == courses_response2.json()


@pytest.mark.api
class TestErrorHandling:
    """Test suite for error handling across endpoints"""

    def test_invalid_endpoint_returns_404(self, test_client):
        """Test that invalid endpoints return 404"""
        response = test_client.get("/api/invalid-endpoint")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_wrong_http_method_returns_405(self, test_client):
        """Test that wrong HTTP methods return 405"""
        # GET on POST endpoint
        response = test_client.get("/api/query")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_post_to_courses_endpoint_fails(self, test_client):
        """Test that POST to GET-only endpoint fails"""
        response = test_client.post(
            "/api/courses",
            json={"data": "test"}
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
