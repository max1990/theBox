"""
Comprehensive tests for settings page validation, save, revert, and error handling
"""

from unittest.mock import patch

import pytest


# Mock the app and dependencies
@pytest.fixture
def client():
    """Create a test client"""
    from app import app

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-key"
    return app.test_client()


@pytest.fixture
def temp_env_dir(tmp_path):
    """Create a temporary environment directory"""
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    env_file = env_dir / ".thebox.env"
    env_file.write_text("SEACROSS_PORT=2000\nBOW_ZERO_DEG=0\n")

    example_file = env_dir / ".thebox.env.example"
    example_file.write_text("SEACROSS_PORT=3000\nBOW_ZERO_DEG=10\n")

    return env_dir, env_file, example_file


def test_get_settings_returns_200(client, temp_env_dir):
    """Test that GET /settings returns 200 and loads current values"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Environment & Offsets" in response.data
        assert b"SEACROSS_PORT" in response.data


def test_validate_good_payload_returns_ok(client, temp_env_dir):
    """Test that validate returns ok:true for valid payload"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "3000",
            "BOW_ZERO_DEG": "10",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert "normalized" in data


def test_validate_bad_payload_returns_errors(client, temp_env_dir):
    """Test that validate returns field errors for invalid payload"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "SEACROSS_PORT": "70000",  # Invalid port
            "CONFIDENCE_BASE": "1.5",  # Invalid confidence
            "RANGE_MIN_KM": "5.0",  # Min > Max
            "RANGE_MAX_KM": "2.0",
            "VISION_INPUT_RES": "999",  # Invalid resolution
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is False
        assert "errors" in data
        assert len(data["errors"]) > 0


def test_save_writes_atomically_and_creates_backup(client, temp_env_dir):
    """Test that save performs atomic write and creates backup"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "3000",
            "BOW_ZERO_DEG": "10",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/save", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True

        # Check file was written
        content = env_file.read_text()
        assert "SEACROSS_PORT=3000" in content

        # Check backup was created
        backups = list(env_dir.glob(".thebox.env.bak.*"))
        assert len(backups) > 0


def test_save_normalizes_angles(client, temp_env_dir):
    """Test that save normalizes angles to [0, 360)"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "BOW_ZERO_DEG": "-10",  # Should become 350
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "2000",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/save", data=payload)
        assert response.status_code == 200

        # Check angle was normalized
        content = env_file.read_text()
        assert "BOW_ZERO_DEG=350.0" in content or "BOW_ZERO_DEG=350" in content


def test_revert_with_backup_restores(client, temp_env_dir):
    """Test that revert restores from latest backup"""
    env_dir, env_file, example_file = temp_env_dir

    # Create a backup
    backup_file = env_dir / ".thebox.env.bak.20240101120000"
    backup_file.write_text("SEACROSS_PORT=5000\nBOW_ZERO_DEG=20\n")

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        response = client.post("/settings/revert")
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True

        # Check file was restored
        content = env_file.read_text()
        assert "SEACROSS_PORT=5000" in content


def test_revert_without_backup_returns_error(client, temp_env_dir):
    """Test that revert returns error when no backup exists"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        response = client.post("/settings/revert")
        assert response.status_code == 404
        data = response.get_json()
        assert data["ok"] is False
        assert "No backup found" in data["error"]


def test_confidence_validation_enforces_hierarchy(client, temp_env_dir):
    """Test that confidence validation enforces TRUE >= BASE >= FALSE"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        # Invalid hierarchy: TRUE < BASE
        payload = {
            "CONFIDENCE_BASE": "0.8",
            "CONFIDENCE_TRUE": "0.6",  # Less than BASE
            "CONFIDENCE_FALSE": "0.2",
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "2000",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is False
        assert (
            "CONFIDENCE_TRUE" in data["errors"] or "CONFIDENCE_BASE" in data["errors"]
        )


def test_range_validation_enforces_min_max(client, temp_env_dir):
    """Test that range validation enforces MIN < MAX"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        # Invalid range: MIN >= MAX
        payload = {
            "RANGE_MIN_KM": "5.0",
            "RANGE_MAX_KM": "2.0",  # Less than MIN
            "RANGE_FIXED_KM": "3.0",
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "2000",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is False
        assert "RANGE_MIN_KM" in data["errors"] or "RANGE_MAX_KM" in data["errors"]


def test_weights_validation_requires_positive_sum(client, temp_env_dir):
    """Test that weights validation requires at least one positive weight"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        # All weights zero
        payload = {
            "WEIGHT_RF": "0",
            "WEIGHT_VISION": "0",
            "WEIGHT_IR": "0",
            "WEIGHT_ACOUSTIC": "0",
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "2000",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_INPUT_RES": "640",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is False
        assert "WEIGHT" in str(data["errors"])


def test_vision_resolution_validation(client, temp_env_dir):
    """Test that vision resolution validation only allows valid values"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        # Invalid resolution
        payload = {
            "VISION_INPUT_RES": "999",  # Not in allowed values
            "SEACROSS_HOST": "255.255.255.255",
            "SEACROSS_PORT": "2000",
            "CONFIDENCE_BASE": "0.5",
            "CONFIDENCE_TRUE": "0.9",
            "CONFIDENCE_FALSE": "0.1",
            "RANGE_MIN_KM": "0.2",
            "RANGE_MAX_KM": "2.0",
            "RANGE_FIXED_KM": "1.0",
            "VISION_FRAME_SKIP": "0",
            "VISION_N_CONSEC_FOR_TRUE": "1",
            "VISION_LATENCY_MS": "50",
            "VISION_MAX_DWELL_MS": "1000",
        }

        response = client.post("/settings/validate", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is False
        assert "VISION_INPUT_RES" in data["errors"]
