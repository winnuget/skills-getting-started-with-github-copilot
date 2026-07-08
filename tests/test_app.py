"""FastAPI tests using Arrange-Act-Assert (AAA) pattern."""
import pytest
from fastapi.testclient import TestClient


class TestGetRoot:
    """Test GET / endpoint."""

    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to static/index.html."""
        # Arrange: Nothing to arrange, endpoint is simple

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code in [307, 308]  # Temporary or permanent redirect
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test GET /activities endpoint."""

    def test_get_all_activities_returns_200(self, client, mock_activities):
        """Test that GET /activities returns 200 with all activities."""
        # Arrange: Fresh activities data via fixture

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9  # Should have 9 activities

    def test_get_activities_returns_correct_structure(self, client, mock_activities):
        """Test that each activity has required fields."""
        # Arrange: Expected fields for each activity
        required_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity_name, activity in data.items():
            assert isinstance(activity_name, str)
            assert activity.keys() == required_fields
            assert isinstance(activity["description"], str)
            assert isinstance(activity["schedule"], str)
            assert isinstance(activity["max_participants"], int)
            assert isinstance(activity["participants"], list)

    def test_get_activities_participants_are_strings(self, client, mock_activities):
        """Test that participants list contains only email strings."""
        # Arrange: Nothing special to arrange

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity in data.values():
            for participant in activity["participants"]:
                assert isinstance(participant, str)

    def test_get_activities_includes_all_activity_names(self, client, mock_activities):
        """Test that response includes all expected activity names."""
        # Arrange
        expected_activities = {
            "Chess Club", "Programming Class", "Gym Class", "Basketball", "Volleyball",
            "Debate Club", "Math Olympiad", "Drama Club", "Visual Arts"
        }

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert set(data.keys()) == expected_activities

    def test_get_activities_max_participants_positive(self, client, mock_activities):
        """Test that all activities have positive max_participants."""
        # Arrange: Nothing special to arrange

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity in data.values():
            assert activity["max_participants"] > 0


class TestSignupForActivity:
    """Test POST /activities/{activity_name}/signup endpoint."""

    # ===== Happy Path Tests =====
    def test_signup_new_participant_success(self, client, mock_activities):
        """Test successful signup of a new participant."""
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        initial_count = len(mock_activities[activity_name]["participants"])

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        assert email in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count + 1

    def test_signup_returns_correct_message_format(self, client, mock_activities):
        """Test that signup returns properly formatted message."""
        # Arrange
        activity_name = "Basketball"
        email = "player@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]

    def test_signup_to_activity_with_one_spot_left(self, client, mock_activities):
        """Test signup succeeds when exactly one spot remains."""
        # Arrange: Find activity with 1 spot left or create scenario
        activity_name = "Volleyball"  # max 14, currently 1 participant, so 13 spots
        # Fill to capacity - 1
        while len(mock_activities[activity_name]["participants"]) < 13:
            mock_activities[activity_name]["participants"].append(
                f"filler{len(mock_activities[activity_name]['participants'])}@mergington.edu"
            )
        email = "lastspot@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email in mock_activities[activity_name]["participants"]

    def test_signup_multiple_participants_to_same_activity(self, client, mock_activities):
        """Test that multiple different participants can signup to same activity."""
        # Arrange
        activity_name = "Programming Class"
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]

        # Act & Assert
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
            assert email in mock_activities[activity_name]["participants"]

    # ===== Error Cases: Activity Validation =====
    def test_signup_activity_not_found_returns_404(self, client, mock_activities):
        """Test signup to non-existent activity returns 404."""
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_wrong_activity_name_case_returns_404(self, client, mock_activities):
        """Test that activity names are case-sensitive."""
        # Arrange
        activity_name = "chess club"  # Lowercase, should fail
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404

    # ===== Error Cases: Participant Validation =====
    def test_signup_duplicate_email_returns_400(self, client, mock_activities):
        """Test signup with duplicate email returns 400."""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already in Chess Club

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "Already signed up" in response.json()["detail"]

    def test_signup_activity_full_returns_400(self, client, mock_activities):
        """Test signup to full activity returns 400."""
        # Arrange
        activity_name = "Debate Club"  # max 16
        # Fill to capacity
        while len(mock_activities[activity_name]["participants"]) < 16:
            mock_activities[activity_name]["participants"].append(
                f"filler{len(mock_activities[activity_name]['participants'])}@mergington.edu"
            )
        email = "overflow@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "Activity is full" in response.json()["detail"]

    def test_signup_missing_email_returns_422(self, client, mock_activities):
        """Test signup without email parameter returns 422 validation error."""
        # Arrange
        activity_name = "Chess Club"

        # Act
        response = client.post(f"/activities/{activity_name}/signup")

        # Assert
        assert response.status_code == 422  # Unprocessable Entity

    def test_signup_after_partial_fill(self, client, mock_activities):
        """Test signup works after activity is partially filled."""
        # Arrange
        activity_name = "Math Olympiad"  # max 20
        emails_to_add = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        # Fill partially
        for email in emails_to_add:
            mock_activities[activity_name]["participants"].append(email)

        new_email = "newcomer@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )

        # Assert
        assert response.status_code == 200
        assert new_email in mock_activities[activity_name]["participants"]


class TestUnregisterFromActivity:
    """Test DELETE /activities/{activity_name}/unregister endpoint."""

    # ===== Happy Path Tests =====
    def test_unregister_participant_success(self, client, mock_activities):
        """Test successful unregistration of a participant."""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already in Chess Club
        initial_count = len(mock_activities[activity_name]["participants"])

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
        assert email not in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count - 1

    def test_unregister_returns_correct_message_format(self, client, mock_activities):
        """Test that unregister returns properly formatted message."""
        # Arrange
        activity_name = "Programming Class"
        email = "emma@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]

    def test_unregister_last_participant(self, client, mock_activities):
        """Test unregistering the last participant from an activity."""
        # Arrange
        activity_name = "Basketball"  # Only 1 participant initially
        email = "alex@mergington.edu"
        assert len(mock_activities[activity_name]["participants"]) == 1

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert len(mock_activities[activity_name]["participants"]) == 0

    def test_unregister_from_activity_with_multiple_participants(self, client, mock_activities):
        """Test unregistering one participant from activity with many."""
        # Arrange
        activity_name = "Drama Club"  # Has multiple participants
        email = "isabella@mergington.edu"
        initial_count = len(mock_activities[activity_name]["participants"])

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email not in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count - 1

    # ===== Error Cases: Activity Validation =====
    def test_unregister_activity_not_found_returns_404(self, client, mock_activities):
        """Test unregister from non-existent activity returns 404."""
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_wrong_activity_name_case_returns_404(self, client, mock_activities):
        """Test that activity names are case-sensitive on unregister."""
        # Arrange
        activity_name = "chess club"  # Lowercase, should fail
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404

    # ===== Error Cases: Participant Validation =====
    def test_unregister_participant_not_found_returns_400(self, client, mock_activities):
        """Test unregister non-existent participant returns 400."""
        # Arrange
        activity_name = "Chess Club"
        email = "notamember@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "Participant not found" in response.json()["detail"]

    def test_unregister_missing_email_returns_422(self, client, mock_activities):
        """Test unregister without email parameter returns 422 validation error."""
        # Arrange
        activity_name = "Chess Club"

        # Act
        response = client.delete(f"/activities/{activity_name}/unregister")

        # Assert
        assert response.status_code == 422  # Unprocessable Entity

    def test_unregister_twice_second_fails(self, client, mock_activities):
        """Test that unregistering the same participant twice fails on second attempt."""
        # Arrange
        activity_name = "Drama Club"
        email = "isabella@mergington.edu"

        # Act: First unregister (should succeed)
        response1 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Act: Second unregister (should fail)
        response2 = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400
        assert "Participant not found" in response2.json()["detail"]


class TestIntegrationSignupAndUnregister:
    """Integration tests for signup and unregister together."""

    def test_signup_then_unregister_workflow(self, client, mock_activities):
        """Test complete workflow: signup and then unregister."""
        # Arrange
        activity_name = "Chess Club"
        email = "workflow@mergington.edu"

        # Act: Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert signup
        assert signup_response.status_code == 200
        assert email in mock_activities[activity_name]["participants"]

        # Act: Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert unregister
        assert unregister_response.status_code == 200
        assert email not in mock_activities[activity_name]["participants"]

    def test_multiple_signups_and_unregisters(self, client, mock_activities):
        """Test multiple users signing up and unregistering."""
        # Arrange
        activity_name = "Programming Class"
        users = [
            ("user1@mergington.edu", True),   # (email, should_register)
            ("user2@mergington.edu", True),
            ("user3@mergington.edu", False),  # Sign up but don't unregister
        ]

        # Act & Assert: Sign up all users
        for email, _ in users:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
            assert email in mock_activities[activity_name]["participants"]

        # Act & Assert: Unregister some users
        for email, should_unregister in users:
            if should_unregister:
                response = client.delete(
                    f"/activities/{activity_name}/unregister",
                    params={"email": email}
                )
                assert response.status_code == 200
                assert email not in mock_activities[activity_name]["participants"]

        # Final assert: Check remaining participants
        activity = mock_activities[activity_name]
        assert "user3@mergington.edu" in activity["participants"]
        assert "user1@mergington.edu" not in activity["participants"]
        assert "user2@mergington.edu" not in activity["participants"]
