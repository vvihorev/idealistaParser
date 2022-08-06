import os
import json
import time
import datetime
import sqlite3
import smtplib
import requests
from requests.auth import HTTPBasicAuth
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger
from dotenv import load_dotenv


load_dotenv()


class IdealistaAPIManager:
    def request_idealista(self):
        url_value = self.generate_search_request()
        api_key = os.environ.get("IDEALISTA_API_KEY")
        api_secret = os.environ.get("IDEALISTA_API_SECRET")
        if not api_key or not api_secret:
            logger.error("Environment variables IDEALISTA_API_SECRET, IDEALISTA_API_KEY not found")
            exit()
        token_value = self._get_oauth_token(api_key, api_secret)
        search_json = self._search_api(url_value, token_value)
        search_response = json.loads(search_json)
        search_pretty = json.dumps(search_response, indent=4, sort_keys=True)
        logger.debug('Got response from Idealista API.')
        filename = "data/idealista_json_" + time.strftime("%Y-%m-%d_%H-%M") + ".json"
        with open(filename, 'w') as export:
            json.dump(search_pretty, export)
            logger.debug(f'Wrote response to file: {filename}')

    def generate_search_request(self, numPage=1):
        base_idealista_url = "https://api.idealista.com/3.5/it/search"
        search_parameters = {
            "center": "45.469,9.182",
            "distance": "5500",
            "propertyType": "homes",
            "operation": "rent",
            "locale": "en",
            "locationId": "0-EU-IT-MI-01-001-135",
            "sinceDate": "T",
            "maxPrice": "1300",
            "bedroom": "2",
            "maxItems": "50",
            "numPage": f"{numPage}",
            "order": "price",
            "sort": "desc"
        }
        response = requests.post(base_idealista_url, data=search_parameters)
        return base_idealista_url + '?' + response.request.body.replace("%2C", ",")

    def _get_oauth_token(self, key, secret):
        oauth_url = "https://api.idealista.com/oauth/token"
        payload = {"grant_type": "client_credentials"}
        r = requests.post(oauth_url, auth=HTTPBasicAuth(key, secret), data=payload)
        token_response = json.loads(r.text)
        try:
            token_value = token_response["access_token"]
        except KeyError:
            logger.error(f"No access_token found in response. Is the proper API token provided?")
            exit()
        return token_value

    def _search_api(self, url, token):
        headers = {"Authorization": "Bearer " + token}
        r = requests.post(url, headers=headers)
        return r.text


class StorageManager:
    def __init__(self, db_file='db.sqlite', json_data_folder='data/') -> None:
        self.db_file = db_file
        self.json_data_folder = json_data_folder

    def update_flats_in_database(self):
        """Inserts flats into the database"""
        conn = sqlite3.connect("db.sqlite")
        cur = conn.cursor()
        cur.execute( """
            create table
            if not exists houses
            (
                address Text,
                numPhotos Integer,
                price Float,
                priceByArea Float,
                rooms Int,
                thumbnail Text,
                url Text UNIQUE,
                search_date DateTime
            );
            """)
        folder = self.json_data_folder
        files = [folder + x for x in os.listdir(folder)]
        for file in files:
            entries = self._get_flats_from_json(file)
            cur.execute( f"""
                insert or replace into houses
                values {','.join([str(entry) for entry in entries])};
            """)
        cur.close()
        conn.commit()
        conn.close()

    def send_out_new_flats(self, notification_manager, to_email=False):
        """Gets views for_two and for_three from the database"""
        self._create_database_views()
        conn = sqlite3.connect('db.sqlite')
        cur = conn.cursor()
        cur.execute('select * from for_two')
        for_two = cur.fetchall()
        cur.execute('select * from for_three')
        for_three = cur.fetchall()
        cur.close()
        conn.close()
        if to_email:
            notification_manager.send_email(for_two, for_three)
        else:
            with open('results', 'a') as file:
                file.write(f"Flats for: {datetime.datetime.now()}\n\n")
                for flats in [for_two, for_three]:
                    file.write(notification_manager.print_text_flats(flats))
                file.write('\n')

    def _get_flats_from_json(self, filepath: str):
        """Gets flats data from an 'idealista api query results' file"""
        with open(filepath, "r") as file:
            data = json.loads(file.read())
        data = json.loads(data)
        elems = data['elementList']
        fields = ['address', 'numPhotos', 'price', 'priceByArea', 'rooms', 'thumbnail', 'url']
        entries = []
        for elem in elems:
            if 'NO STUDENTS' in elem['description']:
                continue
            elem_fields = [elem[field] for field in fields]
            elem_fields.append(str(datetime.datetime.now()))
            entries.append(tuple(elem_fields))
        return entries

    def _create_database_views(self):
        """Creates views for_two and for_three in the database"""
        conn = sqlite3.connect('db.sqlite')
        cur = conn.cursor()
        cur.execute("""
            create view if not exists for_two as
            select address, price, rooms, url from houses
            where rooms < 3 and price < 1000 and search_date > datetime('now', '-20 hours')
            order by rooms, price;
        """)
        cur.execute("""
            create view if not exists for_three as
            select address, price, rooms, url from houses
            where rooms = 3 and search_date > datetime('now', '-20 hours')
            order by rooms, price;
        """)
        cur.close()
        conn.commit()
        conn.close()


class NoficationManager:
    def print_html_flats(self, flats, for_who='two'):
        msg_body = f"<h1>Flats for {for_who}</h1>"
        for flat in flats:
            msg_body += f"<p>Адрес: {flat[0]}, <b>Цена: {flat[1]}</b>, Комнат: {flat[2]}, Ссылка:{flat[3]}, "
            route_to_uni = "https://www.google.com/maps/dir/Via Festa del Perdono, 7/".replace(' ', '%20') + flat[0].replace(' ', '%20')
            msg_body += "<a href=" + route_to_uni + ">Дорога до уника</a></p>"
        return msg_body

    def print_text_flats(self, flats):
        result = ""
        for flat in flats:
            result += f"{flat[0]};{flat[1]};{flat[2]};{flat[3]}\n"
        return result

    def send_email(self, for_two, for_three):
        msg_body = "<html><head></head><body>"
        msg_body += self.print_html_flats(for_two, 'two')
        msg_body += self.print_html_flats(for_three, 'three')
        msg_body += "</body></html>"

        email_subject = "Новые квартиры за сегодня"
        sender_email_address = os.environ.get("GMAIL_SENDER_ADDRESS")
        receiver_email_address = os.environ.get("GMAIL_RECEIVER_ADDRESS")
        email_smtp = "smtp.gmail.com"
        email_password = os.environ.get("GMAIL_APP_PASSWORD")
          
        message = MIMEMultipart('alternative')
        message['Subject'] = email_subject
        message['From'] = sender_email_address
        message['To'] = receiver_email_address
        body = MIMEText(msg_body, 'html')
        message.attach(body)
          
        server = smtplib.SMTP(email_smtp, '587')
        server.ehlo()
        server.starttls()
        server.login(sender_email_address, email_password)
        server.sendmail(sender_email_address, receiver_email_address, message.as_string())
        server.quit()

