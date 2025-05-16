from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import pandas as pd
import os

app = Flask(__name__)
CORS(app)


def search_pubchem(smiles, csv="Walczak-Inventory.xlsx", threshold=70):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/similarity/smiles/{smiles}/JSON?Threshold={threshold}&MaxRecords=100"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        similar_cids = data.get("IdentifierList", {}).get("CID", [])
        if not similar_cids:
            return "No similar compounds found on PubChem."

        try:
            df = pd.read_csv(csv)
        except FileNotFoundError:
            return f"Error: Could not find the file '{csv}'. Please make sure it's in the same directory."

        matches = df[df["PubChem_ID"].isin(similar_cids)]

        if matches.empty:
            return "Compound not found in the inventory."

        results = []
        for _, row in matches.iterrows():
            result = {
                "Name": row.get('ChemicalName', 'N/A'),
                "CAS": row['CASNumber'],
                "ID": row['ChemicalID'],
                "Quantity": f"{row.get('Qty', 'N/A')} {row.get('Units', '')}",
                "Room": row['Room'],
                "Location1": row['Location1'],
                "Location2": row['Location2']
            }
            results.append(result)

        return results

    except requests.exceptions.RequestException as e:
        return {"error": f"Error during PubChem request: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    smiles = data.get('smiles')
    if smiles:
        results = search_pubchem(smiles)
        return jsonify(results)
    else:
        return jsonify({"error": "No SMILES string provided"}), 400


@app.route('/')
def index():
    #  Calculate the directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "index.html")


if __name__ == '__main__':
    app.run(debug=True)
