import asyncssh
import asyncio

async def setup_wireguard(server_ip, server_password, local_config_path):
    try:
        async with asyncssh.connect(server_ip, username='root', password=server_password, known_hosts=None) as conn:
            print(f"Загрузка и установка WireGuard на {server_ip}...")
            await conn.run('wget -O /root/wg_installer.sh https://get.vpnsetup.net/wg && chmod +x /root/wg_installer.sh && sudo /root/wg_installer.sh --auto', check=True)
            await asyncio.sleep(30)  # Даем время на установку
            print(f"WireGuard установлен на {server_ip}.")
            async with conn.start_sftp_client() as sftp:
                await sftp.get('/root/client.conf', localpath=local_config_path)
            print(f"Конфигурационный файл скачан - {local_config_path}.")
    except Exception as e:
        print(f"Ошибка при настройке WireGuard на {server_ip}: {e}")

async def setup_socks5(server_ip, server_password):
    try:
        async with asyncssh.connect(server_ip, username='root', password=server_password, known_hosts=None) as conn:
            print(f"Настройка SOCKS5 на {server_ip}...")
            await conn.run("export PORT=8080; export PASSWORD=Sobaka54gol0s; curl https://selivan.github.io/socks.txt | sudo --preserve-env bash", check=True)
            await asyncio.sleep(20)  # Даем время на настройку
            print(f"Прокси SOCKS5 готов! socks5://root:Sobaka54gol0s@{server_ip}:8080")
    except Exception as e:
        print(f"Ошибка при настройке SOCKS5 на {server_ip}: {e}")

async def setup_http(server_ip, server_password):
    try:
        async with asyncssh.connect(server_ip, username='root', password=server_password, known_hosts=None) as conn:
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

async def setup_servers(server_ips_with_passwords, proxy_type):
    tasks = []
    for server_info in server_ips_with_passwords:
        server_ip, server_password = server_info.split(':')
        local_config_path = f'VPN_{server_ip}.conf'  # Путь к файлу конфигурации для WireGuard
        if proxy_type == "wireguard":
            task = setup_wireguard(server_ip, server_password, local_config_path)
        elif proxy_type == "socks5":
            task = setup_socks5(server_ip, server_password)
        elif proxy_type == "http":
            task = setup_http(server_ip, server_password)
        tasks.append(asyncio.create_task(task))
    await asyncio.gather(*tasks)

async def main():
    server_info_input = input("Введите пары в таком виде -> server_ip:server_password, разделённые пробелом\n: ")
    server_ips_with_passwords = server_info_input.split()
    
    print("Выберите тип прокси (по умолчанию socks5):\n1. socks5 (работает только на ubuntu 20.04, создание за ~ 30 сек)\n2. http (работает только на ubuntu 20.04, создание за ~ 1 мин)\n3. Wireguard (любая ubuntu, создание за ~ 1 мин)")
    proxy_choice = input("Введите номер выбранного варианта [1]: ") or "1"
    proxy_type = "socks5" if proxy_choice == "1" else "http" if proxy_choice == "2" else "wireguard"

    await setup_servers(server_ips_with_passwords, proxy_type)

asyncio.run(main())
