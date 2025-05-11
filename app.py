from flask import Flask, render_template, request, send_file, redirect
import os
import pandas as pd
import zipfile

app = Flask(__name__)
UPLOAD_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
LOGS_FOLDER = 'logs'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, LOGS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

VALID_PREFIXES = {
    "330", "331", "333", "334", "335", "336", "337", "338", "339", "360", "363", "366", "368",
    "340", "342", "343", "344", "345", "346", "347", "348", "349", "376",
    "320", "322", "323", "324", "327", "328", "329", "380", "383", "388", "389",
    "390", "391", "392", "393", "397"
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return redirect('/')
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)
        column = request.form['column']

        corrections, duplicates, anomalies, invalids = [], [], [], []
        seen_numbers = set()
        cleaned_numbers = []

        for idx, num in enumerate(df[column]):
            row_num = idx + 2
            original = str(num).strip()
            new_num = ''.join(c for c in original if c.isdigit() or (c == '+' and original.startswith('+')))
            new_num = new_num.replace(" ", "")
            if new_num != original:
                corrections.append((row_num, original, new_num))

            if len(new_num) < 9:
                invalids.append((row_num, new_num))
                cleaned_numbers.append(new_num)
                continue

            if new_num.startswith('+39') and len(new_num) == 13:
                corrected = new_num[3:]
                corrections.append((row_num, new_num, corrected))
                new_num = corrected
            elif new_num.startswith('393') and len(new_num) == 12:
                corrected = new_num[2:]
                corrections.append((row_num, new_num, corrected))
                new_num = corrected

            if new_num.startswith('800'):
                cleaned_numbers.append(new_num)
                continue

            if not new_num.startswith(('3', '0')) and 9 <= len(new_num) <= 10:
                corrected = '0' + new_num
                corrections.append((row_num, new_num, corrected))
                new_num = corrected

            if new_num in seen_numbers:
                duplicates.append((row_num, new_num))
            else:
                seen_numbers.add(new_num)

            if len(new_num) > 10:
                anomalies.append((row_num, new_num))

            if len(new_num) == 9 and new_num[:3] not in VALID_PREFIXES:
                invalids.append((row_num, new_num))

            cleaned_numbers.append(new_num)

        df[column] = cleaned_numbers
        base = os.path.splitext(file.filename)[0]

        path_corr = f"{OUTPUT_FOLDER}/{base}_corretto.xlsx"
        path_log1 = f"{LOGS_FOLDER}/{base}_correzioni.xlsx"
        path_log2 = f"{LOGS_FOLDER}/{base}_duplicati.xlsx"
        path_log3 = f"{LOGS_FOLDER}/{base}_anomalie.xlsx"
        path_log4 = f"{LOGS_FOLDER}/{base}_non_validi.xlsx"
        path_def = f"{OUTPUT_FOLDER}/{base}_definitivo.xlsx"
        zip_path = f"{OUTPUT_FOLDER}/{base}_risultati.zip"

        df.to_excel(path_corr, index=False)
        pd.DataFrame(corrections, columns=["Riga", "Originale", "Corretto"]).to_excel(path_log1, index=False)
        pd.DataFrame(duplicates, columns=["Riga", "Duplicato"]).to_excel(path_log2, index=False)
        pd.DataFrame(anomalies, columns=["Riga", "Anomalia"]).to_excel(path_log3, index=False)
        pd.DataFrame(invalids, columns=["Riga", "Non_Valido"]).to_excel(path_log4, index=False)

        excluded = set([x[1] for x in duplicates] + [x[1] for x in anomalies] + [x[1] for x in invalids])
        df_def = df[~df[column].astype(str).isin(excluded)]
        df_def.to_excel(path_def, index=False)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in [path_corr, path_log1, path_log2, path_log3, path_log4, path_def]:
                zipf.write(f, os.path.basename(f))

        return send_file(zip_path, as_attachment=True)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)