import requests
import json

from flask import Flask, request, render_template

# импортирую API_KEY из другого файла
from api_key import API_KEY


# запускаю фласк приложение
app = Flask(__name__)


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
    
    except Exception as e:
        print('get_location_city_key', e)
        return None


# получает температуру, влажность и скорость ветра
def get_temp_humidity_wind_speed(location_key: str) -> dict:
    try:
        req = requests.get(
            f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}',
            params={'apikey': API_KEY, 'details': True}
            )

        weather_data = req.json()
        
        temp = weather_data[0]['Temperature']['Metric']['Value']
        humidity = weather_data[0]['RelativeHumidity']
        wind_speed = weather_data[0]['Wind']['Speed']['Metric']['Value']
        
        return {'Temperature': temp, 'Humidity': humidity, 'WindSpeed': wind_speed}
    
    except Exception as e:
        print('get_temp_humidity_wind_speed', e)
        return {'Temperature': -1, 'Humidity': -1, 'WindSpeed': -1}


# получает вероятность дождя
def get_rain_prob(location_key: str) -> dict:
    try:
        req = requests.get(
            f'http://dataservice.accuweather.com/forecasts/v1/hourly/1hour/{location_key}',
            params={'apikey': API_KEY, 'details': True}
        )

        rain_prob = req.json()[0]['RainProbability']

        return {'RainProbability': rain_prob}
    
    except Exception as e:
        print('get_rain_prob', e)
        return {'RainProbability': -1}



# проверяет погоду на пригодность для поездки
def check_weather(temp: int, wind_speed: int, rain_prob: int):
    try:
        if -10 <= temp <= 20 and 0 <= wind_speed <= 20 and 0 <= rain_prob <= 20:
            return 'Погода блеск, катись куда хочешь!'
        
        else:
            return 'Тебе следует остаться дома'
    except Exception as e:
        print('check_weather', e)
        return 'Что-то пошло не так, попробуйте снова'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('ways.html')
    
    else:
        try:
            way = request.form['way']
            status = 1
        except KeyError:
            status = 0
        
        if status == 1:
            if way == 'По ширине и долготе':
                return render_template('lat_lon.html')
            
            elif way == 'По городу':
                return render_template('cities.html')
        
        if status == 0:
            try:
                lat_dep = request.form['lat_dep']
                lon_dep = request.form['lon_dep']
                lat_arr = request.form['lat_arr']
                lon_arr = request.form['lon_arr']
                status = 1
            except KeyError:
                status = 0

            
            if status == 1:
                location_key_dep = get_location_key(lat_dep, lon_dep)
                location_key_arr = get_location_key(lat_arr, lon_arr)

                if location_key_dep is None or location_key_arr is None:
                    return render_template('lat_lon.html')
            else:
                city_dep = request.form['city_dep']
                city_arr = request.form['city_arr']
                location_key_dep = get_location_city_key(city_dep)
                location_key_arr = get_location_city_key(city_arr)

                if location_key_dep is None or location_key_arr is None:
                    return render_template('cities.html')


            data_dep = get_temp_humidity_wind_speed(location_key_dep) | get_rain_prob(location_key_dep)
            data_arr = get_temp_humidity_wind_speed(location_key_arr) | get_rain_prob(location_key_arr)

            text_dep = check_weather(data_dep['Temperature'], data_dep['WindSpeed'], data_dep['RainProbability'])
            text_arr = check_weather(data_arr['Temperature'], data_arr['WindSpeed'], data_arr['RainProbability'])

            if text_dep == text_arr == 'Погода блеск, катись куда хочешь!':
                return render_template('out.html', text='Погода блеск, катись куда хочешь!')
            else:
                return render_template('out.html', text='Тебе следует остаться дома')


# запуск программы
if __name__ == '__main__':
    app.run(debug=True)

