from airflow import DAG
from airflow.operators.python import PythonOperator
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
    description='DAG to fetch and normalize air pollution data from OpenWeatherMap API including AQI category',
    schedule_interval='*/5 * * * *',
)

# Liste des villes avec leurs coordonnées (latitude, longitude)
cities = {
    'Los Angeles': ('34.0522', '-118.2437'),
    'Paris': ('48.8566', '2.3522'),
    'Tokyo': ('35.6828', '139.7594'),
    'Antananarivo': ('-18.8792', '47.5079'),
    'Nairobi': ('-1.2864', '36.8172'),
    'Lima': ('-12.0464', '-77.0428')
}

# Fonction pour appeler l'API et traiter les données
def fetch_and_normalize_air_pollution_data():
    api_key = '64c3b81d0e042e9ee938730c409c956d'
    all_data = []

    for city, (latitude, longitude) in cities.items():
        url = f'http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}'

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Normalisation des composants de la pollution
            components = data['list'][0]['components']
            normalized_components = normalize_data(components)

            # Ajout de la catégorie AQI
            aqi_category = data['list'][0]['main']['aqi']

            # Remplacer les composants d'origine par les valeurs normalisées
            data['list'][0]['components'] = normalized_components
            data['list'][0]['main']['aqi'] = aqi_category

            # Ajouter la ville aux données
            data['city'] = city

            # Ajouter les nouvelles données normalisées à la liste
            all_data.append(data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {city}: {e}")

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

    # Ajouter les nouvelles données normalisées à la liste
    existing_data.extend(all_data)

    # Écrire à nouveau dans le fichier
    with open(file_path, 'w') as f:
        json.dump(existing_data, f, indent=4)

    return all_data

# Fonction de normalisation (Min-Max scaling)
def normalize_data(components):
    min_values = {'co': 0, 'no': 0, 'no2': 0, 'o3': 0, 'so2': 0, 'pm2_5': 0, 'pm10': 0, 'nh3': 0, 'aqi': 0}
    max_values = {'co': 1000, 'no': 100, 'no2': 100, 'o3': 300, 'so2': 100, 'pm2_5': 500, 'pm10': 500, 'nh3': 100, 'aqi': 500}

    normalized_components = {}
    for key, value in components.items():
        min_val = min_values.get(key, 0)
        max_val = max_values.get(key, 1)
        normalized_value = (value - min_val) / (max_val - min_val) if max_val != min_val else 0
        normalized_components[key] = normalized_value

    return normalized_components

# Définir la tâche dans le DAG
fetch_task = PythonOperator(
    task_id='fetch_air_pollution_task',
    python_callable=fetch_and_normalize_air_pollution_data,
    dag=dag,
)
