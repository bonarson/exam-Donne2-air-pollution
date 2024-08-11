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

        # Extraire et normaliser les données
        components = data['list'][0]['components']
        normalized_components = normalize_data(components)

        # Créer le dictionnaire de sortie avec les colonnes souhaitées
        output_data = {
            'Country': 'FR',  # Exemple statique pour le pays
            'City': 'Paris',  # Exemple statique pour la ville
            'AQI Value': data['list'][0].get('main', {}).get('aqi', 'N/A'),
            'AQI Category': 'N/A',  # Peut être calculé selon la valeur de AQI
            'CO AQI Value': normalized_components.get('co', 'N/A'),
            'CO AQI Category': categorize_aqi(normalized_components.get('co', 0)),
            'Ozone AQI Value': normalized_components.get('o3', 'N/A'),
            'Ozone AQI Category': categorize_aqi(normalized_components.get('o3', 0)),
            'NO2 AQI Value': normalized_components.get('no2', 'N/A'),
            'NO2 AQI Category': categorize_aqi(normalized_components.get('no2', 0)),
            'PM2.5 AQI Value': normalized_components.get('pm2_5', 'N/A'),
            'PM2.5 AQI Category': categorize_aqi(normalized_components.get('pm2_5', 0)),
            'PM10 AQI Value': normalized_components.get('pm10', 'N/A'),
            'PM10 AQI Category': categorize_aqi(normalized_components.get('pm10', 0)),
            'newCountry': 'France'  # Exemple statique pour le nouveau pays
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

        # Ajouter les nouvelles données au fichier
        existing_data.append(output_data)

        # Écrire à nouveau dans le fichier
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

    return output_data

# Fonction de normalisation (Min-Max scaling)
def normalize_data(components):
    # Définir les valeurs min et max pour chaque composant
    min_values = {'co': 0, 'no': 0, 'no2': 0, 'o3': 0, 'so2': 0, 'pm2_5': 0, 'pm10': 0, 'nh3': 0}
    max_values = {'co': 1000, 'no': 100, 'no2': 100, 'o3': 300, 'so2': 100, 'pm2_5': 500, 'pm10': 500, 'nh3': 100}

    normalized_components = {}
    for key, value in components.items():
        min_val = min_values.get(key, 0)
        max_val = max_values.get(key, 1)
        normalized_value = (value - min_val) / (max_val - min_val) if max_val != min_val else 0
        normalized_components[key] = normalized_value

    return normalized_components

# Fonction pour catégoriser l'AQI
def categorize_aqi(value):
    if value < 0.2:
        return 'Good'
    elif value < 0.4:
        return 'Moderate'
    elif value < 0.6:
        return 'Unhealthy for Sensitive Groups'
    elif value < 0.8:
        return 'Unhealthy'
    else:
        return 'Very Unhealthy'

# Définir la tâche dans le DAG
fetch_task = PythonOperator(
    task_id='fetch_air_pollution_task',
    python_callable=fetch_and_normalize_air_pollution_data,
    dag=dag,
)

fetch_task

