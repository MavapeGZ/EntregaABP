
# Proyecto ABP - Stinder 

Este proyecto contiene la aplicación **Stinder**, recomendador basado en contenidos desarrollado en Python Notebooks.

## 📋 Contenidos

- [Requisitos](##requisitos)
- [Instalación](##instalación)
- [Configurar la aplicación](##configurar-la-aplicacion)
- [Ejecutar la aplicación](##ejecutar-la-aplicación)

## ✅ Requisitos
- **Python**: [Instalar Python](https://www.python.org/downloads/)
- **Visual Studio Code**: [Instalar VSCode](https://code.visualstudio.com/)

## 🚀 Instalación

**Clona este repositorio** en tu máquina local:

   ```bash
   git clone https://github.com/MavapeGZ/EntregaABP.git
   ```

## ⚙️ Configurar la aplicación
Abriremos el proyecto usando Visual Studio Code. Seleccionaremos el archivo `tratamientoDatos.ipynb`.

### **Extensiones de Visual Studio Code 🔌**
Se necesitarán las siguientes extensiones: 
- **Python** (paquete con Pylance y Python Debugger)
- **Jupyter** (paquete con Jupyter Keymap, Jupyter Notebook Renderers, Jupyter Slide Show, Jupyter Cell Tags)

### **Entorno virtual de Python 🐍**
En la parte superior derecha del archivo `.ipynb` tendremos que seleccionar el kernel para correr nuestro proyecto. Por defecto aparecerá la versión de Python que tengamos instalada en nuestro ordenador (nuestro caso: `Python 3.13.0`). Seguiremos los siguientes pasos: 
  1. Hacer click en nuestra versión de Python.
  2. Opción "Seleccionar otro kernel"
  3. Opción "Python Enviroments"
  4. Opción "Create Python Enviroment"
  5. Seleccionamos como base la versión de Python que ya tenemos instalada.
  6. Esperamos a que se cree el directorio `.venv`
  7. Activamos el entorno virtual ejecutando el comando `./.venv/Scripts/activate` 

### **Instalación de liberías necesarias 📚**
- **Pandas** (para la manipulación de datos)
- **NLTK** (para procesamiento de texto)
- **Scikit-learn** (para modelado y cálculos de distancias)
- **FuzzyWuzzy** (para la coincidencia de cadenas)

```bash
   pip install pandas nltk scikit-learn fuzzywuzzy[speedup]
   ```

## ▶️ Ejecutar la aplicación
Para la ejecución de la aplicación sólo necesitamos dos archivos: `tratamientoDatos.ipynb` y `stinder.ipynb`.

1. Se deberá ejecutar el archivo de tratamiento de datos (*desde la opción de Run All o Execute Cell*). Su ejecución generará el fichero `steam_data.csv`, que usaremos para realizar las recomendaciones de videojuegos.
2. Se deberá ejecutar la primera celda de código del archivo stinder (*desde la opción de Execute Cell*) (en el caso de solicitar que escojamos kernel escogeremos el que hemos creado anteriormente)
3. Ahora abriremos la terminal y nos aseguraremos de que el entorno virtual esté activado (*./.venv/Scripts/activate*)
4. La primera celda habrá creado un fichero app.py, la cual ejecutaremos abriendo una terminal con el comando `streamlit run app.py` (es necesario situarse en el directorio en que se encuentra el fichero app.py)
5. Esto abrirá una pestaña en nuestro navegador predeterminado en la cual continuará la ejecución del programa.
6. Durante la ejecución de Stinder se nos pedirá que introduzcamos datos. La primera petición es el juego con el que queremos comparar. Para asegurarnos que existe el juego en nuestro dataset (o que puedes escoger específicamente el que quieres en el caso de varios similares), después de introducir el valor (*en el input de Visual Studio Code*) se mostrará un menú con los juegos encontrados en caso de haberlos.
7. Después de mostrar el menú se solicitará que se seleccione el juego que queremos (en el caso de que haya más de uno). Una vez hayamos seleccionado el juego se mostrarán las recomendaciones para él.

