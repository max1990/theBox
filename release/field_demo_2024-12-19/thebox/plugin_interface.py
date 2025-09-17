from abc import ABC, abstractmethod


class PluginInterface(ABC):
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.name = self.__class__.__name__

    def publish(self, event_type, data, store_in_db=True):
        self.event_manager.publish(event_type, data, self.name, store_in_db)

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def unload(self):
        pass

    def get_blueprint(self):
        """
        Optional method for plugins to provide a Flask Blueprint.
        """
        return None
