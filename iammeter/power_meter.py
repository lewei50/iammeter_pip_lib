#!/usr/bin/env python3
# -*- coding: utf-8 -*
import json
from collections import namedtuple
import requests

import aiohttp
import voluptuous as vol
import logging
_LOGGER = logging.getLogger(__name__)

class IamMeterError(Exception):
    """Indicates error communicating with iammeter"""


class DiscoveryError(Exception):
    """Raised when unable to discover iammeter"""


IamMeterResponse = namedtuple('IamMeterResponse',
                              'data, serial_number, mac')
                              

class IamMeter:
    """Base wrapper around iammeter HTTP API"""
    def __init__(self, host, port, sn):
        self.host = host
        self.port = port
        self.serial_number = sn
        self.mac = ""

    async def get_data(self):
        try:
            data = await self.make_request(
                self.host, self.port
            )
            self.serial_number = data.serial_number
            self.mac = data.mac
        except aiohttp.ClientError as ex:
            msg = "Could not connect to iammeter endpoint"
            raise IamMeterError(msg) from ex
        except ValueError as ex:
            msg = "Received non-JSON data from iammeter endpoint"
            raise IamMeterError(msg) from ex
        except vol.Invalid as ex:
            msg = "Received malformed JSON from iammeter"
            raise IamMeterError(msg) from ex
        except:
        	msg = "error"
        	raise IamMeterError("error")
        return data

    @classmethod
    async def make_request(cls, host, port):
        """
        Return instance of 'iammeterResponse'
        Raise exception if unable to get data
        """
        raise NotImplementedError()

    @classmethod
    def sensor_map(cls):
        """
        Return sensor map
        """
        raise NotImplementedError()

async def fetch(url):
    async with aiohttp.request("GET",url) as r:
        #_LOGGER.error(r.status)
        reponse = await r.text(encoding="utf-8")
        #yield reponse
        
async def discover(host, port) -> IamMeter:
    base = 'http://admin:admin@{}:{}/monitorjson'
    url = base.format(host, port)
    #_LOGGER.error(url)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                #_LOGGER.error(resp.status)
                txt_data = await resp.text()
                json_data = json.loads(txt_data)
                #_LOGGER.error(json_data)
                #json_response = json.loads(json_data)
                sn = ""
                if 'SN' in json_data:
                    sn = json_data['SN']
                if 'data' in json_data:
                    #_LOGGER.info('3162')
                    return WEM3162(host,port,sn)
                if 'Data' in json_data:
                    #_LOGGER.info('3080')
                    return WEM3080(host,port,sn)
                if 'Datas' in json_data:
                    #_LOGGER.info('3080T')
                    return WEM3080T(host,port,sn)
                #return json_data
        raise DiscoveryError()
    except aiohttp.client_exceptions.ServerDisconnectedError:
        raise IamMeterError("Server Disconnected Error")
    
class WEM3162(IamMeter):
    __schema = vol.Schema({
    	vol.Required('data'): list,
    }, extra=vol.REMOVE_EXTRA)
	#Voltage,Current,Power,ImportEnergy,ExportGrid,frequency,PF
    __sensor_map = {
        'Voltage':                (0, 0, 'V'),
        'Current':                (0, 1, 'A'),
        'Power':                  (0, 2, 'W'),
        'ImportEnergy':           (0, 3, 'kWh'),

        'ExportGrid':             (0, 4, 'kWh'),
    }
    
    @staticmethod
    def map_response(resp_data, sensor_map):
        return {
            f"{sensor_name}": resp_data[j]
            for sensor_name, (i, j, _)
            in sensor_map.items()
        }

    @classmethod
    async def make_request(cls, host, port=80):
        base = 'http://admin:admin@{}:{}/monitorjson'
        url = base.format(host, port)
        #_LOGGER.error(url)
        #resp = requests.get(url)
        #txt_response = resp.text
        #json_response = json.loads(txt_response)
        #_LOGGER.error(json_response)
        #response = cls.__schema(json_response)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as req:
                garbage = await req.read()
        formatted = garbage.decode("utf-8")
        json_response = json.loads(formatted)
        response = cls.__schema(json_response)
        #_LOGGER.error(cls.map_response(response['data'], cls.__sensor_map))
        cls.dev_type = "WEM3162"
        return IamMeterResponse(
            data=cls.map_response(response['data'], cls.__sensor_map),
            serial_number="",
            mac=""
        )

    @classmethod
    def sensor_map(cls):
        """
        Return sensor map
        """
        return cls.__sensor_map


class WEM3080(IamMeter):
    __schema = vol.Schema({
    	vol.Required('SN'): str,
    	vol.Required('mac'): str,
    	vol.Required('Data'): list,
    }, extra=vol.REMOVE_EXTRA)
	#Voltage,Current,Power,ImportEnergy,ExportGrid,frequency,PF
    __sensor_map = {
        'Voltage':                (0, 0, 'V'),
        'Current':                (0, 1, 'A'),
        'Power':                  (0, 2, 'W'),
        'ImportEnergy':           (0, 3, 'kWh'),

        'ExportGrid':             (0, 4, 'kWh'),

    }
    
    @staticmethod
    def map_response(resp_data, sensor_map):
        return {
            f"{sensor_name}": resp_data[j]
            for sensor_name, (i, j, _)
            in sensor_map.items()
        }

    @classmethod
    async def make_request(cls, host, port=80):
        base = 'http://admin:admin@{}:{}/monitorjson'
        url = base.format(host, port)
        #_LOGGER.error(url)
        #resp = requests.get(url)
        #json_response = resp.json()
        #_LOGGER.error(json_response)
        #response = cls.__schema(json_response)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as req:
                garbage = await req.read()
        formatted = garbage.decode("utf-8")
        json_response = json.loads(formatted)
        response = cls.__schema(json_response)
        #_LOGGER.error(cls.map_response(response['Data'], cls.__sensor_map))
        cls.dev_type = "WEM3080"
        return IamMeterResponse(
            data=cls.map_response(response['Data'], cls.__sensor_map),
            serial_number=response['SN'],
            mac=response['mac']
        )

    @classmethod
    def sensor_map(cls):
        """
        Return sensor map
        """
        return cls.__sensor_map



class WEM3080T(IamMeter):
    __schema = vol.Schema({
    	vol.Required('SN'): str,
    	vol.Required('mac'): str,
    	vol.Required('Datas'): list,
    }, extra=vol.REMOVE_EXTRA)
	#Voltage,Current,Power,ImportEnergy,ExportGrid,frequency,PF
    __sensor_map = {
        'Voltage_A':                (0,0, 'V'),
        'Current_A':                (0,1, 'A'),
        'Power_A':                  (0,2, 'W'),
        'ImportEnergy_A':           (0,3, 'kWh'),

        'ExportGrid_A':             (0,4, 'kWh'),
        'Frequency_A':              (0,5, 'Hz'),
        'PF_A':                     (0,6, ''),

        'Voltage_B':                (1,0, 'V'),
        'Current_B':                (1,1, 'A'),
        'Power_B':                  (1,2, 'W'),
        'ImportEnergy_B':           (1,3, 'kWh'),

        'ExportGrid_B':             (1,4, 'kWh'),
        'Frequency_B':              (1,5, 'Hz'),
        'PF_B':                     (1,6, ''),
        
        'Voltage_C':                (2,0, 'V'),
        'Current_C':                (2,1, 'A'),
        'Power_C':                  (2,2, 'W'),
        'ImportEnergy_C':           (2,3, 'kWh'),

        'ExportGrid_C':             (2,4, 'kWh'),
        'Frequency_C':              (2,5, 'Hz'),
        'PF_C':                     (2,6, ''),
    }
    
    @staticmethod
    def map_response(resp_data, sensor_map):
        return {
            f"{sensor_name}": resp_data[i][j]
            for sensor_name, (i,j,_)
            in sensor_map.items()
        }

    @classmethod
    async def make_request(cls, host, port=80):
        base = 'http://admin:admin@{}:{}/monitorjson'
        url = base.format(host, port)
        #_LOGGER.error(url)
        #resp = requests.get(url)
        #json_response = resp.json()
        #response = cls.__schema(json_response)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as req:
                garbage = await req.read()
        formatted = garbage.decode("utf-8")
        json_response = json.loads(formatted)
        response = cls.__schema(json_response)
        #_LOGGER.error(response)
        #_LOGGER.error(cls.map_response(response['Datas'], cls.__sensor_map))
        cls.dev_type = "WEM3080T"
        return IamMeterResponse(
            data=cls.map_response(response['Datas'], cls.__sensor_map),
            serial_number=response['SN'],
            mac=response['mac']
        )

    @classmethod
    def sensor_map(cls):
        """
        Return sensor map
        """
        return cls.__sensor_map


# registry of iammeters
REGISTRY = [WEM3080,WEM3080T,WEM3162]