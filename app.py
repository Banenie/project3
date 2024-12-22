import requests
import json

from flask import Flask, request, render_template

from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

import dash_bootstrap_components as dbc

import pandas as pd

import datetime


# импортирую API_KEY из другого файла
from api_key import API_KEY


# запускаю фласк приложение
flask_app = Flask(__name__)


# получает location_key для будущих запросов погоды
def get_location_key(lat: int, lon: int) -> str:
    try:
        req = requests.get(
            'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search',
            params={'apikey': API_KEY, 'q': f'{lat},{lon}'}
            )

        location_key = req.json()['Key']

        # сохраняет ключ, чтобы экономить запросы
        with open('location_keys.json', 'w+') as file:
            json.dump(location_key, file)
        
        return location_key
    
    except KeyError:
        print('Закончились бесплатные попытки')
        return None

    except Exception as e:
        print('get_location_key', e)
        return None


# получает location_key для будущих запросов погоды по городу
def get_location_city_key(city: str) -> str:
    try:
        print(city)
        req = requests.get(
            'http://dataservice.accuweather.com/locations/v1/cities/search',
            params={'apikey': API_KEY, 'q': f'{city}', 'language': 'ru'}
            )

        location_key = req.json()[0]['Key']

        # сохраняет ключ, чтобы экономить запросы
        with open('location_keys.json', 'w+') as file:
            json.dump(location_key, file)
        
        return location_key
    
    except KeyError:
        print('Закончились бесплатные попытки')
        return None
    
    except Exception as e:
        print('get_location_city_key', e)
        return None


# получает погодные данные
def get_5days_weather_data(location_key: str) -> dict:
    try:
        req = requests.get(
            f'http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}',
            params={'apikey': API_KEY, 'details': True, 'metric': True}
        )
        data = req.json()
        weather_data = []
        for day in range(5):
            temp = data['DailyForecasts'][day]['Temperature']['Maximum']['Value']
            humidity = data['DailyForecasts'][day]['Day']['RelativeHumidity']['Average']
            wind_speed = data['DailyForecasts'][day]['Day']['Wind']['Speed']['Value']
            rain_prob = data['DailyForecasts'][day]['Day']['RainProbability']


            weather_data.append({'Temperature': temp, 'WindSpeed': wind_speed, 'RainProbability': rain_prob, 'Humidity': humidity})

        return weather_data
    
    except Exception as e:
        print('get_5days_weather_data', e)
        return [{'Temperature': -1, 'WindSpeed': -1, 'RainProbability': -1, 'Humidity': -1,}] * 5


# проверяет погоду на пригодность для поездки
def check_weather(temp: int, wind_speed: int, rain_prob: int, a: int):
    try:
        if -10 <= int(temp) <= 20 and 0 <= int(wind_speed) <= 20 and 0 <= int(rain_prob) <= 20:
            return 'Погода блеск, катись куда хочешь!'
        
        else:
            return 'Тебе следует остаться дома'
    except Exception as e:
        print('check_weather', e)
        return 'Что-то пошло не так, попробуйте снова'


dash_app = Dash(server=flask_app, suppress_callback_exceptions=True, routes_pathname_prefix="/dash/", meta_tags=[{'charset': "UTF-8"}])
dash_app.title = '10'


dash_app.layout = html.Div([
    html.P(html.Label('Как вы хотите узнать погоду?')),
    dbc.Select(['По ширине и долготе', 'По городу'], id='way'),
    html.Button('Отправить', id='send')
], style={'text-align': 'center'}, id='forms')


@dash_app.callback(
    Output('forms', 'children', allow_duplicate=True),
    Input('send', 'n_clicks'),
    State('way', 'value'),
    State('forms', 'children'),
    prevent_initial_call=True
)
def cities_or_latlon(n_clicks, value, children):
    if not value:
        return children
    
    if value == 'По ширине и долготе':
        return [
            html.P(html.Label('Место отправления:')),
            html.Label('Широта:'),
            dbc.Input(type='text', id='lat_dep'),
            html.Br(),
            html.Br(),
            html.Label('Долгота:'),
            dbc.Input(type='text', id='lon_dep'),
            html.Br(),
            html.Br(),
            html.P(html.Label('Место  прибытия:')),
            html.Label('Широта:'),
            dbc.Input(type='text', id='lat_arr'),
            html.Br(),
            html.Br(),
            html.Label('Долгота:'),
            dbc.Input(type='text', id='lon_arr'),
            html.Br(),
            html.Br(),
            html.Br(),
            html.Label('Промежуточные точки в формате (ш, д),(ш, д)...  '),
            dbc.Input(type='text', id='latlons'),
            html.Br(),
            html.Br(),
            html.P([html.Label('Количество дней прогноза:  '), dbc.Select(['1', '3', '5'], id='way')]),
            html.Button('Отправить', id='send_places')
        ]
    
    else:
        return [
            html.P(html.Label('Город отправления:')),
            html.P(dbc.Input(type='text', id='city_dep')),
            html.P(html.Label('Город прибытия:')),
            html.P(dbc.Input(type='text', id='city_arr')),
            html.P(html.Label('Промежуточные города (через запятую):')),
            html.P(dbc.Input(type='text', id='cities')),
            html.P([html.Label('Количество дней прогноза:  '), dbc.Select(['1', '3', '5'], id='way')]),
            html.P(html.Button('Отправить', id='send_cities'))
        ]


@dash_app.callback(
    Output('forms', 'children', allow_duplicate=True),
    Input('send_cities', 'n_clicks'),
    State('city_dep', 'value'),
    State('city_arr', 'value'),
    State('cities', 'value'),
    State('way', 'value'),
    State('forms', 'children'),
    prevent_initial_call=True
)
def final_cities(n_clicks, city_dep, city_arr, cities, way, children):
    if not city_dep or not city_arr:
        return children
    
    if way is None:
        return children

    try:
        if cities is None:
            list_city = [city_dep, city_arr]
        else:
            list_city = [city_dep] + cities.split(',') + [city_arr]
    except AttributeError:
        return children
    
    try:
        location_keys = [get_location_city_key(city) for city in list_city]
    except Exception as e:
        print('location_city_keys', e)
        return children

    weather_data = [get_5days_weather_data(key) for key in location_keys]
    check_data = [check_weather(*j.values()) for i in weather_data for j in i]

    weather_data = [[{key: float(value) for key, value in j.items()} for j in i] for i in weather_data]

    today = datetime.datetime.now().date()
    df = pd.DataFrame({
        'City': list_city * int(way),
        'Day': [today + datetime.timedelta(i // len(list_city)) for i in range(len(list_city) * int(way))],
        'Temperature': [i[idx // len(list_city)]['Temperature'] for idx, i in enumerate(weather_data * int(way))],
        'WindSpeed': [i[idx // len(list_city)]['WindSpeed'] for idx, i in enumerate(weather_data * int(way))],
        'RainProbability': [i[idx // len(list_city)]['RainProbability'] for idx, i in enumerate(weather_data * int(way))],
        'Humidity': [i[idx // len(list_city)]['Humidity'] for idx, i in enumerate(weather_data * int(way))]
    })

    if all(i == 'Погода блеск, катись куда хочешь!' for i in check_data):
        return [
            html.H1('Программа оценила погоду, она считает что:'),
            html.P('Погода блеск, катись куда хочешь!'),
            html.Details([
                html.Summary('Температура'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Temperature', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Скорость ветра'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'WindSpeed', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Вероятность дождя'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'RainProbability', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Влажность'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Humidity', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.P(html.Button('Отправить', id='end', n_clicks=0))
        ]
    else:
        return [
            html.H1('Программа оценила погоду, она считает что:'),
            html.P('Тебе следует остаться дома'),
            html.Details([
                html.Summary('Температура'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Temperature', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Скорость ветра'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'WindSpeed', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Вероятность дождя'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'RainProbability', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Влажность'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Humidity', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.P(html.Button('Отправить', id='end', n_clicks=0))
        ]



@dash_app.callback(
    Output('forms', 'children', allow_duplicate=True),
    Input('send_places', 'n_clicks'),
    State('lat_dep', 'value'),
    State('lon_dep', 'value'),
    State('lat_arr', 'value'),
    State('lon_arr', 'value'),
    State('latlons', 'value'),
    State('way', 'value'),
    State('forms', 'children'),
    prevent_initial_call=True
)
def final_latlons(n_clicks, lat_dep, lon_dep, lat_arr, lon_arr, latlons, way, children):
    if any((not i) for i in [lat_dep, lon_dep, lat_arr, lon_arr]):
        return children
    
    if way is None:
        return children

    try:
        if latlons is None:
            list_coords = [(lat_dep, lon_dep), (lat_arr, lon_arr)]
        else:
            list_coords = [(lat_dep, lon_dep)] + list(eval(latlons)) + [(lat_arr, lon_arr)]
    except (TypeError, AttributeError):
        return children
    
    try:
        location_keys = [get_location_key(i[0], i[1]) for i in list_coords]
    except Exception as e:
        print('location_latlon_keys', e)
        return children

    weather_data = [get_5days_weather_data(key) for key in location_keys]
    check_data = [check_weather(*j.values()) for i in weather_data for j in i]

    weather_data = [[{key: float(value) for key, value in j.items()} for j in i] for i in weather_data]
    list_places = [f'Место {i}' for i in range(len(weather_data))]

    today = datetime.datetime.now().date()
    df = pd.DataFrame({
        'City': list_places * int(way),
        'Day': [today + datetime.timedelta(i // len(list_places)) for i in range(len(list_places) * int(way))],
        'Temperature': [i[idx // len(list_places)]['Temperature'] for idx, i in enumerate(weather_data * int(way))],
        'WindSpeed': [i[idx // len(list_places)]['WindSpeed'] for idx, i in enumerate(weather_data * int(way))],
        'RainProbability': [i[idx // len(list_places)]['RainProbability'] for idx, i in enumerate(weather_data * int(way))],
        'Humidity': [i[idx // len(list_places)]['Humidity'] for idx, i in enumerate(weather_data * int(way))]
    })

    if all(i == 'Погода блеск, катись куда хочешь!' for i in check_data):
        return [
            html.H1('Программа оценила погоду, она считает что:'),
            html.P('Погода блеск, катись куда хочешь!'),
            html.Details([
                html.Summary('Температура'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Temperature', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Скорость ветра'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'WindSpeed', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Вероятность дождя'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'RainProbability', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Влажность'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Humidity', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.P(html.Button('Отправить', id='end', n_clicks=0))
        ]
    else:
        return [
            html.H1('Программа оценила погоду, она считает что:'),
            html.P('Тебе следует остаться дома'),
            html.Details([
                html.Summary('Температура'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Temperature', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Скорость ветра'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'WindSpeed', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Вероятность дождя'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'RainProbability', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.Details([
                html.Summary('Влажность'),
                dcc.Graph('graph', figure=px.line(df, 'Day', 'Humidity', color='City').update_layout(xaxis={
                    'tickmode': 'array',
                    'tickvals': [today + datetime.timedelta(i) for i in range(int(way))],
                    'ticktext': [str(today + datetime.timedelta(i)) for i in range(int(way))]
                })),
            ]),
            html.P(html.Button('Отправить', id='end', n_clicks=0))
        ]

@dash_app.callback(
    Output('forms', 'children', allow_duplicate=True),
    Input('end', 'n_clicks'),
    State('forms', 'children'),
    prevent_initial_call=True
)
def restart(n_clicks, children):
    if n_clicks == 0:
        return children

    return [
    html.P(html.Label('Как вы хотите узнать погоду?')),
    dbc.Select(['По ширине и долготе', 'По городу'], id='way'),
    html.Button('Отправить', id='send')
]

# запуск программы
if __name__ == '__main__':
    dash_app.run(debug=True)
