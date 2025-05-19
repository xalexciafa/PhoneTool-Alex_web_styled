
from flask import Flask, render_template, request, redirect, send_file, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
import zipfile

os.makedirs('input', exist_ok=True)
os.makedirs('output', exist_ok=True)
os.makedirs('logs', exist_ok=True)

app = Flask(__name__)

UPLOAD_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
LOG_FOLDER = 'logs'
ZIP_PATH = 'zipped_results.zip'
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

VALID_PREFIXES = {
    '330','331','333','334','335','336','337','338','339','360','363','366','368','340','342','343','344','345','346','347','348','349','376',
    '320','322','323','324','327','328','329','380','383','388','389','390','391','392','393','397'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df = pd.read_excel(filepath)
        columns = df.columns.tolist()

        return render_template('column_select.html', columns=columns, filename=filename)
    return 'Invalid file format'

@app.route('/process', methods=['POST'])
def process():
    selected_column = request.form['column']
    filename = request.form['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_excel(filepath)

    corrected = []
    duplicati = []
    anomalie = []
    non_validi = []
    eccezioni = []
    report = []
    seen = set()
    valid_rows = []

    for index, row in df.iterrows():
        original = str(row[selected_column])
        cleaned = original
        note = []

        if pd.isna(cleaned):
            continue

        # Se inizia per 800 → numero verde
        if cleaned.startswith('800'):
            eccezioni.append((index + 2, original))
            report.append((index + 2, original, original, 'Numero verde (non modificato)'))
            continue

        # Pulizia base
        cleaned = ''.join(filter(str.isdigit, cleaned)) if not cleaned.startswith('+') else '+' + ''.join(filter(str.isdigit, cleaned))

        if ' ' in original:
            note.append('Rimosso spazio')
        if '#' in original:
            note.append('Rimosso carattere speciale')

        if cleaned.startswith('+39') and len(cleaned) == 13:
            cleaned = cleaned[3:]
            note.append('Rimosso prefisso +39')
        elif cleaned.startswith('393') and len(cleaned) == 12:
            cleaned = cleaned[2:]
            note.append('Rimosso prefisso 39 da 393')

        if not cleaned.startswith(('3', '0')):
            cleaned = '0' + cleaned
            note.append('Aggiunto zero iniziale')

        # Duplicati
        if cleaned in seen:
            duplicati.append((index + 2, cleaned))
            continue
        seen.add(cleaned)

        # Verifica validità
        is_valid = True
        if not cleaned.isdigit():
            is_valid = False
            non_validi.append((index + 2, cleaned))
        elif len(cleaned) > 10:
            is_valid = False
            anomalie.append((index + 2, cleaned))
        elif len(cleaned) < 9:
            is_valid = False
            non_validi.append((index + 2, cleaned))
        elif len(cleaned) == 9 and cleaned[:3] not in VALID_PREFIXES:
            is_valid = False
            non_validi.append((index + 2, cleaned))

        if is_valid:
            row[selected_column] = cleaned
            valid_rows.append(row)
            if note:
                corrected.append((index + 2, original, cleaned, ', '.join(note)))

        report.append((index + 2, original, cleaned, ', '.join(note)))

    # Salvataggi finali
    df.to_excel(os.path.join(OUTPUT_FOLDER, 'corretto.xlsx'), index=False)
    pd.DataFrame(corrected, columns=['Riga', 'Originale', 'Corretto', 'Note']).to_excel(os.path.join(LOG_FOLDER, 'correzioni.xlsx'), index=False)
    pd.DataFrame(duplicati, columns=['Riga', 'Duplicato']).to_excel(os.path.join(LOG_FOLDER, 'duplicati.xlsx'), index=False)
    pd.DataFrame(anomalie, columns=['Riga', 'Anomalia']).to_excel(os.path.join(LOG_FOLDER, 'anomalie.xlsx'), index=False)
    pd.DataFrame(non_validi, columns=['Riga', 'Non valido']).to_excel(os.path.join(LOG_FOLDER, 'non_validi.xlsx'), index=False)
    pd.DataFrame(eccezioni, columns=['Riga', 'Numero verde']).to_excel(os.path.join(LOG_FOLDER, 'eccezioni.xlsx'), index=False)
    pd.DataFrame(report, columns=['Riga', 'Originale', 'Finale', 'Note']).to_excel(os.path.join(LOG_FOLDER, 'report_completo.xlsx'), index=False)

    definitivo_df = pd.DataFrame(valid_rows)
    definitivo_df.to_excel(os.path.join(OUTPUT_FOLDER, 'definitivo.xlsx'), index=False)

    with zipfile.ZipFile(ZIP_PATH, 'w') as zipf:
        for folder in [OUTPUT_FOLDER, LOG_FOLDER]:
            for file in os.listdir(folder):
                zipf.write(os.path.join(folder, file), arcname=os.path.join(folder, file))

    return send_file(ZIP_PATH, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
