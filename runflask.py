""" Runs a flask local server to view the conversations, summaries, and generated KGs"""

from flask import Flask, jsonify, render_template
import parse
from parse import Entry
import generatekgs
data = parse.parse()

app = Flask(__name__, static_url_path = "/graphs", static_folder = "graphs")

# Route to get the index HTML page
@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

# Route to return the desired conversation text
@app.route('/conversation/<int:id>', methods = ['GET'])
def getConversation(id):
    try:
        return jsonify({'data': data[id].dialog_raw, 'error': False})
    except:
        return jsonify({'data': [], 'error': True})

# Route to return the desired summary text
@app.route('/summary/<int:id>', methods = ['GET'])
def getSummary(id):
    try:
        return jsonify({'data': data[id].summaries, 'error': False})
    except:
        return jsonify({'data': [], 'error': True})

# Route to generate the KGs for the desired conversation
@app.route('/kgs/<int:id>', methods = ['GET'])
def getKgs(id):
    try:
        generatekgs.generate_kgs(id)
        return jsonify({'error': False})
    except:
        return jsonify({'error': True})

if __name__ == '__main__':
    port = 8000
    app.run(debug=True)