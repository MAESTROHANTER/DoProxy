import asyncio
import aiohttp
import sys
import asyncssh

async def wait_for_enter(timeout=200):
    try:
        await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, input, "Нажмите Enter для продолжения..."), timeout)
    except asyncio.TimeoutError:
        print("Время ожидания истекло, продолжаем выполнение скрипта...")
        sys.exit(0)

async def setup_wireguard(server_login, server_ip, server_password, local_config_path):
    try:
        async with asyncssh.connect(server_ip, username=server_login, password=server_password, known_hosts=None) as conn:
            print(f"Загрузка и установка WireGuard на {server_ip}...")
            await conn.run('wget -O /root/wg_installer.sh https://get.vpnsetup.net/wg && chmod +x /root/wg_installer.sh && sudo /root/wg_installer.sh --auto', check=True)
            await asyncio.sleep(30)  # Даем время на установку
            print(f"WireGuard установлен на {server_ip}.")
            async with conn.start_sftp_client() as sftp:
                await sftp.get('/root/client.conf', localpath=local_config_path)
            print(f"Конфигурационный файл wireguard скачан - {local_config_path}.")
    except Exception as e:
        print(f"Ошибка при настройке WireGuard на {server_ip}: {e}")

async def setup_socks5(server_login, server_ip, server_password):
    try:
        async with asyncssh.connect(server_ip, username=server_login, password=server_password, known_hosts=None) as conn:
            print(f"Настройка SOCKS5 на {server_ip}...")
            await conn.run("export PORT=8080; export PASSWORD=Sobaka54gol0s; curl https://selivan.github.io/socks.txt | sudo --preserve-env bash", check=True)
            print(f"Прокси SOCKS5 готов! socks5://root:Sobaka54gol0s@{server_ip}:8080")
    except Exception as e:
        print(f"Ошибка при настройке SOCKS5 на {server_ip}: {e}")

async def setup_http(server_login, server_ip, server_password):
    try:
        async with asyncssh.connect(server_ip, username=server_login, password=server_password, known_hosts=None) as conn:
            print(f"Настройка HTTP прокси на {server_ip}...")
            result = await conn.run("wget https://raw.githubusercontent.com/serverok/squid-proxy-installer/master/squid3-install.sh && chmod +x squid3-install.sh && sudo bash squid3-install.sh", check=False)
            await asyncio.sleep(60)  # Даем время на настройку
            result = await conn.run("sudo /usr/bin/htpasswd -b -c /etc/squid/passwd root Sobaka54gol0s", check=False)
            if result.exit_status == 0:
                print(f"Прокси HTTP готов! http://root:Sobaka54gol0s@{server_ip}:3128")
            else:
                print(f"Ошибка при настройке HTTP на {server_ip}. Код выхода: {result.exit_status}")
    except Exception as e:
        print(f"Ошибка при настройке HTTP на {server_ip}: {e}")

async def get_ssh_keys_async(api_key):
    async with aiohttp.ClientSession() as session:
        url = "https://api.vultr.com/v2/ssh-keys"
        headers = {"Authorization": f"Bearer {api_key}"}
        async with session.get(url, headers=headers) as response:
            keys = await response.json()
            if keys['ssh_keys']:
                #print(f"Используется id SSH ключа: {keys['ssh_keys'][0]['id']}")
                return keys['ssh_keys'][0]['id']  # Возвращаем первый доступный id ключа
            else:
                print("SSH ключ не найден. Пожалуйста, создайте ключ через веб-интерфейс Vultr.")
                return None

async def create_vultr_server_async(api_key, ssh_key_id):
    async with aiohttp.ClientSession() as session:
        url = "https://api.vultr.com/v2/instances"
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "region": "ewr",
            "plan": "vc2-1c-1gb",
            "os_id": 387,
            "sshkey_id": [ssh_key_id],
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
                    await asyncio.sleep(10)

async def create_and_log_server(api_key, ssh_key_id, delay=0):
    await asyncio.sleep(delay)  # Задержка перед началом создания сервера
    server_id, server_login, server_password = await create_vultr_server_async(api_key, ssh_key_id)
    if server_id:
        print(f"Сервер создан, ID: {server_id}. Ожидание IP-адреса...")
        main_ip = await wait_for_server_ip_async(api_key, server_id)
        if main_ip:
            print(f"Сервер готов: {server_login}:{main_ip}:{server_password}. Ждём установки зависимостей...")
            await asyncio.sleep(100)
            return server_login, main_ip, server_password # Возвращаем данные для использования в main
        else:
            print("IP-адрес не был назначен серверу вовремя.")
            return None
    else:
        print("Не удалось создать сервер.")
        return None

async def setup_servers(server_infos, proxy_type):
    tasks = []
    for server_info in server_infos:
        server_login, server_ip, server_password = server_info.split(':')
        local_config_path = f'VPN_{server_ip}.conf'
        if proxy_type == "wireguard":
            task = setup_wireguard(server_login, server_ip, server_password, local_config_path)
        elif proxy_type == "socks5":
            task = setup_socks5(server_login, server_ip, server_password) 
        elif proxy_type == "http":
            task = setup_http(server_login, server_ip, server_password)
        tasks.append(asyncio.create_task(task))
    await asyncio.gather(*tasks)

async def main():
    print("Выберите действие:")
    print("1. Vultr")
    print("2. Настроить прокси на уже готовых серверах (socks5/http только для ubuntu 20.04)")
    choice = input(": ")

    if choice == "1":
        api_key = input("Введите API ключ: ")
        ssh_key_id = await get_ssh_keys_async(api_key)  # Получаем ssh_key_id автоматически
        if not ssh_key_id:
            sys.exit
        print("Выберите тип прокси для создания:\n1. socks5\n2. http\n3. Wireguard")
        proxy_choice = input(": ")
        proxy_type = "socks5" if proxy_choice == "1" else "http" if proxy_choice == "2" else "wireguard" if proxy_choice == "3" else "socks5"
        quantity = int(input("Введите количество создаваемых прокси: "))
        #await asyncio.sleep(10)
        tasks = [create_and_log_server(api_key, ssh_key_id, i*10) for i in range(quantity)]
        servers = await asyncio.gather(*tasks)
        
        server_infos = [f"{server_login}:{server_ip}:{server_password}" for server_login, server_ip, server_password in servers if server_login is not None]
        await setup_servers(server_infos, proxy_type)
        await wait_for_enter()
        sys.exit
        '''
        servers = await asyncio.gather(*[create_and_log_server(api_key, ssh_key_id) for _ in range(quantity)])
        server_infos = [f"{server_login}:{server_ip}:{server_password}" for server_login, server_ip, server_password in servers if server_login is not None]
        await setup_servers(server_infos, proxy_type)
        await wait_for_enter()
        sys.exit(0)
        '''
        '''
        servers = []
        for _ in range(quantity):
            server = await create_and_log_server(api_key, ssh_key_id)
            servers.append(server)
            await asyncio.sleep(10)  # Задержка между созданием серверов

        server_infos = [f"{server_login}:{server_ip}:{server_password}" for server_login, server_ip, server_password in servers if server_login is not None]
        await setup_servers(server_infos, proxy_type)
        await wait_for_enter()
        sys.exit(0)
        '''
        

    elif choice == "2":
        server_info_input = input("Введите данные серверов в таком формате, где каждый новый сервер отделён пробелом -> server_login:server_ip:server_password\n: ")
        server_infos = server_info_input.split()
        print("Выберите тип прокси для настройки:\n1. socks5\n2. http\n3. Wireguard")
        proxy_choice = input(": ") or "1"
        proxy_type = "socks5" if proxy_choice == "1" else "http" if proxy_choice == "2" else "wireguard"
        await setup_servers(server_infos, proxy_type)
        await wait_for_enter()
        sys.exit(0)
    else:
        print("Неверный выбор.")
        return

    sys.exit(0)

asyncio.run(main())