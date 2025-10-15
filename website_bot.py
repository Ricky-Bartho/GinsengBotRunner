import requests
import time
import re
from ctypes import *
from server_helper import *
import json
from urllib.parse import quote_plus, unquote

get_n_move_pendings_url = f"https://skudpaisho.com/backend/getCountOfGamesWhereUserTurn.php"

get_current_games_url = "https://skudpaisho.com/backend/getCurrentGamesForUserNew.php"
get_game_notation_url = "https://skudpaisho.com/backend/getGameNotationAndClock.php"
make_move_url = "https://skudpaisho.com/backend/updateGameNotationV3.php"
send_chat_url = "https://skudpaisho.com/backend/sendChatMessage.php"
win_lose_url = "https://skudpaisho.com/backend/updateGameWinInfoNew.php"
create_game_url = "https://skudpaisho.com/backend/createGameV2.php"
get_game_requests_url = "https://skudpaisho.com/backend/getCurrentGameSeeksHostedByUser.php"
get_my_turn_url = "https://skudpaisho.com/backend/getGameInfoV2.php"
get_chat_url = "https://skudpaisho.com/backend/getNewChatMessages.php"

libpai = CDLL('./libpy_wrapper.so')
libpai.py_prune.restype = c_ulonglong
libpai.py_make_move.argtypes = [c_int, c_ulonglong]

move_list = []
host_id_map = {"K": 2, "B": 4, "D": 3, "FB": 5, "LT": 6, "O": 9, "G": 11, "W": 10, "L": 1}
guest_id_map = {"K": 14, "B": 16, "D": 15, "FB": 17, "LT": 18, "O": 21, "G": 20, "W": 19, "L": 1}

HOST_VAL = 0
GUEST_VAL = 1

class GinsengBot:

    def __init__(self, depth=3, null=False, quiesce=False, g5_rule=False, bison_jump=False):
        self.move_list = []
        self.move_num = 0
        self.current_player = GUEST_VAL
        self.host_guest = "GUEST"
        self.hg_letter = self.host_guest[0]
        self.id_map = guest_id_map

        self.depth = depth
        self.null = null
        self.quiesce = quiesce
        libpai.py_init_board(g5_rule, bison_jump)

    def get_move(self) -> RootModel:
        move = libpai.py_prune(self.depth, self.null, self.quiesce)
        jmove = c_to_j(Move.parse_int(move), ((self.move_num-1) // 2) + 1, self.host_guest, self.hg_letter, self.id_map)
        return jmove

    def make_move(self, move: RootModel) -> int: #returns bot's eval
        self.current_player = GUEST_VAL if self.current_player == HOST_VAL else HOST_VAL
        self.host_guest = "GUEST" if self.host_guest == "HOST" else "HOST"
        self.hg_letter = self.host_guest[0]
        self.id_map = guest_id_map if self.current_player == GUEST_VAL else host_id_map

        cmove = j_to_c(move).get_int()
        self.move_list.append(cmove)
        print(self.move_list)
        #white == 0, black == 1
        eval = libpai.py_make_move(0 if move.player == "HOST" else 1, cmove)
        self.move_num += 1
        return eval


class WebGetter:

    def __init__(self, player_id: int, username: str, useremail: str, deviceid: str):
        self.PLAYER_ID = player_id
        self.USERNAME = username
        self.USEREMAIL = useremail
        self.DEVICEID = deviceid

    def get_n_move_pendings(self) -> int:
        q_params = {"userId" : self.PLAYER_ID}
        response = requests.get(get_n_move_pendings_url, params=q_params)
        return int(response.text)

    def get_current_games(self):
        post_payload = {"userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID}
        response = requests.post(get_current_games_url, data=post_payload)
        entries = response.text.split("\n")
        entries = list(filter(None, entries))
        only_game_ids = []
        for entry in entries:
            only_game_ids.append(entry.split("|")[0])
        return only_game_ids

    def get_game_moves(self, game_id) -> List[RootModel]:
        notation_arr = self.get_game_notation(game_id)
        ret_arr = []
        for m_notation in notation_arr:
            t_move = RootModel.model_validate(m_notation)
            ret_arr.append(t_move)
        return ret_arr

    def get_game_notation(self, game_id):
        get_url = f"{get_game_notation_url}?q={game_id}"
        response = requests.get(get_url)
        resp_str = response.json()['notation']
        if resp_str[0] == "%":
            resp_str = unquote(resp_str)
        #print(resp_str)
        return json.loads(resp_str)

    def make_web_move(self, game_id: str, m_list: List[RootModel]):
        m_json = []
        for m in m_list:
            m_json.append(m.model_dump(exclude_defaults=True, exclude_none=True))
        m_string = json.dumps(m_json)
        post_payload = {"id": game_id, "t": quote_plus(m_string), "userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID, "gameTypeName": "Ginseng Pai Sho", "gameClockJson": "", "gameResultId": "NaN"}
        response = requests.post(make_move_url, data=post_payload)
        return response.text

    def send_chat(self, msg: str, game_id: str):
        payload = {"gameId": game_id, "userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID, "chatMessage": msg}
        response = requests.post(send_chat_url, data=payload)
        return response.text

    def send_win(self, game_id: str):
        payload = {"gameId": game_id, "winnerUsername": self.PLAYER_ID, "resultTypeCode": "1", "userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID, "updateRatings": "", "gameTypeId": "18", "hostUsername": "HOST", "guestUsername": "GUEST"}
        response = requests.post(win_lose_url, data=payload)
        return response.text

    def send_resign(self, game_id: str):
        payload = {"gameId": game_id, "winnerUsername": "Human", "resultTypeCode": "9", "userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID, "updateRatings": "", "gameTypeId": "18", "hostUsername": "HOST", "guestUsername": "GUEST"}
        response = requests.post(win_lose_url, data=payload)
        return response.text

    def create_game(self, ):
        firstmove = "%5B%7B%22moveNum%22%3A0%2C%22player%22%3A%22HOST%22%2C%22moveType%22%3A%22--%22%2C%22promptTargetData%22%3A%7B%7D%7D%5D"
        #fmove_str = quote_plus(json.dumps(firstmove))
        #print(fmove_str)
        payload = {"t": "18", "q": firstmove, "userId": self.PLAYER_ID, "username": self.USERNAME, "userEmail": self.USEREMAIL, "deviceId": self.DEVICEID, "options": "[]", "isPrivateIndicator": "", "isWeb": "1", "rankedGame": "n", "gameClockJson": ""}
        response = requests.post(create_game_url, data=payload)
        return response.text

    def get_pending_games(self, ) -> bool:
        q_params = {"userId" : "34354", "gameTypeId": "18"}
        response = requests.get(get_game_requests_url, params=q_params)
        return "Results" in response.text

    def get_my_turn(self, game_id: str) -> bool:
        q_params = {"userId": self.PLAYER_ID, "gameId": game_id, "isWeb": "1"}
        response = requests.get(get_my_turn_url, params=q_params)
        entries = response.text.split("\n")
        entries = list(filter(None, entries))
        for entry in entries:
            entry_split = entry.split("|||")
            if entry_split[0] == game_id:
                return entry_split[7] == "1"
        return False

    def get_chat_messages(self, game_id: str):
        q_params = {"g": game_id, "t": "1970-01-01 00:00:00"}
        response = requests.get(get_chat_url, params=q_params)
        entries = response.text.split("\n")
        entries = list(filter(None, entries))
        return entries

    depth_change_pattern = r"depth: (\d+)"

    def get_settings_chage(self, game_id: str) -> int | None:
        new_chats = self.get_chat_messages(game_id)
        to_print = True
        for i in range(len(new_chats)-1, -1, -1):
            chat = new_chats[i]
            chat_split = chat.split("|||")
            chat_str = chat_split[2]
            depth_change_match = re.search(WebGetter.depth_change_pattern, chat_str)
            if depth_change_match is not None:
                try:
                    new_depth = int(depth_change_match.group(1))
                except:
                    print("invalid depth change request: ", depth_change_match.group(1))
                    return None
                
                if to_print:
                    self.send_chat(f"Changed depth to: {new_depth}", game_id)
                return new_depth

            elif "Changed depth to" in chat_str:
                #already changed depth, don't change again.
                to_print = False

    def is_game_g5(self, game_id: str) -> bool:
        q_params = {"userId": self.PLAYER_ID, "gameId": game_id, "isWeb": "1"}
        response = requests.get(get_my_turn_url, params=q_params)
        entries = response.text.split("\n")
        entries = list(filter(None, entries))
        entry = entries[0]
        return "GinsengLimit5" in entry

    def is_game_bison(self, game_id: str) -> bool:
        q_params = {"userId": self.PLAYER_ID, "gameId": game_id, "isWeb": "1"}
        response = requests.get(get_my_turn_url, params=q_params)
        entries = response.text.split("\n")
        entries = list(filter(None, entries))
        entry = entries[0]
        return "BisonGrantsFlying" in entry



if __name__ == "__main__":

    wg = WebGetter(UPDATE_PLAYER_ID, UPDATE_USERNAME, UPDATE_USEREMAIL, UPDATE_DEVICEID)

    for _ in range(100):

        print("Waiting for games...")

        if wg.get_n_move_pendings() > 0:
            #if you have moves to be made
            print("Games found!")
            current_games = wg.get_current_games()
            #get all games (this includes games where it's not your turn)
            for game_id in current_games:
                if wg.get_my_turn(game_id):
                    #check if it's your turn, then prune and make a move
                    g5_rule = wg.is_game_g5(game_id)
                    bison_rule = wg.is_game_bison(game_id)
                    print("making move for: ", game_id)
                    bot = GinsengBot(depth=7, g5_rule=g5_rule, bison_jump=bison_rule)

                    moves = wg.get_game_moves(game_id)
                    if len(moves) <= 2:
                        wg.send_chat("Good luck! To change the depth type \"depth: N\". if successful, I will respond when I make my move. Use 1 -> 7", game_id)
                    settings_change = wg.get_settings_chage(game_id)
                    if settings_change is not None and settings_change >= 1 and settings_change <= 7:
                        bot.depth = settings_change
                    for m in moves:
                        if m.moveNum > 0:
                            print("eval: ", bot.make_move(m))
                    new_move = bot.get_move()
                    #I think this is the case where the bot returns 0, just resign lol.
                    if new_move.startPoint == '8,-8' or new_move.endPoint == '8,-8':
                        wg.send_resign(game_id)
                        wg.send_chat("You've bested me, gg!", game_id)
                        continue
                    eval = bot.make_move(new_move)
                    moves.append(new_move)
                    wg.make_web_move(game_id, moves)
                    #Send chat message with move number and eval
                    wg.send_chat(f"move: {((bot.move_num-1) // 2) + 1}, Eval: {eval}", game_id)
                    if abs(eval) > 99999:
                        wg.send_win(game_id)
                        print("Game finished!")
                    time.sleep(5)
        time.sleep(20)
