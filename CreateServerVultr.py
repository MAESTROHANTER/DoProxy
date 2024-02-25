import asyncio
import aiohttp

async def setup_wireguard(server_login, server_ip, server_password, local_config_path):
    # Заглушка для функции настройки WireGuard
    print(f"WireGuard настраивается на {server_ip}")

async def setup_socks5(server_login, server_ip, server_password):
    # Заглушка для функции настройки SOCKS5
    print(f"SOCKS5 настраивается на {server_ip}")

async def setup_http(server_login, server_ip, server_password):
    # Заглушка для функции настройки HTTP
    print(f"HTTP настраивается на {server_ip}")

async def get_ssh_keys_async(api_key):
    async with aiohttp.ClientSession() as session:
        url = "https://api.vultr.com/v2/ssh-keys"
        headers = {"Authorization": f"Bearer {api_key}"}
        async with session.get(url, headers=headers) as response:
            keys = await response.json()
            for key in keys['ssh_keys']:
                print(f"SSH ключ: {key['id']}")
                await asyncio.sleep(1000000)

async def create_vultr_server_async(api_key, ssh_key_id):
    async with aiohttp.ClientSession() as session:
        url = "https://api.vultr.com/v2/instances"
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "region": "ewr",
            "plan": "vc2-1c-1gb",
            "os_id": 387,
            "sshkey_id": [ssh_key_id],
            "default_password": "Sobaka54gol0s",
        }
        async with session.post(url, json=data, headers=headers) as response: 
            instance = await response.json()
            instance_data = instance['instance']
            return instance_data['id'], instance_data.get('user_scheme', 'root'), instance_data['default_password']

async def wait_for_server_ip_async(api_key, server_id):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.vultr.com/v2/instances/{server_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        while True:
            async with session.get(url, headers=headers) as response:
                instance = await response.json()
                main_ip = instance['instance']['main_ip']
                if main_ip != "0.0.0.0":
                    return main_ip
                else:
                    await asyncio.sleep(5)

async def create_and_log_server(api_key, ssh_key_id):
    server_id, server_login, server_password = await create_vultr_server_async(api_key, ssh_key_id)
    if server_id:
        print(f"Сервер создан, ID: {server_id}. Ожидание IP-адреса...")
        main_ip = await wait_for_server_ip_async(api_key, server_id)
        if main_ip:
            print(f"Сервер готов: {server_login}:{main_ip}:{server_password}")
            await asyncio.sleep(1000000)
        else:
            print("IP-адрес не был назначен серверу вовремя.")
    else:
        print("Не удалось создать сервер.")

async def main():
    print("Выберите действие:")
    print("1. Создать сервера")
    print("2. Получить ID SSH ключа")
    choice = input(": ")

    api_key = input("Введите API ключ: ")

    if choice == "2":
        await get_ssh_keys_async(api_key)
    elif choice == "1":
        ssh_key_id = input("Введите ID SSH ключа: ")
        quantity = int(input("Введите количество создаваемых серверов: "))
        tasks = [create_and_log_server(api_key, ssh_key_id) for _ in range(quantity)]
        await asyncio.gather(*tasks)
    else:
        print("Неверный выбор.")

asyncio.run(main())
