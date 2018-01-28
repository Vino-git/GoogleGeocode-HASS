"""
Support for Google Geocode sensors.

For more details about this platform, please refer to the documentation at
https://github.com/michaelmcarthur/GoogleGeocode-HASS
"""
from datetime import datetime
from datetime import timedelta 
import json
import requests
from requests import get

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_SCAN_INTERVAL, ATTR_ATTRIBUTION, ATTR_LATITUDE, ATTR_LONGITUDE)
import homeassistant.helpers.location as location
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
# from homeassistant.components import weblink

CONF_ORIGIN = 'origin'
CONF_OPTIONS = 'options'
CONF_ATTRIBUTION = "Data provided by OpenStreetMap"

ATTR_STREET = 'Street'
ATTR_CITY = 'City'
ATTR_TOWN = 'Town'
ATTR_REGION = 'State'
ATTR_POSTAL_CODE = 'Postal Code'
ATTR_COUNRTY = 'Country'
ATTR_HOUSE_NUMBER = 'House Number'
ATTR_COUNTY = 'County'
ATTR_DISPLAY_NAME = 'Display Name'
ATTR_NAME_DETAILS = 'Name Details'

DEFAULT_NAME = 'OpenStreetMap Geocode'
DEFAULT_OPTION = 'street'
current = '0,0'
zone_check = 'a'
SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ORIGIN): cv.string,
    vol.Optional(CONF_OPTIONS, default=DEFAULT_OPTION): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
        cv.time_period,
})

TRACKABLE_DOMAINS = ['device_tracker', 'sensor']

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    name = config.get(CONF_NAME)
    origin = config.get(CONF_ORIGIN)
    options = config.get(CONF_OPTIONS)

    add_devices([GoogleGeocode(hass, origin, name, options)])
    

class GoogleGeocode(Entity):
    """Representation of a Google Geocode Sensor."""

    def __init__(self, hass, origin, name, options):
        """Initialize the sensor."""
        self._hass = hass
        self._name = name
        self._options = options.lower()
        self._state = "Awaiting Update"
        
        self._street = None
        self._city = None
        self._town = None
        self._region = None
        self._postal_code = None
        self._country = None
        self._house_number = None
        self._county = None
        self._display_name = None
        self._name_details = None
        
        # self._origin = origin
        # Check if origin is a trackable entity
        if origin.split('.', 1)[0] in TRACKABLE_DOMAINS:
            self._origin_entity_id = origin
        else:
            self._origin = origin
            
        
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
        
    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return{
            ATTR_STREET: self._street,
            ATTR_CITY: self._city,
            ATTR_TOWN: self._town,
            ATTR_REGION: self._region,
            ATTR_POSTAL_CODE: self._postal_code,
            ATTR_COUNRTY: self._country,
            ATTR_HOUSE_NUMBER: self._house_number,
            ATTR_COUNTY: self._county,
            ATTR_DISPLAY_NAME: self._display_name,
            ATTR_NAME_DETAILS: self._name_details,
        }
        
    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest data and updates the states."""
        
        if hasattr(self, '_origin_entity_id'):
            self._origin = self._get_location_from_entity(
                self._origin_entity_id
            )
        
        """Update if location has changed."""

        global current
        global zone_check
        zone_check = self.hass.states.get(self._origin_entity_id).state
        
        if zone_check == 'not_home':
            if current == self._origin:
                pass
            elif self._origin == None:
                pass
            else:
                lat = self._origin
                current = lat
                self._reset_attributes()
                url = "http://nominatim.openstreetmap.org/reverse?format=json&lat=" + lat + "&zoom=18&addressdetails=1&namedetails=1"
                response = get(url)
                json_input = response.text
                decoded = json.loads(json_input)
                street = 'Unnamed Road'
                city = ''
                town = ''
                display_name = ''
                state = ''
                country = ''
                county = ''
                name_details = ''
                
                if "road" in decoded["address"]:
                    street = decoded["address"]["road"]
                    self._street = street
                if "city" in decoded["address"]:
                    city = decoded["address"]["city"]
                    self._city = city
                if "town" in decoded["address"]:
                    town = decoded["address"]["town"]
                    self._town = town
                if "state" in decoded["address"]:
                    region = decoded["address"]["state"]
                    self._region = region
                if "postcode" in decoded["address"]:
                    postal_code = decoded["address"]["postcode"]
                    self._postal_code = postal_code
                if "country" in decoded["address"]:
                    country = decoded["address"]["country"]
                    self._country = country
                if "house_number" in decoded["address"]:
                    house_number = decoded["address"]["house_number"]
                    self._house_number = house_number
                if "county" in decoded["address"]:
                    county = decoded["address"]["county"]
                    self._county = county
                if "display_name" in decoded:
                    display_name = decoded["display_name"]
                    self._display_name = display_name
                if "namedetails" in decoded:
                    name_details = decoded["namedetails"]["name"]
                    self._name_details = name_details

                    
                if self._options == 'city':
                    if city == '':
                        ADDRESS = town
                        if town == '':
                            ADDRESS = county
                    else:
                        ADDRESS = city
                elif self._options == 'street':
                    ADDRESS = street
                elif self._options == 'both':
                    if city == '':
                        ADDRESS = street + ", " + town
                        if town == '':
                            ADDRESS = street + ", " + county
                    else:
                        ADDRESS = street + ", " + city
                if self._options == 'place':
                    if name_details == '':
                        ADDRESS = street
                    else:
                        ADDRESS = name_details + ", " + street
                elif self._options == 'full':
                    ADDRESS = display_name
                elif self._options == 'state':
                    ADDRESS = region
                elif self._options == 'country':
                    ADDRESS = country
                    
                self._state = ADDRESS
                
        else:
            self._state = zone_check[0].upper() + zone_check[1:]
            self._reset_attributes()


    def _get_location_from_entity(self, entity_id):
        """Get the origin from the entity state or attributes."""
        entity = self._hass.states.get(entity_id)
        
        
        if entity is None:
            _LOGGER.error("Unable to find entity %s", entity_id)
            return None

        # Check if the entity has origin attributes
        if location.has_location(entity):
            return self._get_location_from_attributes(entity)

        # When everything fails just return nothing
        return None
        
    def _reset_attributes(self):
        self._street = None
        self._city = None
        self._town = None
        self._region = None
        self._postal_code = None
        self._country = None
        self._house_number = None
        self._county = None
        self._display_name = None
        self._name_details = None

    @staticmethod
    def _get_location_from_attributes(entity):
        """Get the lat/long string from an entities attributes."""
        attr = entity.attributes
        return "%s&lon=%s" % (attr.get(ATTR_LATITUDE), attr.get(ATTR_LONGITUDE))
