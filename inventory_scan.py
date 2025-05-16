from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import pandas as pd

app = Flask(__name__)
CORS(app)

def search_pubchem_similarity(smiles, threshold=70):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/similarity/smiles/{smiles}/JSON?Threshold={threshold}&MaxRecords=100"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        similar_cids = data.get("IdentifierList", {}).get("CID", [])
        return similar_cids
    except requests.exceptions.RequestException as e:
        return {"error": f"Error during PubChem similarity search: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred during PubChem search: {e}"}

def get_pubchem_properties(cid):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/IUPACName,CAS/JSON"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        properties = data.get("PropertyTable", {}).get("Properties", [{}])[0]
        iupac_name = properties.get("IUPACName")
        cas = properties.get("CAS")
        return iupac_name, cas
    except requests.exceptions.RequestException as e:
        return None, None
    except Exception as e:
        return None, None

def search_inventory(names, cas_numbers, inventory_df):
    matches = inventory_df[
        (inventory_df['ChemicalName'].isin(names)) | (inventory_df['CASNumber'].isin(cas_numbers))
    ]
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

@app.route('/api/search', methods=['POST'])
def search():
    data = request.get_json()
    smiles = data.get('smiles')
    if smiles:
        try:
            similar_cids = search_pubchem_similarity(smiles)
            if isinstance(similar_cids, dict) and "error" in similar_cids:
                return jsonify(similar_cids), 500

            pubchem_results = []
            names = set()
            cas_numbers = set()
            for cid in similar_cids:
                name, cas = get_pubchem_properties(cid)
                if name:
                    names.add(name)
                if cas:
                    cas_numbers.add(cas)
                pubchem_results.append({"CID": cid, "Name": name, "CAS": cas})

            inventory_df = pd.read_csv("Walczak-Inventory.csv")
            inventory_matches = search_inventory(list(names), list(cas_numbers), inventory_df)

            return jsonify({"pubchem_hits": pubchem_results, "inventory_matches": inventory_matches})

        except FileNotFoundError:
            return jsonify({"error": "Could not find the inventory file 'Walczak-Inventory.csv'."}), 404
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"error": "No SMILES string provided"}), 400

if __name__ == '__main__':
    app.run(debug=True)
