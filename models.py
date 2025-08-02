# models.py
import json

class Movie:
    def __init__(self, title, unique_id=None, downloaded=False):
        self.title = title
        self.id = unique_id
        self.downloaded = downloaded

    def to_dict(self):
        return self.__dict__

class Show:
    def __init__(self, title, unique_id=None, downloaded_all=False):
        self.title = title
        self.id = unique_id
        self.downloaded_all = downloaded_all

    def to_dict(self):
        return self.__dict__

class SearchResult:
    def __init__(self, title, link, size, seeders):
        self.title = title
        self.link = link
        self.size = size
        self.seeders = seeders

    def to_dict(self):
        return self.__dict__

def json_encoder(obj):
    """
    JSON encoder to handle custom objects.
    """
    if isinstance(obj, (Movie, Show, SearchResult)):
        return obj.to_dict()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def json_decoder(dct):
    """
    JSON decoder to restore custom objects from a dictionary.
    """
    if 'title' in dct and 'downloaded' in dct:
        return Movie(**dct)
    if 'title' in dct and 'downloaded_all' in dct:
        return Show(**dct)
    if 'title' in dct and 'seeders' in dct:
        return SearchResult(**dct)
    return dct

