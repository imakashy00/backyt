import requests

url = "https://ip.smartproxy.com/json"
username = "spb8asd29b"
password = "1S4boe~sh8WldHp0gY"
proxy = f"http://{username}:{password}@gate.smartproxy.com:7000"
result = requests.get(url, proxies={"http": proxy, "https": proxy})
print(result.text)
