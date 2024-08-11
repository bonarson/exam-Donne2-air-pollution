from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import requests
import json
import os

# Définir les paramètres du DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2022, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    'fetch_air_pollution_data',
    default_args=default_args,
    description='DAG to fetch and normalize air pollution data from OpenWeatherMap API',
    schedule_interval='*/5 * * * *', 
)

# Fonction pour appeler l'API et traiter les données
def fetch_and_normalize_air_pollution_data():
    api_key = '64c3b81d0e042e9ee938730c409c956d'
    latitude = '48.8566'
    longitude = '2.3522'
    url = f'http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}'

    try:
        response = requests.get(url)
        response.raise_for_status()  # Vérifie si l'API a renvoyé une erreur
        data = response.json()

        # Normalisation des composants de la pollution
        components = data['list'][0]['components']
        normalized_components = normalize_data(components)

        # Calcul des valeurs d'AQI pour chaque composant
        aqi_values = calculate_aqi_values(components)
        
        # Ajouter les informations supplémentaires
        city = 'Paris'
        country = 'FR'
        aqi_data = {
            'Country': country,
            'City': city,
            'AQI Value': sum(aqi_values.values()),
            'AQI Category': 'Good',  
            'CO AQI Value': aqi_values['co'],
            'CO AQI Category': 'Good', 
            'Ozone AQI Value': aqi_values['o3'],
            'Ozone AQI Category': 'Good',  
            'NO2 AQI Value': aqi_values['no2'],
            'NO2 AQI Category': 'Good',  
            'PM2.5 AQI Value': aqi_values['pm2_5'],
            'PM2.5 AQI Category': 'Good',  
            'newCountry': 'FR'
        }

        # Lire les données existantes dans le fichier
        file_path = '/home/ngourndii/airflow/air_pollution_data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        # Ajouter les nouvelles données à la liste
        existing_data.append(aqi_data)

        # Écrire à nouveau dans le fichier
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

    return data

# Fonction de normalisation (Min-Max scaling)
def normalize_data(components):
    min_values = {'co': 0, 'no': 0, 'no2': 0, 'o3': 0, 'so2': 0, 'pm2_5': 0, 'pm10': 0, 'nh3': 0}
    max_values = {'co': 1000, 'no': 100, 'no2': 100, 'o3': 300, 'so2': 100, 'pm2_5': 500, 'pm10': 500, 'nh3': 100}

    normalized_components = {}
    for key, value in components.items():
        min_val = min_values.get(key, 0)
        max_val = max_values.get(key, 1)
        normalized_value = (value - min_val) / (max_val - min_val) if max_val != min_val else 0
        normalized_components[key] = normalized_value

    return normalized_components

# Fonction pour calculer les valeurs d'AQI
def calculate_aqi_values(components):
    # Calculs d'AQI fictifs pour chaque composant
    # Les vraies méthodes de calcul d'AQI devraient être définies ici
    return {
        'co': components['co'],
        'o3': components['o3'],
        'no2': components['no2'],
        'pm2_5': components['pm2_5']
    }

# Définir la tâche dans le DAG
fetch_task = PythonOperator(
    task_id='fetch_air_pollution_task',
    python_callable=fetch_and_normalize_air_pollution_data,
    dag=dag,
)

fetch_task
