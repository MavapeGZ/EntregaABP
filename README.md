
# Proyecto ABP - Stinder 

Este proyecto contiene la aplicación **Stinder**, recomendador basado en contenidos desarrollado en Python Notebooks. 
El código en este repositorio ha sido desarrollado por el grupo _VideogamesRecommender_ compuesto por Raúl Blanco Garrido, Anxo Rodríguez Castro, Anxo Rodríguez Méndez y Mario Vázquez Pérez


## 📋 Contenidos

- Requisitos
- Instalación
- Configurar la aplicación
- Ejecutar la aplicación
- [Entrega 3](#entrega-3)
- [Entrega 4](#entrega-4)
- [Entrega 5](#entrega-5)


## ✅Requisitos

- **Python**: [Instalar Python](https://www.python.org/downloads/)
- **Visual Studio Code**: [Instalar VSCode](https://code.visualstudio.com/)
- **Streamlit**: [Documentación de Streamlit](https://streamlit.io/)

## 🚀 Instalación

Una vez satisfechos los requisitos, sigue los siguientes pasos:

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

### **Entrega 3**

#### **Instalación de liberías necesarias 📚**
- **Pandas** (para la manipulación de datos)
- **NLTK** (para procesamiento de texto)
- **Scikit-learn** (para modelado y cálculos de distancias)
- **FuzzyWuzzy** (para la coincidencia de cadenas)

```bash
   pip install pandas nltk scikit-learn fuzzywuzzy[speedup]
   ```

### **Entrega 4**

#### **Instalación de liberías necesarias 📚**
- **Pandas** (para la manipulación de datos)
- **NLTK** (para procesamiento de texto)
- **Scikit-learn** (para modelado y cálculos de distancias)
- **FuzzyWuzzy** (para la coincidencia de cadenas)
- **Streamlit** (para la interfaz gráfica)

```bash
   pip install pandas nltk scikit-learn fuzzywuzzy[speedup] streamlit
   ```

### **Entrega 5**

> **Entrega 5:** En el caso de querer utilizar la entrega 5 con el proyecto clonado desde github se deberá hacer primero.
 ```bash
   git checkout entrega5
   ```

#### **Instalación de liberías necesarias 📚**
- **Pandas** (para la manipulación de datos)
- **NLTK** (para procesamiento de texto)
- **Scikit-learn** (para modelado y cálculos de distancias)
- **FuzzyWuzzy** (para la coincidencia de cadenas)
- **Streamlit** (para la interfaz gráfica)
- **DeepL** (para la traducción de los textos)

```bash
   pip install pandas nltk scikit-learn fuzzywuzzy[speedup] streamlit deepl
   ```


## ▶️ Ejecutar la aplicación
### **Entrega 3**
Para la ejecución de la aplicación sólo necesitamos dos archivos: `tratamientoDatos.ipynb` y `stinder.ipynb`.

1. Se deberá ejecutar el archivo de tratamiento de datos (*desde la opción de Run All o Execute Cell*). Su ejecución generará el fichero `steam_data.csv`, que usaremos para realizar las recomendaciones de videojuegos.
2. Se deberá ejecutar el archivo stinder (*desde la opción de Run All o Execute Cell*) (en el caso de solicitar que escojamos kernel escogeremos el que hemos creado anteriormente)
3. Durante la ejecución de Stinder se nos pedirá que introduzcamos datos. La primera petición es el juego con el que queremos comparar. Para asegurarnos que existe el juego en nuestro dataset (o que puedes escoger específicamente el que quieres en el caso de varios similares), después de introducir el valor (*en el input de Visual Studio Code*) se mostrará un menú con los juegos encontrados en caso de haberlos.
4. Después de mostrar el menú se solicitará que se seleccione el juego que queremos (en el caso de que haya más de uno). Una vez hayamos seleccionado el juego se mostrarán las recomendaciones para él.

### **Entrega 4**
Para la ejecución de la aplicación sólo necesitamos dos archivos: `tratamientoDatos.ipynb` y `stinder.py`.

1. Se deberá ejecutar el archivo de tratamiento de datos (*desde la opción de Run All o Execute Cell*). Su ejecución generará el fichero `steam_data.csv`, que usaremos para realizar las recomendaciones de videojuegos.
2. En la consola de Visual Studio Code ejecutaremos el comando de debajo para que se nos habilite la interfaz gráfica.
```bash
   streamlit run stinder.py
   ```
3. Una vez tenemos habilitada la interfaz gráfica podemos pedir recomendaciones del modo "Individual" de la aplicación. Si escribimos un juego se nos habilitará un desplegable con los juegos a los que podríamos hacer referencia que están dentro de nuestro dataset. Una vez hayamos escogido el juego al que hacíamos referencia podremos seguir el proceso de like/dislike de Stinder.
4. Recibiremos 10 recomendaciones, a las que podemos darle like o dislike simplemente pulsando en el botón correspondiente (puede ser necesario pulsar varias veces para que cambie a la siguiente recomendación). 

### **Entrega 5**
Para la ejecución de la aplicación sólo necesitamos dos archivos: `tratamientoDatos.ipynb` y `stinder.py`. Necesitamos asegurarnos de que estamos en la rama correcta del proyecto 
```bash
   git checkout entrega5
   ```
1. Se deberá ejecutar el archivo de tratamiento de datos (*desde la opción de Run All o Execute Cell*). Su ejecución generará el fichero `steam_data.csv`, que usaremos para realizar las recomendaciones de videojuegos.
2. En la consola de Visual Studio Code ejecutaremos el comando de debajo para que se nos habilite la interfaz gráfica.
```bash
   streamlit run stinder.py
   ```
3. Una vez tenemos habilitada la interfaz gráfica podemos pedir recomendaciones introduciendo el nombre del videojuego y por una descripción. También tenemos la opción de introducirle nuestras propias bibliotecas de Steam en formato csv para que nos genere recomendaciones. En el caso de la recomendación por nombre, se nos habilitará un desplegable una vez escribamos para seleccionar que el recomendador haga recomendaciones para el juego que nosotros realmente queremos. Para la descripción es tan sencillo como escribir de qué queremos que sea el juego y recibiremos las pertinentes recomendaciones. Para las recomendaciones por biblioteca introduciremos un csv como el siguiente:

| Appid  | Hours played |
| ------ | ------------ |
| 14510  | 145  |
| 14542  | 30  |

El fichero `.csv` sólo deberá contener datos (_y no las cabceras appid y hours_played_)

4. En cualquier modo recibiriemos 10 recomendaciones, en las que nos dejará darle like, dislike o introducir nuestra opinión del juego. Estas acciones positivas o negativas sobre los juegos tendrán efecto immediato en los juegos recomendados.
> NORMA 1: Para el correcto funcionamiento del recomendador animamos a seguir las siguientes normas: No escribir en el input de nombre y descripción a la vez (ya que priorizará las recomendaciones por nombre).

> NORMA 2: Se recomienda el uso de bibliotecas de más de 10 juegos válidos cada una (se necesitarán entre 2 y 5 bibliotecas para generar recomendaciones), por lo que se le puede pedir a CHATGPT que genere un fichero csv con los campos que pedimos (siendo el appid un numero entre el 10 y 1069460) (también se pueden buscar a mano los appids en el dataset que generemos, siendo esta la opción recomendada)
