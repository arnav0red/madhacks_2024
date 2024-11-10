import google.generativeai as genai
import json, re, random, requests, time
from typing import List
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
        self.deck: List[Card] = [cardsMap[4]] * 3 + [cardsMap[5]] * 3 + [cardsMap[8]]

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

    def giveCards(self, numCards: int):
        if len(self.deck) < numCards:
            self.deck = self.grave
            random.shuffle(self.deck)
            self.grave = []
        return [self.deck.pop() for i in range(numCards)]

    def startRound(self):
        giveUserOutput(
            f"Stats: \nMorale: {self.morale}, Attraction: {self.attraction}/{self.maxAttraction}\nDebuffs: {convertToList(self.debuffs)}"
        )
        self.hand = self.giveCards(self.drawPerTurn)
        giveUserOutput("Your cards: " + str([i.name for i in self.hand]))
        playedCard = convertInputToCard(
            askUserInput("Which card would you like to play? "), self.hand
        )
        self.playCard(playedCard)

    def playCard(self, card: Card):
        giveUserOutput(f"Playing: {card.name}\n{card.description}\n")
        if "attract" in card.effect:
            self.attraction += card.effect["attract"]
        if "friendzone" in card.effect:
            self.moraleDamagePerTurn += card.effect["friendzone"]
            if "friendzone" in self.debuffs:
                self.debuffs["friendzone"] += card.effect["friendzone"]
            else:
                self.debuffs["friendzone"] = card.effect["friendzone"]
        if "decrAffect" in card.effect:
            card.effect["attract"] -= card.effect["decrAffect"]

    def endRound(self):
        self.morale -= self.moraleDamagePerTurn
        if self.morale <= 0:
            return False
        self.grave.extend(self.hand)
        self.hand = []
        return True


class GameSession:

    def __init__(self, winningScore: int):
        self.scoringChat = model.start_chat(
            history=[{"role": "user", "parts": gameStartInformationPrompt}]
            + convertedCharInfo
        )
        self.winningScore = winningScore
        self.playerList: List[Player] = []

    def addPlayers(self, listPlayers: list):
        self.playerList.extend(listPlayers)
        return self.playerList

    def getListPlayers(self):
        return self.playerList

    def scorePlayers(self, responseText: str) -> Player:
        responseList = responseText.split("\n")
        print(responseList)
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


def sendMessage(session: GameSession, msgList: List[str]) -> str:
    message = ""
    for i in range(len(msgList)):
        message += f"{i}. {session.getListPlayers()[i]}: {msgList[i]} \n, "
    response = session.scoringChat.send_message(
        message,
        safety_settings={
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        },
    )
    print("message: $", message, "$")
    return response.text


def askUserInput(message: str):
    return input(message)


def giveUserOutput(message: str):
    send_message_to_flask(message)
    print(message)


def giveUserButtons(listData: list):
    toReturn = []
    for i in listData:
        toReturn.append(
            {"label": i[0], "id": i[1]},
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


def send_message_to_flask(message):
    url = "http://127.0.0.1:5000/send_message"
    response = requests.post(url, json={"message": message})
    if response.status_code == 200:
        return response.json().get("response")
    else:
        print("Failed to get a response from Flask server.")
        return None


def update_buttons(new_buttons):
    url = "http://127.0.0.1:5000/update_buttons"
    response = requests.post(url, json={"buttons": new_buttons})
    if response.status_code == 200:
        print("Buttons updated successfully.")
    else:
        print("Failed to update buttons.")


gamesSet = set()
with open("data.json", "r") as file:
    data = json.load(file)
gameStartInformationPrompt = data["gameStartInformation"]
charInfo = data["charInfo"]
convertedCharInfo = []
for i in charInfo:
    convertedCharInfo.append({"role": "user", "parts": i})
cardInfo = data["cards"]
cardsMap = {}
for i in cardInfo:
    cardsMap[i["id"]] = card = Card(
        id=i["id"],
        name=i["name"],
        flavor_text=i["flavor_text"],
        description=i["description"],  # Blank for now
        type=i["type"],  # Blank for now
        effect=i["effect"],  # Blank for now
    )
if __name__ == "__main__":
    mainSesh = startGameSession(["John"])
    players = mainSesh.getListPlayers()

    round = Round(players[0], 100)

    round.startRound()
    while round.endRound():
        round.startRound()
        time.sleep(1)
    # while True:
    #     print(
    #         f"Curr Score: {players[0].score}/{mainSesh.winningScore}, {players[1].score}/{mainSesh.winningScore},"
    #     )
    #     inp1 = input("P1 input:")
    #     inp2 = input("P2 input:")
    #     print(f"Inputs: {inp1} {inp2}")
    #     mainSesh.scorePlayers(sendMessage(mainSesh, [inp1, inp2]))
