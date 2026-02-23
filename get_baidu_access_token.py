import json
import requests

def get_baidu_access_token():
    url = ("https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&"
           "client_id=S8Ql2TN2FjOT7O9LmbOPasWm&client_secret=5gcNIzn0le2crcSHrqRBy8A1CY8gapgW") #修改成系统变量
    payload = ""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    #print(response.text) #这里可以记录log
    json_data = json.loads(response.text)
    access_token = json_data.get("access_token")
    #print("Access Token:", access_token)
    return access_token