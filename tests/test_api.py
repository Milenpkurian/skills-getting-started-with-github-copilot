"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        "Tennis Club": {
            "description": "Learn tennis skills and compete in matches",
            "schedule": "Wednesdays and Saturdays, 4:00 PM - 5:30 PM",
            "max_participants": 16,
            "participants": ["alex@mergington.edu"]
        },
        "Basketball Team": {
            "description": "Join our competitive basketball team",
            "schedule": "Mondays and Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu", "marcus@mergington.edu"]
        }
    }

    # Clear and reset
    activities.clear()
    activities.update(original_activities)

    yield

    # Clean up after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Tennis Club" in data
        assert "Basketball Team" in data
        assert isinstance(data["Tennis Club"], dict)
        assert "description" in data["Tennis Club"]
        assert "participants" in data["Tennis Club"]
        assert "max_participants" in data["Tennis Club"]

    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Tennis%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Tennis Club" in data["message"]

        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Tennis Club"]["participants"]

    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup is prevented"""
        # First signup should succeed
        response1 = client.post(
            "/activities/Tennis%20Club/signup?email=test@mergington.edu"
        )
        assert response1.status_code == 200

        # Second signup should fail
        response2 = client.post(
            "/activities/Tennis%20Club/signup?email=test@mergington.edu"
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_increases_participant_count(self, client):
        """Test that signup increases the participant count"""
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[
                            "Tennis Club"]["participants"])

        # Sign up a new student
        client.post("/activities/Tennis%20Club/signup?email=new@mergington.edu")

        # Verify count increased
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()[
                            "Tennis Club"]["participants"])
        assert updated_count == initial_count + 1


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_successful(self, client):
        """Test successful unregister from an activity"""
        # First, sign up a student
        client.post(
            "/activities/Tennis%20Club/signup?email=temp@mergington.edu")

        # Then unregister
        response = client.delete(
            "/activities/Tennis%20Club/unregister?email=temp@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        assert "temp@mergington.edu" in data["message"]

        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "temp@mergington.edu" not in activities_data["Tennis Club"]["participants"]

    def test_unregister_not_signed_up(self, client):
        """Test unregister for a student who isn't signed up"""
        response = client.delete(
            "/activities/Tennis%20Club/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Unregister alex@mergington.edu who is already in Tennis Club
        response = client.delete(
            "/activities/Tennis%20Club/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200

        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Tennis Club"]["participants"]


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signing up and then unregistering"""
        email = "workflow@mergington.edu"
        activity = "Basketball Team"

        # Get initial state
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[
            activity]["participants"]
        assert email not in initial_participants

        # Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200

        # Verify signup
        after_signup_response = client.get("/activities")
        after_signup_participants = after_signup_response.json()[
            activity]["participants"]
        assert email in after_signup_participants

        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200

        # Verify unregister
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity]["participants"]
        assert email not in final_participants
        assert len(final_participants) == len(initial_participants)
