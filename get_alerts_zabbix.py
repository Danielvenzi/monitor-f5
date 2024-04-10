#!/usr/bin/python3
import requests
from datetime import datetime, timedelta, time, date
import time as timet
import telegram
import asyncio


# Definicação de intervalo de epoch para coleta de alertas do dia de hoje (00h até 23:59)
#midnight = datetime.combine(datetime.today(), time.min)
# midnight = int(midnight.timestamp())
# today_twenty_three = int(midnight) + 86399


def get_auth_token():

    # Payload para autenticação na API do Zabbix
    auth_payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": "Admin",
            "password": "Niv@ti.1010"
        },
        "auth": None,
        "id": 0
    }

    response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=auth_payload)
    auth_response = response.json()

    return auth_response['result']

def deauth_from_zabbix(auth_token):

    payload = {
        "jsonrpc": "2.0",
        "method": "user.logout",
        "params": [],
        "id": 1,
        "auth": str(auth_token)
    }

    response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=payload)
    deauth_response = response.json()

    print(deauth_response)


def get_alerts_info(auth_token, group_id, now, now_minus_one):

    alert_query = {
            "jsonrpc": "2.0",
            "method": "alert.get",
            "params": {
                "output": "extend",
                "groupids": str(group_id),
                "time_from": str(now_minus_one),
                "time_till": str(now)
            },
            "auth": str(auth_token),
            "id": 1
        }
    
    # Tenta coletar os alertas do Zabbix
    try:

        response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=alert_query)
        query_response = response.json()

        result = query_response['result']

    # Tenta fazer a query 6 vezes em caso de timeout
    except requests.exceptions.Timeout as err:
        counter = 0
        result = []
        while counter <= 5:

            try:
                response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=alert_query)
                query_response = response.json()

                result = query_response['result']

            except requests.exceptions.Timeout:
                pass

            counter += 1

    # Trata o erro Connection Error
    except requests.exceptions.ConnectionError as err:
        print(err)
        result = []
        pass

    # Trata o erro Too Many Requests
    except requests.exceptions.TooManyRedirects as err:
        print(err)
        result = []
        pass


    # Trata o erro HTTP Error
    except requests.exceptions.HTTPError as err:
        print(err)
        result = []
        pass

    return result


def get_user_groups_ids(auth_token):

    user_group_query = {
            "jsonrpc": "2.0",
            "method": "usergroup.get",
            "params": {
                "output": "extend",
                "status": 0
            },
            "auth": str(auth_token),
            "id": 1
        }

    response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=user_group_query)
    query_response = response.json()

    print(query_response)

def get_user_groups(auth_token):

    user_group_query = {
                "jsonrpc": "2.0",
                "method": "hostgroup.get",
                "params": {
                    "output": "extend",
                    "groupid": "43"
                },
                "auth": str(auth_token),
                "id": 1
            }
    
    response = requests.post("http://172.20.0.24/zabbix/api_jsonrpc.php", json=user_group_query)
    query_response = response.json()

    print(query_response)

async def send_telegram_message(message):

    BOT_TOKEN = "6670572669:AAHboCwTu-W33MdcKzMKS_GDpSw4VIMs8LI"

    bot = telegram.Bot(token=BOT_TOKEN)

    await bot.send_message(chat_id=-4106059457, text=message)


sent_ids = []
sent_alerts = {}

if __name__ == "__main__":

    ids_ttl = int(timet.time())
    while True:

        # Função que coleta o token de autenticação
        api_token = get_auth_token()

        # mpdft_group_id = '43'
        # mpm_group_id = '39'
        #group_ids = ['43','39']

        group_ids = {
            '43':'MPDFT',
            '39':'MPM'
        }

        # Gera os epoch timestamps para o intervalo de 1 minuto atrás até agora
        now = datetime.now()
        now = int(now.timestamp())
        now_minus_one = now - 3600

        for gid in list(group_ids.keys()):
            
            result_alerts = get_alerts_info(api_token, gid, now, now_minus_one)
            #result_alerts = [{'alertid': '13020', 'actionid': '7', 'eventid': '13413450', 'userid': '16', 'clock': '1712599022', 'mediatypeid': '5', 'sendto': 'atendimento@nivati.com.br', 'subject': 'Problem: Avantdata FP2-SEG-003 NDR is unavailable by ICMP', 'message': 'NOTE: Escalation cancelled: host "fp2-seg-003" disabled.\nProblem started at 18:57:27 on 2024.03.08\r\nProblem name: Avantdata FP2-SEG-003 NDR is unavailable by ICMP\r\nHost: Avantdata FP2-SEG-003 NDR\r\nSeverity: Disaster\r\n\r\nOriginal problem ID: 13413450\r\n', 'status': '1', 'retries': '0', 'error': '', 'esc_step': '1', 'alerttype': '0', 'p_eventid': '0', 'acknowledgeid': '0'}]
            if len(result_alerts) == 0:
                print("No alerts in group {} - {}".format(gid, group_ids[gid]))
                continue

            print(result_alerts)

            for alert in result_alerts:
                
                # Verifica se o eventID já foi enviado
                if alert['eventid'] not in sent_ids:

                    # Verifica se o alerta específico desse evento já foi enviado
                    if alert['alertid'] not in list(sent_alerts.keys()):

                        sent_alerts[alert['eventid']] = [alert['alertid']]

                    print("Novo alerta - {} - {}".format(alert['eventid'], alert['alertid']))

                    #TODO fazer a comunicação com telegram aqui
                    asyncio.run(send_telegram_message("ALERT {}\n\nSUBJECT: {}\n\nMESSAGE: {}\n".format(group_ids[gid], 
                                                                            alert['subject'], 
                                                                            alert['message'])))

                    sent_ids.append(alert['eventid'])

                # Se o evento já tiver sido reportado verifica se o alerta é diferente
                elif alert['eventid'] in sent_ids:

                    if alert['alertid'] not in sent_alerts[alert['eventid']]:

                        sent_alerts[alert['eventid']].append(alert['alertid'])

                        print("Novo alerta - {} - {}".format(alert['eventid'], alert['alertid']))

                        #TODO fazer a comunicação com telegram aqui
                        asyncio.run(send_telegram_message("ALERT {}\n\nSUBJECT: {}\n\nMESSAGE: {}\n".format(group_ids[gid], 
                                                                                alert['subject'], 
                                                                                alert['message'])))

                    else:

                        pass

        # Função apra desautenticar a sessão do usuário Admin na API do Zabbix
        deauth_from_zabbix(api_token)

        # Verifica se já passou 1h e podemos resetar os IDs dos alertas já enviados (para não usar muita memória)
        check_now = timet.time()
        if (check_now-ids_ttl) >= 3600:
            
            # Inicia o novo Time To Live dos IDs
            ids_ttl = int(timet.time())

            # Limpa os IDs já enviados
            sent_ids.clear()

            # Limpa os alertas já enviados
            sent_alerts.clear()

        # Esperar por 60 segundos para refazer a pesquisa por alertas
        timet.sleep(60)

        #get_user_groups_ids(api_token)

        #get_user_groups(api_token)
