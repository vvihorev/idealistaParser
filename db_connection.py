import os
import json
import datetime
import sqlite3
import smtplib

import dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


dotenv.load_dotenv()


def get_entries(filepath: str):
    """Gets flats data from an 'idealista api query results' file"""
    with open(filepath, "r") as file:
        data = json.loads(file.read())
    data = json.loads(data)
    elems = data['elementList']
    fields = ['address', 'numPhotos', 'price', 'priceByArea', 'rooms', 'thumbnail', 'url']
    entries = []
    for elem in elems:
        elem_fields = [elem[field] for field in fields]
        elem_fields.append(str(datetime.datetime.now()))
        entries.append(tuple(elem_fields))
    return entries


def fill_entries(files: list):
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
    for file in files:
        entries = get_entries(file)
        cur.execute( f"""
            insert or replace into houses
            values {','.join([str(entry) for entry in entries])};
        """)
    cur.close()
    conn.commit()
    conn.close()


def get_files(folder='data/') -> list:
    """Lists all files in the gived directory"""
    return [folder + x for x in os.listdir(folder)]


def get_views():
    conn = sqlite3.connect('db.sqlite')
    cur = conn.cursor()

    cur.execute('select * from for_two')
    for_two = cur.fetchall()
    cur.execute('select * from for_three')
    for_three = cur.fetchall()

    def print_flats(flats, for_who='two'):
        msg_body = f"<h1>Flats for {for_who}</h1>"
        for flat in flats:
            msg_body += f"<p>Адрес: {flat[0]}, <b>Цена: {flat[1]}</b>, Комнат: {flat[2]}, Ссылка:{flat[3]}, "
            route_to_uni = "https://www.google.com/maps/dir/Via Festa del Perdono, 7/".replace(' ', '%20') + flat[0].replace(' ', '%20')
            msg_body += "<a href=" + route_to_uni + ">Дорога до уника</a></p>"
        return msg_body

    msg_body = "<html><head></head><body>"
    msg_body += print_flats(for_two, 'two')
    msg_body += print_flats(for_three, 'three')
    msg_body += "</body></html>"

    cur.close()
    conn.close()

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


if __name__ == "__main__":
    # fill_entries(get_files())
    get_views()
