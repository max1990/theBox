"""
Tests for Trakka mode switching functionality
"""

from unittest.mock import patch

import pytest


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
    env_file.write_text("TRAKKA_DETECTION_MODE=builtin\nSEACROSS_PORT=2000\n")

    example_file = env_dir / ".thebox.env.example"
    example_file.write_text("TRAKKA_DETECTION_MODE=builtin\nSEACROSS_PORT=3000\n")

    return env_dir, env_file, example_file


def test_trakka_mode_builtin_saves_correctly(client, temp_env_dir):
    """Test that TRAKKA_DETECTION_MODE=builtin saves correctly"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "TRAKKA_DETECTION_MODE": "builtin",
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
        data = response.get_json()
        assert data["ok"] is True

        # Check mode was saved
        content = env_file.read_text()
        assert "TRAKKA_DETECTION_MODE=builtin" in content


def test_trakka_mode_none_saves_correctly(client, temp_env_dir):
    """Test that TRAKKA_DETECTION_MODE=none saves correctly"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "TRAKKA_DETECTION_MODE": "none",
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
        data = response.get_json()
        assert data["ok"] is True

        # Check mode was saved
        content = env_file.read_text()
        assert "TRAKKA_DETECTION_MODE=none" in content


def test_trakka_mode_ours_saves_correctly(client, temp_env_dir):
    """Test that TRAKKA_DETECTION_MODE=ours saves correctly"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "TRAKKA_DETECTION_MODE": "ours",
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
        data = response.get_json()
        assert data["ok"] is True

        # Check mode was saved
        content = env_file.read_text()
        assert "TRAKKA_DETECTION_MODE=ours" in content


def test_trakka_mode_validation_rejects_invalid(client, temp_env_dir):
    """Test that invalid Trakka modes are rejected"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        payload = {
            "TRAKKA_DETECTION_MODE": "invalid_mode",  # Invalid mode
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
        assert "TRAKKA_DETECTION_MODE" in data["errors"]


def test_trakka_mode_switching_does_not_error(client, temp_env_dir):
    """Test that switching between modes doesn't cause errors"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        modes = ["builtin", "none", "ours"]

        for mode in modes:
            payload = {
                "TRAKKA_DETECTION_MODE": mode,
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
            data = response.get_json()
            assert data["ok"] is True

            # Verify mode was saved
            content = env_file.read_text()
            assert f"TRAKKA_DETECTION_MODE={mode}" in content


def test_trakka_mode_loads_from_current_settings(client, temp_env_dir):
    """Test that current Trakka mode is loaded and displayed"""
    env_dir, env_file, example_file = temp_env_dir

    # Set a specific mode in the env file
    env_file.write_text("TRAKKA_DETECTION_MODE=ours\nSEACROSS_PORT=2000\n")

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        response = client.get("/settings")
        assert response.status_code == 200

        # Check that the current mode is displayed
        assert b'value="ours"' in response.data or b"selected>ours" in response.data


def test_trakka_builtin_options_loaded(client, temp_env_dir):
    """Test that Trakka built-in options are loaded and displayed"""
    env_dir, env_file, example_file = temp_env_dir

    with patch("mvp.env_loader.env_paths") as mock_paths:
        mock_paths.return_value = (env_file, example_file)

        # Mock the trakka options
        with patch("mvp.trakka_docs.get_trakka_builtin_options") as mock_options:
            mock_options.return_value = {
                "source": "static_defaults",
                "options": {
                    "TRAKKA_THRESHOLD": ["0.1", "0.2", "0.3", "0.4", "0.5"],
                    "TRAKKA_SENSITIVITY": ["low", "medium", "high"],
                },
                "note": "Default options",
            }

            response = client.get("/settings")
            assert response.status_code == 200

            # Check that Trakka options are displayed
            assert b"Trakka Built-in Options" in response.data
            assert b"TRAKKA_THRESHOLD" in response.data
            assert b"TRAKKA_SENSITIVITY" in response.data
