import os
import tempfile
from scripts.run_mvp import main as run_main


def test_e2e_mvp(monkeypatch):
    # Use a small synthetic file
    fd, path = tempfile.mkstemp(text=True)
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for i in range(3):
            f.write(str({
                "Data": {
                    "EpochTimeMilliSeconds": 1700000000000 + i*100,
                    "AngleOfArrivalRadians": 1.0 + 0.1*i,
                    "CorrelationKey": "ABC123"
                }
            }) + "\n")

    monkeypatch.setenv("DRONESHIELD_INPUT_FILE", path)
    monkeypatch.setenv("DRONESHIELD_UDP_PORT", "56999")
    monkeypatch.setenv("REPLAY_INTERVAL_MS", "5")
    monkeypatch.setenv("DB_PATH", os.path.join(tempfile.gettempdir(), "thebox_mvp_test.sqlite"))
    monkeypatch.setenv("SEARCH_VERDICT", "true")
    monkeypatch.setenv("VISION_VERDICT", "true")
    monkeypatch.setenv("VISION_LABEL", "Quadcopter")
    monkeypatch.setenv("CONFIDENCE_BASE", "0.75")
    monkeypatch.setenv("CONFIDENCE_TRUE", "1.0")
    monkeypatch.setenv("RANGE_MODE", "fixed")
    monkeypatch.setenv("RANGE_FIXED_KM", "2.0")

    try:
        run_main()
    except SystemExit as e:
        assert e.code == 0


