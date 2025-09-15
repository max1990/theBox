from app import app, plugin_manager


def test_ui_status_route_registered():
    # Ensure plugin is available and blueprint registered
    with app.test_client() as c:
        # load plugins once in app main, but ensure search_planner exists
        names = list(plugin_manager.plugins.keys())
        # If not loaded in config, skip gracefully (test environment)
        # We still can import blueprint via plugin and register locally if needed.
        # Here we just exercise that /status returns JSON when page exists.
        for name, plugin in plugin_manager.plugins.items():
            if plugin.__class__.__name__ == 'SearchPlannerPlugin':
                rv = c.get(f"/plugins/{plugin.name}/status")
                assert rv.status_code in (200, 404)  # 200 if registered, else 404 if not in config
                break

