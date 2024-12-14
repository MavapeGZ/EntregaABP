import pandas as pd
import json

#Cargar el CSV original
input_file = "./data/processed_steam_data.csv"  # Cambia esto por la ruta de tu archivo
output_file = "./data/steam_data_v2.csv"

# Leer el archivo CSV
data = pd.read_csv(input_file)

# Extraer la primera captura de pantalla o poner null si no hay ninguna
def extract_first_screenshot(screenshots):
    try:
        screenshots_list = json.loads(screenshots.replace("'", '"'))  # Convertir a JSON válido
        if screenshots_list and isinstance(screenshots_list, list):
            return screenshots_list[0]['path_thumbnail']
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None

# Crear el nuevo DataFrame
processed_data = pd.DataFrame({
    'appid': data['appid'],
    'name': data['name'],
    'processed_text': data['processed_text'],
    'header_image': data['header_image'],
    'first_screenshot': data['screenshots'].apply(extract_first_screenshot)
})

# Guardar el nuevo DataFrame en un archivo CSV
processed_data.to_csv(output_file, index=False)

print(f"Archivo procesado guardado como {output_file}")
