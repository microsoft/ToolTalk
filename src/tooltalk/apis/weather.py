"""
Copyright (c) Microsoft Corporation.
Licensed under the MIT license.
"""
from abc import ABC
from datetime import datetime, timedelta

from .exceptions import APIException
from .api import API, APISuite


WEATHER_DB_NAME = "Weather"
"""
Weather
location: str - key
weather: dict of weather data ordered by date (oldest to newest)
    date: str - key
    high: float
    low: float
    conditions: str (sunny, rainy, cloudy, etc.)

HistoricWeather
location: str - key
months: list of historic weather by month
    min_temp: float
    max_temp: float
    record_min_temp: float
    record_max_temp: float
    avg_rainfall: float
    snow_days: int
"""


class WeatherAPI(API, ABC):
    database_name = WEATHER_DB_NAME

    def __init__(
            self,
            account_database: dict,
            now_timestamp: str,
            api_database: dict = None
    ) -> None:
        super().__init__(account_database, now_timestamp, api_database)
        # retrieval APIs so modifying dates is fine
        new_database = dict()
        for location, weather in self.database.items():
            weather = {
                datetime.strptime(date, "%Y-%m-%d").date(): value
                for date, value in weather.items()
            }
            # sort from oldest to newest
            new_database[location] = weather
        self.database = new_database


class CurrentWeather(WeatherAPI):
    description = "Get the current weather of a location."
    parameters = {
        "location": {
            'type': 'string',
            'description': 'The location to get the weather of.',
            "required": True
        }
    }
    output = {
        "weather": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "The date of the weather."},
                "high": {"type": "number", "description": "The high temperature of the day."},
                "low": {"type": "number", "description": "The low temperature of the day."},
                "conditions": {"type": "string", "description": "The conditions of the day."},
            },
            'description': 'The weather of the location.'
        }
    }
    is_action = False
    database_name = WEATHER_DB_NAME

    def call(self, location: str) -> dict:
        """
        Get the current weather of a location.

        Args:
            location: The location to get the weather of.
        """
        # find occurrence of date in database
        location = location.lower().strip()
        if location not in self.database:
            raise APIException(f"Location {location} not found in database")
        location_weather = self.database[location]
        now_date = self.now_timestamp.date()
        location_weather = location_weather[now_date]
        return {"weather": location_weather}


class ForecastWeather(WeatherAPI):
    description = "Get the 3-day forecast weather of a location."
    parameters = {
        "location": {
            'type': 'string',
            'description': 'The location to get the weather of.',
            "required": True
        }
    }
    output = {
        "forecast": {
            'type': 'array',
            "item": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "The date of the weather."},
                    "high": {"type": "number", "description": "The high temperature of the day."},
                    "low": {"type": "number", "description": "The low temperature of the day."},
                    "conditions": {"type": "string", "description": "The conditions of the day."},
                },
            },
            'description': 'list containing weather information for next 5 days.'
        }
    }
    is_action = False
    database_name = WEATHER_DB_NAME

    def call(self, location: str) -> dict:
        """
        Get the 3-day forecast weather of a location.

        Args:
            location: The location to get the weather of.
        """
        # find occurrence of date in database
        location = location.lower().strip()
        if location not in self.database:
            raise APIException(f"Location {location} not found in database")
        location_weather = self.database[location]
        now_date = self.now_timestamp.date()
        forecast = list()
        for i in range(3):
            forecast.append(location_weather[now_date + timedelta(days=i+1)])
        return {"forecast": forecast}


class HistoricWeather(API):
    description = "Get historic weather information of a location by month."
    parameters = {
        "location": {
            'type': 'string',
            'description': 'The location to get the weather of.',
            "required": True
        },
        "month": {
            'type': 'string',
            'description': 'The month to get weather of as a full name.',
            "required": True,
        }
    }
    output = {
        "weather": {
            "type": "object",
            "properties": {
                "min_temp": {"type": "number", "description": "The minimum temperature of the month in fahrenheit."},
                "max_temp": {"type": "number", "description": "The maximum temperature of the month in fahrenheit."},
                "record_min_temp": {"type": "number", "description": "The record minimum temperature of the month in fahrenheit."},
                "record_max_temp": {"type": "number", "description": "The record maximum temperature of the month in fahrenheit."},
                "avg_rainfall": {"type": "number", "description": "The average rainfall of the month in inches."},
                "snow_days": {"type": "number", "description": "The number of snow days of the month."},
            },
            'description': 'Historic weather of location for month.'
        }
    }
    is_action = False
    database_name = "HistoricWeather"

    def call(self, location: str, month: str) -> dict:
        """
        Get historic weather information of a location by month.

        Args:
            location: The location to get the weather of.
            month: The month to get weather of as a full name.
        """
        location = location.lower().strip()
        if location not in self.database:
            raise APIException(f"Location {location} not found in database")

        month = month.lower()
        if month not in self.database[location]:
            raise APIException(f"Historic weather data for {location} missing for month {month}")
        return {"weather": self.database[location][month]}


class WeatherSuite(APISuite):
    name = "Weather"
    description = "Get weather information of a location."
    apis = [
        CurrentWeather,
        ForecastWeather,
        HistoricWeather,
    ]
