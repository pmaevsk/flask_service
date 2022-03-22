from dataclasses import replace
from collections import OrderedDict
import json
import os
import sqlite3

from bs4 import BeautifulSoup as bs
from flask import Flask, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from oauthlib.oauth2 import WebApplicationClient
import requests

from db import init_db_command
from user import User

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)

try:
    init_db_command()
except sqlite3.OperationalError: 
    pass # Assume it's already been created

client = WebApplicationClient(GOOGLE_CLIENT_ID)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/")
def index():
        return (
            '<a class="button" href="/login">Google Login</a>''<br>'
            '<a class="button" href="/about">About</a>''<br>'
            '<a class="button" href="/list/city">Weather on the weekend</a>''<br>'
            '<a class="button" href="/city/date">Weather on this day</a>''<br>'
            '<a class="button" href="/useragent">User-agent</a>''<br>'
            '<a class="button" href="/logout">Logout</a>'
        )

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    login_user(user)

    return redirect(url_for("index"))

@app.route("/about")
def about():
    if current_user.is_authenticated:
        return (
            '<p>Logged in</p>'
            '<p>Your name: {}</p>'
            '<p>Your email: {}</p>'
            "<div><p>Your Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'

@app.route("/list/city")
def get_city():
    return render_template('city_form.html')
@app.route("/list/city", methods=['POST'])
def weekweather():
    text = request.form['text']
    city = text.lower()
    # r = requests.get('https://www.yandex.com/weather/segment/details?offset=0&lat=53.902496&lon=27.561481&limit=10', headers = {'User-Agent':'Mozilla/5.0'})
    r = requests.get('https://www.yandex.com/weather/{}/segment/details?limit=10'.format(city), headers = {'User-Agent':'Mozilla/5.0'})
    soup = bs(r.content, 'lxml')
    res_dict = OrderedDict()
    dates = list()
    temps = list()
    conditions = list()
    sep_temp = list()
    res_list = list()
    # <span class="temp__pre">day</span><span class="temp__value temp__value_with-unit">+13</span>
    # <time class="time forecast-briefly__date" datetime="2022-03-21 00:00+0300">21 Mar</time>
    for cond in soup.find_all('div',{'class':'forecast-briefly__condition'}):
        conditions.append(cond.get_text())
    for val in soup.find_all('time',{'class':'time forecast-briefly__date'}):
        dates.append(val.get_text())
    tags = soup.find_all('div',{'class':'temp forecast-briefly__temp forecast-briefly__temp_day'})
    for val in tags:
        sep_temp.append(val.find('span', {'class':'temp__value temp__value_with-unit'}))
    for temp in sep_temp:   
        temps.append(temp.text.replace('\u2212','-'))
    for i in range(1,8):
        res_dict[dates[i]] = str(temps[i]) + "C " + str(conditions[i])
    for key, value in res_dict.items():
        res_list.append(key + " " + value)
    return '<p>Weather in {} for week: </p><p>{}</p>'.format(city, str(res_list))
    
@app.route("/city/date")
def get_city_date():
    return render_template('date_form.html')
@app.route("/city/date", methods=['POST'])
def dateweather():
    city_r = request.form['city']
    city = city_r.lower()
    date_r = request.form['date']
    date = date_r
    # r = requests.get('https://www.yandex.com/weather/segment/details?offset=0&lat=53.902496&lon=27.561481&limit=10', headers = {'User-Agent':'Mozilla/5.0'})
    r = requests.get('https://www.yandex.com/weather/{}/segment/details?limit=10'.format(city), headers = {'User-Agent':'Mozilla/5.0'})
    soup = bs(r.content, 'lxml')
    res_dict = OrderedDict()
    dates = list()
    temps = list()
    conditions = list()
    sep_temp = list()
    for cond in soup.find_all('div',{'class':'forecast-briefly__condition'}):
        conditions.append(cond.get_text())
    for val in soup.find_all('time',{'class':'time forecast-briefly__date'}):
        dates.append(val.get_text())
    tags = soup.find_all('div',{'class':'temp forecast-briefly__temp forecast-briefly__temp_day'})
    for val in tags:
        sep_temp.append(val.find('span', {'class':'temp__value temp__value_with-unit'}))
    for temp in sep_temp:   
        temps.append(temp.text.replace('\u2212','-'))
    for i in range(1,8):
        res_dict[dates[i]] = str(temps[i]) + "C " + str(conditions[i])
    return '<p>Weather in {} on the {}: {}</p>'.format(city, date, res_dict[date])
@app.route("/useragent")
def useragent():
    ua = request.user_agent
    return '<p>You are using {} operation system, and accessing this app with {} browser.</p>'.format(ua.platform, ua.browser)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(ssl_context="adhoc", debug=True)