from flask import Flask, request, render_template, send_file, session, flash, redirect, url_for
import pandas as pd
import os
import re
from io import BytesIO
from zipfile import ZipFile

app = Flask(__name__)
app.secret_key = 'alex-super-secret'

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
    numero = str(numero).strip().replace(" ", "")
    if numero.startswith('+39') and len(numero) == 13:
        numero = numero[3:]
    elif numero.startswith('39') and len(numero) == 12:
        numero = numero[2:]
    numero = numero.replace(',', '').split('E')[0]
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
        file = request.files.get('file')
        if not file:
            flash("Nessun file caricato.")
            return render_template('index.html')
        df = pd.read_excel(file)
        session['data'] = df.to_json()
        session['filename'] = file.filename
        return render_template('colonne.html', colonne=list(df.columns), anteprima=df.head())
    return render_template('index.html')

@app.route('/correggi', methods=['POST'])
def correggi():
    colonna = request.form.get('colonna')
    if 'data' not in session:
        flash("Errore: file non caricato o sessione scaduta.")
        return redirect(url_for('index'))
    df = pd.read_json(session['data'])
    filename = session.get('filename', 'file.xlsx')

    for col in df.columns:
        df[col] = df[col].apply(rimuovi_caratteri_speciali)

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

    df_corretto = pd.DataFrame(righe_valide)

    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        with BytesIO() as b:
            df_corretto.to_excel(b, index=False)
            zf.writestr('corretto.xlsx', b.getvalue())
        if anomalie:
            with BytesIO() as b:
                pd.DataFrame(anomalie).to_excel(b, index=False)
                zf.writestr('anomalie.xlsx', b.getvalue())
        if correzioni:
            with BytesIO() as b:
                pd.DataFrame(correzioni).to_excel(b, index=False)
                zf.writestr('correzioni.xlsx', b.getvalue())
        if non_validi:
            with BytesIO() as b:
                pd.DataFrame(non_validi).to_excel(b, index=False)
                zf.writestr('non_validi.xlsx', b.getvalue())
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name="risultati_correzione.zip")

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)