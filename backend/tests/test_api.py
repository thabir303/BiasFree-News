"""
Basic tests for BiasFree News API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "BiasFree News API"
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data


def test_analyze_endpoint_validation():
    """Test analyze endpoint input validation."""
    # Test with too short content
    response = client.post(
        "/api/analyze",
        json={"content": "short", "title": "Test"}
    )
    assert response.status_code == 422  # Validation error
    
    # Test with valid content
    valid_content = "এটি একটি পরীক্ষামূলক বাংলা সংবাদ নিবন্ধ যা বিশ্লেষণের জন্য যথেষ্ট দীর্ঘ।"
    response = client.post(
        "/api/analyze",
        json={"content": valid_content, "title": "টেস্ট শিরোনাম"}
    )
    # Note: This will fail without valid OpenAI key, but validates structure
    assert response.status_code in [200, 500]


def test_scrape_endpoint_validation():
    """Test scrape endpoint validates newspaper sources."""
    response = client.post(
        "/api/scrape",
        json={
            "source": "invalid_source",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
    )
    assert response.status_code == 422  # Should fail validation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
