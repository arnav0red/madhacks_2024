from flask import Flask, request, jsonify
from flask_cors import CORS
import main  # Import your game logic

app = Flask(__name__)
CORS(app)

# Store chat messages (or game state) temporarily
messages = []

# Initial button list (before game starts)
button_list = [{"label": "Start Game", "action": "start_game", "description": "Start the game session."},
               {"label": "Add Player", "action": "add_player", "description": "Add a player to the game."}]


@app.route("/send_game_update", methods=["POST"])
def send_game_update():
    """Receive data from the game and update the front-end."""
    data = request.json
    game_message:str = data.get("message", "")
    # Save the game message to be displayed in the front-end
    messages.append({"sender": "You", "message": game_message})
    return jsonify({"response": "Game update received"})

@app.route("/send_response_update", methods=["POST"])
def send_response_update():
    """Receive data from the game and update the front-end."""
    data = request.json
    game_message:str = data.get("message", "")
    # Save the game message to be displayed in the front-end
    messages.append({"sender": "Your Date", "message": game_message})
    return jsonify({"response": "Game update received"})


@app.route("/get_messages", methods=["GET"])
def get_messages():
    """Fetch chat messages to send to the front-end."""
    return jsonify({"messages": messages})


@app.route("/get_buttons", methods=["GET"])
def get_buttons():
    """Fetch available buttons to send to the front-end."""
    return jsonify({"buttons": button_list})


@app.route("/button_click", methods=["POST"])
def button_click():
    """Receive the button click action and forward it to the game."""
    data = request.json
    button_action = data.get("action", "")

    # Handle the button click (send action to game)
    game_response = main.handle_button_action(button_action)

    # Optionally, send the updated response to the front-end
    #messages.append({"sender": "You", "message": game_response})

    return jsonify({"response": game_response})


# Endpoint to update buttons when game state changes
@app.route("/update_buttons", methods=["POST"])
def update_buttons():
    """Update the button list after the game starts."""
    global button_list
    data = request.json
    button_list = data.get("buttons", [])

    return jsonify({"response": "Button list updated"})


if __name__ == "__main__":
    app.run(debug=True)
