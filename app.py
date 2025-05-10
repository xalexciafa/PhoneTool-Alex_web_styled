from flask import Flask, request, render_template, send_file, session
import pandas as pd
import os
import re
from io import BytesIO
from zipfile import ZipFile

app = Flask(__name__)
app.secret_key = 'supersegretokey'

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

def rimuovi_spazi(valore):
    if isinstance(valore, str):
        return valore.replace(" ", "")
    return valore

def correggi_numero(numero):
    if not isinstance(numero, str):
        return numero, None

    originale = numero
    numero = rimuovi_spazi(numero)

    if len(numero) < 9:
        return None, f"Numero troppo corto: {originale}"

    if numero.startswith('+39') and len(numero) == 13:
        numero = numero[3:]

    if len(numero) > 10:
        return numero, f"Lunghezza superiore a 10 caratteri: {originale}"

    if len(numero) == 9:
        prefisso = numero[:3]
        if prefisso not in PREFISSI_VALIDI:
            return numero, f"Prefisso non valido: {prefisso}"
        return numero, None

    if not numero.startswith(('3', '0')):
        numero = '0' + numero

    return numero, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return "Nessun file caricato."

        df = pd.read_excel(file)
        session['data'] = df.to_json()
        session['filename'] = file.filename
        return render_template('colonne.html', colonne=list(df.columns), anteprima=df.head())

    return render_template('index.html')

@app.route('/correggi', methods=['POST'])
def correggi():
    colonna = request.form.get('colonna')
    if not colonna:
        return "Nessuna colonna selezionata."

    df = pd.read_json(session['data'])
    filename = session.get('filename', 'file.xlsx')

    for col in df.columns:
        df[col] = df[col].apply(rimuovi_caratteri_speciali)

    anomalie, correzioni, non_validi = [], [], []

    for idx, valore in df[colonna].items():
        originale = valore
        valore, anomalia = correggi_numero(valore)
        if valore is None:
            non_validi.append(df.loc[idx].to_dict())
            df.drop(index=idx, inplace=True)
        else:
            df.at[idx, colonna] = valore
            if anomalia:
                anomalie.append({'Riga': idx + 2, 'Valore Originale': originale, 'Anomalia': anomalia})
            elif originale != valore:
                correzioni.append({'Riga': idx + 2, 'Valore Originale': originale, 'Valore Corretto': valore})

    memory_file = BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        with BytesIO() as b:
            df.to_excel(b, index=False)
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

        with BytesIO() as b:
            with pd.ExcelWriter(b, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="Corretto", index=False)
                if anomalie:
                    pd.DataFrame(anomalie).to_excel(writer, sheet_name="Anomalie", index=False)
                if correzioni:
                    pd.DataFrame(correzioni).to_excel(writer, sheet_name="Correzioni", index=False)
                if non_validi:
                    pd.DataFrame(non_validi).to_excel(writer, sheet_name="Non Validi", index=False)
            zf.writestr('report_completo.xlsx', b.getvalue())

    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name="risultati_correzione.zip")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)