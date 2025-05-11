from flask import Flask, render_template, request, redirect, send_file, session
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'alex_secret_key'
UPLOAD_FOLDER = 'input'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return 'Nessun file selezionato', 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            columns = df.columns.tolist()
            session['filepath'] = filepath
            return render_template('select_column.html', columns=columns)
        except Exception as e:
            return f'Errore nella lettura del file: {e}', 400

    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    column = request.form.get('column')
    filepath = session.get('filepath')
    if not column or not filepath:
        return 'Colonna o file non disponibile', 400

    return f'File ricevuto e colonna selezionata: {column}'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)