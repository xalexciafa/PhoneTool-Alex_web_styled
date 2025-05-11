from flask import Flask, request, render_template, send_from_directory, redirect, url_for, session, flash
import pandas as pd
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key'
UPLOAD_FOLDER = "files"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PREFISSI_VALIDI = {
    '330', '331', '333', '334', '335', '336', '337', '338', '339',
    '360', '363', '366', '368', '340', '342', '343', '344', '345',
    '346', '347', '348', '349', '376', '320', '322', '323', '324',
    '327', '328', '329', '380', '383', '388', '389', '390', '391',
    '392', '393', '397'
}

def rimuovi_caratteri_speciali(valore):
    if isinstance(valore, str):
        return re.sub(r'[^a-zA-Z0-9\s]', '', valore)
    return valore

def correggi_numero(numero):
    if pd.isnull(numero):
        return None, "Valore nullo"
    numero = str(numero).strip().replace(" ", "").replace(",", "")
    if "E+" in numero.upper():
        try:
            numero = str(int(float(numero)))
        except:
            return None, "Formato scientifico non convertibile"
    if numero.startswith('+39') and len(numero) == 13:
        numero = numero[3:]
    elif numero.startswith('39') and len(numero) == 12:
        numero = numero[2:]
    if not numero.isdigit():
        return None, f"Contiene caratteri non numerici: {numero}"
    if len(numero) < 9:
        return None, f"Numero troppo corto: {numero}"
    if len(numero) > 10:
        return numero, f"Lunghezza superiore a 10 caratteri: {numero}"
    if len(numero) == 9 and numero[:3] not in PREFISSI_VALIDI:
        return numero, f"Prefisso non valido: {numero[:3]}"
    if not numero.startswith(('3', '0')):
        numero = '0' + numero
    return numero, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash("Nessun file caricato.")
            return render_template('index.html')
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        df = pd.read_excel(filepath)
        session['filepath'] = filepath
        return render_template('colonne.html', colonne=list(df.columns), anteprima=df.head())
    return render_template('index.html')

@app.route('/correggi', methods=['POST'])
def correggi():
    colonna = request.form.get('colonna')
    filepath = session.get('filepath')
    if not filepath or not os.path.exists(filepath):
        flash("File non trovato o sessione scaduta.")
        return redirect(url_for('index'))

    df = pd.read_excel(filepath)
    df[colonna] = df[colonna].apply(rimuovi_caratteri_speciali)

    # Salva duplicati
    duplicati = df[df.duplicated(subset=[colonna], keep=False)]
    if not duplicati.empty:
        duplicati.to_excel(os.path.join(UPLOAD_FOLDER, 'duplicati.xlsx'), index=False)
        df = df.drop_duplicates(subset=[colonna])

    anomalie, correzioni, non_validi, righe_valide = [], [], [], []

    for idx, valore in df[colonna].items():
        originale = valore
        valore, anomalia = correggi_numero(valore)
        if valore is None:
            non_validi.append(df.loc[idx].to_dict())
            continue
        riga = df.loc[idx].copy()
        riga[colonna] = valore
        righe_valide.append(riga)
        if anomalia:
            anomalie.append({'Riga': idx + 2, 'Valore Originale': originale, 'Anomalia': anomalia})
        elif originale != valore:
            correzioni.append({'Riga': idx + 2, 'Valore Originale': originale, 'Valore Corretto': valore})

    pd.DataFrame(righe_valide).to_excel(os.path.join(UPLOAD_FOLDER, 'corretto.xlsx'), index=False)
    if correzioni:
        pd.DataFrame(correzioni).to_excel(os.path.join(UPLOAD_FOLDER, 'correzioni.xlsx'), index=False)
    if anomalie:
        pd.DataFrame(anomalie).to_excel(os.path.join(UPLOAD_FOLDER, 'anomalie.xlsx'), index=False)
    if non_validi:
        pd.DataFrame(non_validi).to_excel(os.path.join(UPLOAD_FOLDER, 'non_validi.xlsx'), index=False)

    return render_template(
        'final.html',
        corretto=True,
        correzioni=bool(correzioni),
        anomalie=bool(anomalie),
        non_validi=bool(non_validi),
        duplicati=not duplicati.empty
    )

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)