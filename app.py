from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)
Classification_File = 'Classification Results on Face Dataset (1000 images).csv'
Column_Names = ['Image', 'Results']
DataFrame = pd.read_csv(Classification_File, header=None, names=Column_Names) #remove header
Mapping = DataFrame.set_index(Column_Names[0])[Column_Names[1]].to_dict()


@app.route("/", methods=["POST"])
def findFaceClassification():
    if 'inputFile' not in request.files:
        return "No File Found"
    current_file = request.files['inputFile']
    current_file_name, current_file_extension = os.path.splitext(current_file.filename)

    Allowed_Extensions = {'.jpg'}
    if current_file_extension.lower() not in Allowed_Extensions:
        return "Error: Unsupported file format. Please upload an image file of jpg!"
        
    if current_file_name not in Mapping:
        return "Error! File not found in the given data"
    
    Result = Mapping[current_file_name]
    return jsonify({current_file_name: Result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)