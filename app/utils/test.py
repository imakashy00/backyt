import requests


def test_proxy():
    username = "spb8asd29b"
    password = "wlvz_skyJviL90T44D"
    proxy = f"socks5h://{username}:{password}@gate.smartproxy.com:7000"
    proxies = {"http": proxy, "https": proxy}

    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies)
        print(f"Proxy test result: {response.json()}")
        return True
    except Exception as e:
        print(f"Proxy test failed: {e}")
        return False


test_proxy()
