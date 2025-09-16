import os
from pathlib import Path
import re


def test_get_settings_returns_200(client):
    r = client.get('/settings')
    assert r.status_code == 200
    assert b'Environment & Offsets' in r.data


def test_post_valid_saves_atomically_and_backup(tmp_path, monkeypatch, client):
    # Point env dir to temp
    env_dir = tmp_path / 'env'
    env_dir.mkdir()
    env_file = env_dir / '.thebox.env'
    env_file.write_text('SEACROSS_PORT=2000\n')

    from mvp import env_loader
    monkeypatch.setattr(env_loader, 'env_paths', lambda: (env_file, env_dir / '.thebox.env.example'))

    payload = {
        'SEACROSS_HOST': '255.255.255.255',
        'SEACROSS_PORT': '3000',
        'BOW_ZERO_DEG': '10',
        'CONFIDENCE_BASE': '0.5',
        'CONFIDENCE_TRUE': '0.9',
        'CONFIDENCE_FALSE': '0.1',
        'CONF_HYSTERESIS': '0.2',
        'RANGE_MIN_KM': '0.2',
        'RANGE_MAX_KM': '2.0',
        'RANGE_FIXED_KM': '1.0',
        'RANGE_EWMA_ALPHA': '0.5',
        'VISION_INPUT_RES': '640',
        'VISION_FRAME_SKIP': '0',
        'VISION_N_CONSEC_FOR_TRUE': '1',
        'VISION_LATENCY_MS': '50',
        'VISION_MAX_DWELL_MS': '1000',
    }

    r = client.post('/settings', data={**payload, 'action': 'save'})
    assert r.status_code == 200
    text = env_file.read_text()
    assert 'SEACROSS_PORT=3000' in text
    # backup exists
    backups = list(env_dir.glob('.thebox.env.bak.*'))
    assert backups, 'Expected a dated backup file'


def test_post_invalid_returns_400_and_errors(tmp_path, monkeypatch, client):
    env_dir = tmp_path / 'env'
    env_dir.mkdir()
    env_file = env_dir / '.thebox.env'
    env_file.write_text('SEACROSS_PORT=2000\n')

    from mvp import env_loader
    monkeypatch.setattr(env_loader, 'env_paths', lambda: (env_file, env_dir / '.thebox.env.example'))

    r = client.post('/settings', data={'SEACROSS_PORT': '70000', 'action': 'save'})
    assert r.status_code == 400
    assert b'Out of range' in r.data


def test_angle_normalization(tmp_path, monkeypatch, client):
    env_dir = tmp_path / 'env'
    env_dir.mkdir()
    env_file = env_dir / '.thebox.env'
    env_file.write_text('BOW_ZERO_DEG=0\n')

    from mvp import env_loader
    monkeypatch.setattr(env_loader, 'env_paths', lambda: (env_file, env_dir / '.thebox.env.example'))

    r = client.post('/settings', data={'BOW_ZERO_DEG': '-10', 'SEACROSS_HOST': '255.255.255.255', 'SEACROSS_PORT': '2000', 'action': 'save'})
    assert r.status_code == 200
    text = env_file.read_text()
    assert 'BOW_ZERO_DEG=350.0' in text or 'BOW_ZERO_DEG=350' in text


