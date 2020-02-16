import logging
from yaml import load, SafeLoader


class Field:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Config:
    def __init__(self, config_file_name=None, logger=None):
        self.logger = logger
        self.config_file_name = config_file_name
        self.fields = []

    def log(self, msg, level=logging.INFO):
        if self.logger:
            self.logger.log(level, msg)

    def add(self, key, value):
        self.fields[key] = (Field(key, value))

    def get(self, name):
        for field in self.fields:
            if field.name == name:
                return field.value
        return None

    def update(self, name, value):
        for field in self.fields:
            if field.name == name:
                field.value = value
                return True
        return False

    def load_config_file(self):
        if not self.config_file_name:
            self.log('[CONFIG]There was not config file name when initialising the object', logging.ERROR)
            return False

        self.log('[CONFIG]Attempting to open "{}"'.format(self.config_file_name))
        try:
            with open(self.config_file_name, 'r') as file:
                data = load(file, Loader=SafeLoader)
        except FileNotFoundError:
            self.log('[CONFIG]No "{}" file was not found'.format(self.config_file_name), logging.WARNING)
            return False

        for key, value in data.items():
            self.fields.append(Field(key, value))
            self.log('[CONFIG]Loaded config item "{}: {}" from "{}"'.format(key, value, self.config_file_name))

        self.log('[CONFIG]Finished loading config file "{}"'.format(self.config_file_name))
        return True


