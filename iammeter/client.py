# coding: utf-8

IAMMETER_REQUEST_URL = 'http://admin:admin@{}:{}/monitorjson'

import requests

class IamMeter:
    """Base wrapper around iammeter HTTP API"""
    def __init__(self, host, port = 80, sn = ""):
        self.host = host
        self.port = port
        self.serial_number = sn
        self.mac = ""
        self.client = Client(host, port)
        self.measurement = self.client.get_data()
        self.model = self.measurement["Model"]

class Client(object):
    def __init__(self, ip, port = 80):
        self.ip = ip
        self.port = port
        self.url = IAMMETER_REQUEST_URL

    def get_data(self):
        url = self.url.format(self.ip, self.port)
        r = requests.get(url)
        return(self.parse_data(r.json()))

    def parse_data(self, data):
        #WEM3162
        if 'data' in data:
            out = {
                "Model":"WEM3162",
                "Voltage":data["Data"][0],
                "Current":data["Data"][1],
                "Power":data["Data"][2],
                "ImportEnergy":data["Data"][3],
                "ExportGrid":data["Data"][4]
            }
        #WEM3080
        if 'Data' in data:
            out = {
                "Model":"WEM3080",
                "sn":data["SN"],
                "mac":data["mac"],
                "Voltage":data["Data"][0],
                "Current":data["Data"][1],
                "Power":data["Data"][2],
                "ImportEnergy":data["Data"][3],
                "ExportGrid":data["Data"][4]
            }
        #WEM3080T
        if 'Datas' in data:
            out = {
                "Model":"WEM3080T",
                "sn":data["SN"],
                "mac":data["mac"],
                "Voltage_A":data["Datas"][0][0],
                "Current_A":data["Datas"][0][1],
                "Power_A":data["Datas"][0][2],
                "ImportEnergy_A":data["Datas"][0][3],
                "ExportGrid_A":data["Datas"][0][4],
                "Frequency_A":data["Datas"][0][5],
                "PF_A":data["Datas"][0][6],
                "Voltage_B":data["Datas"][1][0],
                "Current_B":data["Datas"][1][1],
                "Power_B":data["Datas"][1][2],
                "ImportEnergy_B":data["Datas"][1][3],
                "ExportGrid_B":data["Datas"][1][4],
                "Frequency_B":data["Datas"][1][5],
                "PF_B":data["Datas"][1][6],
                "Voltage_C":data["Datas"][2][0],
                "Current_C":data["Datas"][2][1],
                "Power_C":data["Datas"][2][2],
                "ImportEnergy_C":data["Datas"][2][3],
                "ExportGrid_C":data["Datas"][2][4],
                "Frequency_C":data["Datas"][2][5],
                "PF_C":data["Datas"][2][6],
            }
            try:
                out["Voltage_Net"]=data["Datas"][3][0]
                out["Power_Net"]=data["Datas"][3][2]
                out["ImportEnergy_Net"]=data["Datas"][3][3]
                out["ExportGrid_Net"]=data["Datas"][3][4]
                out["Frequency_Net"]=data["Datas"][3][5]
                out["PF_Net"]=data["Datas"][3][6]
            except:
                print("Data format not implement.")
        return out
