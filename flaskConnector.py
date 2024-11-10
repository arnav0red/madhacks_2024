from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Store messages and buttons in memory
messages = []
button_list = [{"label": "Hello", "action": "Hello"}, {"label": "Goodbye", "action": "Goodbye"}]

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    user_message = data.get("message", "")
    messages.append({"sender": "user", "message": user_message})
    
    bot_response = f"Echo: {user_message}"
    messages.append({"sender": "bot", "message": bot_response})
    
    return jsonify({"response": bot_response})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify({"messages": messages})

@app.route('/get_buttons', methods=['GET'])
def get_buttons():
    return jsonify({"buttons": button_list})

# Endpoint to update button list
@app.route('/update_buttons', methods=['POST'])
def update_buttons():
    global button_list
    new_buttons = request.json.get("buttons", [])
    button_list = new_buttons
    return jsonify({"status": "Buttons updated"})

if __name__ == '__main__':
    app.run(debug=True)
