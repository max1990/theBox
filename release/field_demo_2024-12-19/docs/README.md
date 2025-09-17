# The Box - Drone Detection Service

This is a drone detection service with a flexible plugin architecture.

## Getting Started

1.  **Install Dependencies**: Run `./start.sh` (on macOS/Linux) or `start.bat` (on Windows) to create a virtual environment and install the required packages.
2.  **Run the Application**: Use the same start scripts to launch the web server.
3.  **Access the UI**: Open your web browser and navigate to `http://localhost`.

## How to Write a Plugin

Creating a plugin for The Box is straightforward. All plugins are Python files located in the `plugins` directory and must contain a class that inherits from `PluginInterface`.

### 1. Project Structure

All plugins must be placed in their own subdirectory within the `plugins/` directory. The `PluginManager` will automatically discover and load any subdirectories that do not start with `__`.

Each plugin's folder must contain a `plugin.py` file, which will serve as the entry point for the plugin.

A typical plugin's file structure might look like this:

```
plugins/
└── my_awesome_plugin/
    ├── __init__.py
    ├── plugin.py
    ├── templates/
    │   └── my_plugin_page.html
    └── static/
        └── css/
            └── style.css
```

### 2. The PluginInterface

Every plugin must define a class that inherits from `thebox.plugin_interface.PluginInterface`. This class serves as the entry point for your plugin and must implement the following methods:

*   **`load(self)`**: This method is called when your plugin is loaded. Use it to set up any resources, start background threads, or subscribe to events.
*   **`unload(self)`**: This method is called when the application is shutting down or the plugin is being reloaded. Use it to clean up any resources.

### 3. The Event System

The core of The Box is its event system, which allows plugins to communicate with each other and with the main application.

#### Subscribing to Events

Your plugin can subscribe to events using the `self.event_manager.subscribe` method:

```python
self.event_manager.subscribe(event_type, field, callback, priority)
```

*   `event_type` (str): The type of event to subscribe to (e.g., `"detection"`).
*   `field` (str): A specific field within the database to watch for changes.
*   `callback` (function): The function to call when the event occurs. It will receive `event_type`, `path`, and `value` as arguments.
*   `priority` (int): A number indicating the order in which subscribers are notified. Higher numbers are called first.

#### Publishing Events

Your plugin can publish events using the `self.publish` helper method:

```python
self.publish(event_type, data, store_in_db=True)
```

*   `event_type` (str): The type of event you are publishing.
*   `data` (dict): A dictionary representing the changes to be made to the database. The keys are dot-notation paths to the fields, and the values are the new data.
*   `store_in_db` (bool): If `True`, the data will be saved to the database. If `False`, the event will be published to subscribers, but the database will not be changed.

### 4. Creating a Web Interface

Plugins can optionally provide a web interface, which will be seamlessly integrated into the main UI as a new tab. To do this, you must implement the `get_blueprint` method in your plugin's class.

This method should return a Flask `Blueprint` instance. Here is a simple example:

```python
from flask import Blueprint, render_template

def get_blueprint(self):
    bp = Blueprint(self.name, __name__, template_folder='templates')

    @bp.route('/')
    def index():
        return render_template('my_plugin_page.html')

    return bp
```

Your HTML templates should be placed in a `templates` directory within your plugin's directory. Any static assets, such as CSS or JavaScript files, should be placed in a `static` directory.

### 5. Example Plugin

For a complete, working example, please refer to the `plugins/example_listener` and `plugins/example_input` directories. They demonstrate the new modular structure.

### Example Plugin Workflow: From Detection to External System

To illustrate how plugins can collaborate, let's consider a practical example involving three distinct plugins: a drone detector, a direction finder, and an external system interface called "SeaCross".

#### 1. The Drone Detector Plugin (Drone Shield)

This plugin's job is to scan a wide range of frequencies to detect the presence of drones. It doesn't have direction-finding capabilities.

*   **Action**: When it finds a drone, it needs to notify other plugins that might be able to gather more information. It does this by publishing a `new_drone_spotted` event.
*   **Data Storage**: This is a transient message, not a permanent piece of data, so it publishes the event with `store_in_db=False`.
*   **Example Code**:
    ```python
    # Inside the Drone Detector plugin's code
    drone_id = "drone_xyz_789"
    frequency = 433.5
    self.publish(
        "new_drone_spotted",
        {"id": drone_id, "frequency": frequency},
        store_in_db=False
    )
    ```

#### 2. The Direction Finder Plugin (Silvus)

This plugin is specialized. It listens for newly spotted drones and uses its hardware to determine their direction.

*   **Action**: It subscribes to the `new_drone_spotted` event. When it receives a notification, it tunes its equipment to the specified frequency to find the drone's direction. Once found, it publishes a `detection` event to add this new, valuable information to the database.
*   **Data Storage**: This information is important and should be persisted, so it publishes the event with `store_in_db=True`.
*   **Example Code**:
    ```python
    # Inside the Direction Finder plugin
    def load(self):
        self.event_manager.subscribe("new_drone_spotted", "", self.on_new_drone_spotted, 10)

    def on_new_drone_spotted(self, event_type, path, value):
        drone_id = value["id"]
        frequency = value["frequency"]
        
        # Perform hardware-specific direction finding...
        direction = self.find_direction_for_frequency(frequency)

        # Publish the new data to be stored in the database
        self.publish(
            "detection",
            {f"drones.{drone_id}.direction": direction, f"drones.{drone_id}.frequency": frequency},
            store_in_db=True
        )
    ```

#### 3. The SeaCross Plugin

This plugin acts as a bridge to an external system called SeaCross. It waits for comprehensive drone data and then forwards it.

*   **Action**: It subscribes to `detection` events, specifically waiting for a `direction` to be added to a drone's data. When this happens, it calculates a guessed position and sends this information to the SeaCross system. It might also publish another event, like `seacross_announcement`, for internal logging, without storing it in the database.
*   **Data Storage**: The primary action is external, so any internal event it publishes would use `store_in_db=False`.
*   **Example Code**:
    ```python
    # Inside the SeaCross plugin
    def load(self):
        self.event_manager.subscribe("detection", "drones", self.on_drone_update, 10)

    def on_drone_update(self, event_type, path, value):
        # We are only interested when a direction is added
        if path.endswith(".direction"):
            parts = path.split('.')
            drone_id = parts[1]
            direction = value
            
            # Retrieve other drone data if needed
            frequency = self.event_manager.db.get(f"drones.{drone_id}.frequency")

            # Calculate the guessed position...
            position = self.calculate_position(direction, frequency)

            # Send the data to the external SeaCross system
            self.send_to_seacross(drone_id, position)

            # Optionally publish an internal message for logging
            self.publish(
                "seacross_announcement",
                {"drone_id": drone_id, "position": position},
                store_in_db=False
            )
    ```

This workflow demonstrates how decoupled plugins can create a powerful and extensible system where each component has a single responsibility.
