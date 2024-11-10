import google.generativeai as genai
import json, re, random, requests, time, copy
from typing import List, Dict
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import flaskConnector

genai.configure(api_key=open("geminiKey.txt", "r").readline())
model = genai.GenerativeModel("gemini-1.0-pro")


class Card:
    def __init__(
        self, id: int, name: str, flavor_text: str, description: str, type: str, effect
    ):
        self.id = id
        self.name = name
        self.flavor_text = flavor_text
        self.description = description
        self.type = type
        self.effect: dict = effect

    def __str__(self):
        return (
            f"Card ID: {self.id}\n"
            f"Name: {self.name}\n"
            f"Flavor Text: {self.flavor_text}\n"
            f"Description: {self.description}\n"
            f"Type: {self.type}\n"
            f"Effect: {self.effect}\n"
        )


class Player:
    def __init__(self, name: str):
        self.name = name
        self.score = 0
        self.morale = 100
        self.deck: List[Card] = []
        self.deck.extend([copy.deepcopy(cardsMap[4]) for _ in range(1)])
        self.deck.extend([copy.deepcopy(cardsMap[5]) for _ in range(1)])
        self.deck.extend([copy.deepcopy(cardsMap[8]) for _ in range(1)])
        self.deck.extend([copy.deepcopy(cardsMap[3]) for _ in range(1)])
        self.deck.extend([copy.deepcopy(cardsMap[7]) for _ in range(1)])

    def __str__(self):
        return self.name


class Round:
    def __init__(
        self,
        player: Player,
        maxAttraction: int,
    ):
        self.player = player
        self.morale = player.morale
        self.deck: List[Card] = self.player.deck.copy()
        random.shuffle(self.deck)
        self.hand: List[Card] = []
        self.grave: List[Card] = []
        self.maxAttraction = maxAttraction
        self.attraction = 0
        self.moraleDamagePerTurn = 10
        self.drawPerTurn = 3
        self.debuffs = {}
        self.buffs = {}

    def giveCards(self, numCards: int):
        if len(self.deck) < numCards:
            self.deck = self.grave
            random.shuffle(self.deck)
            self.grave = []
        return [self.deck.pop() for i in range(numCards)]

    def startRound(self):
        giveUserOutput(
            f"Stats: \nMorale: {self.morale}, Attraction: {self.attraction}/{self.maxAttraction}\nBuffs: {convertToList(self.buffs)}, Debuffs: {convertToList(self.debuffs)}"
        )
        self.hand = self.giveCards(self.drawPerTurn)
        giveUserOutput("Your cards: " + str([i.name for i in self.hand]))
        giveUserButtons(
            [
                [i.name, i.id, "(" + i.description + ") " + i.flavor_text]
                for i in self.hand
            ]
        )

        # askUserInput("Which card would you like to play? ")

    def playCard(self, card: Card):
        giveUserOutput(f"Playing: {card.name}\n{card.description}\n")
        if "attract" in card.effect:
            addition = 0
            if "confidence" in self.buffs:
                addition = self.buffs["confidence"]
            self.attraction += card.effect["attract"] + addition
        if "friendzone" in card.effect:
            self.moraleDamagePerTurn += card.effect["friendzone"]
            if "friendzone" in self.debuffs:
                self.debuffs["friendzone"] += card.effect["friendzone"]
            else:
                self.debuffs["friendzone"] = card.effect["friendzone"]
        if "decrAffect" in card.effect:
            card.effect["attract"] -= card.effect["decrAffect"]
            card.description = re.sub(
                r"(Attract \+ )\d+",
                r"\g<1>" + str(card.effect["attract"]),
                card.description,
            )
        if "gamba" in card.effect:
            weights = [float(i) for i in card.effect["gamba"].keys()]

            play = random.choices([1, 2], weights)
            if play == 1:
                addition = 0
                if "confidence" in self.buffs:
                    addition = self.buffs["confidence"]
                self.attraction += card.effect["gamba"]["0.2"]["attract"] + addition
                send_message_to_flask("Worked out")
            else:
                self.morale -= card.effect["gamba"]["0.8"]["moraleNeg"]
                send_message_to_flask("Didn't work out")

    def endRound(self):
        self.morale -= self.moraleDamagePerTurn
        if self.morale <= 0:
            return False
        self.grave.extend(self.hand)
        self.hand = []
        return True


class GameSession:

    def __init__(self, winningScore: int, player: str):
        self.scoringChat = model.start_chat(
            history=[{"role": "user", "parts": gameStartInformationPrompt}]
            + convertedCharInfo
        )
        self.userChat = model.start_chat(history=[{"role": "user", "parts": userInfo}])
        self.winningScore = winningScore
        self.playerList: List[Player] = [Player(player)]
        self.round = Round(self.playerList[0], 100)

    def addPlayers(self, listPlayers: list):
        self.playerList.extend(listPlayers)
        return self.playerList

    def getListPlayers(self):
        return self.playerList

    def scorePlayers(self, responseText: str) -> Player:
        responseList = responseText.split("\n")
        for i in range(len(responseList)):
            if i == int(re.findall(r"(\d+):\s*-?\s*\d", responseList[i])[0]):
                self.playerList[i].score += int(
                    re.findall(r"\d:\s*(-?\d)", responseList[i])[0]
                )


def startGameSession(userList: List[str]) -> GameSession:
    sesh = GameSession(10)
    sesh.addPlayers([Player(i) for i in userList])
    gamesSet.add(sesh)
    return sesh


def sendMessage(chat, message) -> str:
    response = chat.send_message(
        message,
        safety_settings={
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )
    return response.text


def askUserInput(message: str):
    return input(message)


def giveUserOutput(message: str):
    send_message_to_flask(message)
    print(message)


def giveUserButtons(listData: list):
    toReturn = []
    for i in range(len(listData)):
        toReturn.append(
            {"label": listData[i][0], "action": i, "description": listData[i][2]},
        )
    update_buttons(toReturn)


def convertInputToCard(message: str, listCards: List[Card]):
    temp = int(message)
    if temp >= len(listCards) or temp < 0:
        return listCards[0]
    return listCards[temp]


def convertToList(inputDict: dict):
    message = ""
    for i in inputDict:
        message += f"{str(i).capitalize()}: {inputDict[i]}"
    return message


def update_buttons(new_buttons):
    url = "http://127.0.0.1:5000/update_buttons"
    response = requests.post(url, json={"buttons": new_buttons})
    if response.status_code == 200:
        print("Buttons updated successfully.")
    else:
        print("Failed to update buttons.")


def handle_button_action(action):
    if len(mainSesh.round.hand) > 0:
        mainSesh.round.playCard(mainSesh.round.hand[action])
        if useAI:
            userText = sendMessage(mainSesh.userChat, mainSesh.round.hand[action].name)
            responseText = sendMessage(mainSesh.scoringChat, userText)
            send_message_to_flask(userText)
            send_response_to_flask(responseText)
    if mainSesh.round.endRound():
        mainSesh.round.startRound()
    else:
        send_message_to_flask(
            "Your morale is shattered. It's over for now, but don't give up—perhaps you'll rise again!"
        )


def send_message_to_flask(message):
    """Send game output to Flask for front-end display."""
    url = "http://127.0.0.1:5000/send_game_update"  # Flask server URL
    response = requests.post(url, json={"message": message})
    return response.json()


def send_response_to_flask(message):
    """Send game output to Flask for front-end display."""
    url = "http://127.0.0.1:5000/send_response_update"  # Flask server URL
    response = requests.post(url, json={"message": message})
    return response.json()


gamesSet = set()
with open("data.json", "r") as file:
    data = json.load(file)
gameStartInformationPrompt = data["gameStartInformation"]
charInfo = data["charInfo"]
userInfo = data["userInfo"]
useAI = False
convertedCharInfo = []
for i in charInfo:
    convertedCharInfo.append({"role": "user", "parts": i})
cardInfo = data["cards"]
cardsMap: Dict[int, Card] = {}
for i in cardInfo:
    cardsMap[i["id"]] = card = Card(
        id=i["id"],
        name=i["name"],
        flavor_text=i["flavor_text"],
        description=i["description"],  # Blank for now
        type=i["type"],  # Blank for now
        effect=i["effect"],  # Blank for now
    )
mainSesh = GameSession(10, "John")

if __name__ == "__main__":
    players = mainSesh.getListPlayers()

    mainSesh.round.startRound()
    while True:
        time.sleep(1)
    # while True:
    #     print(
    #         f"Curr Score: {players[0].score}/{mainSesh.winningScore}, {players[1].score}/{mainSesh.winningScore},"
    #     )
    #     inp1 = input("P1 input:")
    #     inp2 = input("P2 input:")
    #     print(f"Inputs: {inp1} {inp2}")
    #     mainSesh.scorePlayers(sendMessage(mainSesh, [inp1, inp2]))
