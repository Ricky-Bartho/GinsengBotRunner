from ctypes import *
from pydantic import BaseModel
from typing import Dict, List

row_map = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
col_map = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q']
piece_map = ["K", "B", "D", "FB", "LT", "O", "G", "W", "L"]

class Move:
    def __init__(self):
        self.s1 = 0
        self.s2 = 0
        self.s3 = 0
        self.s4 = 0
        self.capture = 0
        self.cappiece = 0
        self.piece = 0
        self.ability = 0
        self.swap = 0
        self.swap_piece = 0

    def get_int(self) -> int:
        return self.swap_piece << 47 | self.swap << 46 | self.s4 << 37 | self.s3 << 28 | self.cappiece << 24 | self.ability << 23 | self.piece << 19 | self.capture << 18 | self.s2 << 9 | self.s1

    def parse_int(move):
        m = Move()
        m.s1 = move & 0b111111111
        m.s2 = (move >> 9) & 0b111111111
        m.capture = (move >> 18) & 0b1
        m.piece = (move >> 19) & 0b1111
        m.ability = (move >> 23) & 0b1
        m.cappiece = (move >> 24) & 0b1111
        m.s3 = (move >> 28) & 0b111111111
        m.s4 = (move >> 37) & 0b111111111
        m.swap = (move >> 46) & 0b1
        m.swap_piece = (move >> 47) & 0b1111
        return m


def get_row(sq):
    return sq // 17

def get_col(sq):
    return sq % 17


def get_x(sq):
    return get_col(sq) - 8

def get_y(sq):
    return get_row(sq) - 8

def print_move(move):
    s1 = move & 0b111111111
    print("s1: ", col_map[get_col(s1)], row_map[get_row(s1)])
    s2 = (move >> 9) & 0b111111111
    print("s2: ", col_map[get_col(s2)], row_map[get_row(s2)])
    print("capture: ", (move >> 18) & 0b1)
    piece = (move >> 19) & 0b1111
    print("piece: ", piece_map[piece])
    ability = (move >> 23) & 0b1
    print("ability: ", ability)
    cappiece = (move >> 24) & 0b1111
    print("cappiece: ", piece_map[cappiece])
    s3 = (move >> 28) & 0b111111111
    print("s3: ", col_map[get_col(s3)], row_map[get_row(s3)])
    s4 = (move >> 37) & 0b111111111
    print("s4: ", col_map[get_col(s4)], row_map[get_row(s4)])
    swap = (move >> 46) & 0b1
    print("swap: ", swap)
    swap_piece = (move >> 47) & 0b1111
    print("swap_piece: ", piece_map[swap_piece])


def row_col_to_sq(x, y):
    return (y+8) * 17 + (x+8)


class Settings(BaseModel):
    depth: int = 4
    null: bool = False
    quiesce: bool = False
    g5: bool | None = None
    bison_jump: bool | None = None

class RowAndColumn(BaseModel):
    row: int | None = None
    col: int | None = None
    x: int | None = None
    y: int | None = None
    notationPointString: str | None = None

class MovedTilePoint(BaseModel):
    pointText: str | None = None
    x: int | None = None
    y: int | None = None
    rowAndColumn: RowAndColumn | None = None

class MovedTileDestinationPoint(BaseModel):
    pointText: str | None = None
    x: int | None = None
    y: int | None = None
    rowAndColumn: RowAndColumn | None = None

class ChosenCapturedTile(BaseModel):
    ownerName: str | None = None
    code: str | None = None
    id: int | None = None

class PromptTargetDataItem(BaseModel):
    chosenCapturedTile: ChosenCapturedTile | None = None
    movedTilePoint: MovedTilePoint | None = None
    movedTileDestinationPoint: MovedTileDestinationPoint | None = None
    

class RootModel(BaseModel):
    moveNum: int | None = None
    player: str | None = None
    moveType: str | None = None
    startPoint: str | None = None
    endPoint: str | None = None
    promptTargetData: Dict[str, PromptTargetDataItem] | None = None
    endPointMovementPath: List[str] | None = None

class ptKey(BaseModel):
    tileOwner: str | None = None
    tileCode: str | None = None
    boardPoint: str | None = None
    tileId: int | None = None



gates = [[-8,0], [0,-8], [8,0], [0,8]]
def j_to_c(jmove: RootModel) -> Move:
    m = Move()
    start_point = jmove.startPoint

    start_x = int(start_point.split(",")[1])
    start_y = -int(start_point.split(",")[0])
    m.s1 = row_col_to_sq(start_x, start_y)

    end_point = jmove.endPoint
    end_x = int(end_point.split(",")[1])
    end_y = -int(end_point.split(",")[0])
    m.s2 = row_col_to_sq(end_x, end_y)

    #want to get promptTargetData["long string"][movedTilePoint][x] and [y]
    #this is s3
    pdata = jmove.promptTargetData
    for k, v in pdata.items():
        #assume only one key value pair in prompttargetdata
        if v.movedTilePoint is not None and v.movedTileDestinationPoint is not None:
            #This case means we are using ability
            m.ability = 1
            m.s3 = row_col_to_sq(int(v.movedTilePoint.rowAndColumn.y), -int(v.movedTilePoint.rowAndColumn.x))
            m.s4 = row_col_to_sq(int(v.movedTileDestinationPoint.rowAndColumn.y), -int(v.movedTileDestinationPoint.rowAndColumn.x))
        elif v.chosenCapturedTile is not None:
            #This case means we are swapping
            m.swap = 1
            m.swap_piece = piece_map.index(v.chosenCapturedTile.code)
    return m

def c_to_j(move: Move, move_num, host_guest, hg_letter, id_map) -> RootModel:

    jmove = RootModel()
    jmove.moveNum = move_num
    jmove.moveType = "Move"
    jmove.player = host_guest

    s1x = -get_y(move.s1)
    s1y = get_x(move.s1)

    s2x = -get_y(move.s2)
    s2y = get_x(move.s2)

    jmove.startPoint = f"{s1x},{s1y}"
    jmove.endPoint = f"{s2x},{s2y}"
    jmove.promptTargetData = {}
    jmove.endPointMovementPath = [f"{s1x},{s1y}", f"{s2x},{s2y}"]

    if move.ability: #use ability
        keyval = ptKey()
        keyval.tileOwner = hg_letter
        keyval.tileCode = piece_map[move.piece]
        keyval.boardPoint = f"{s2x},{s2y}"
        keyval.tileId = id_map[keyval.tileCode]

        s3x = -get_y(move.s3)
        s3y = get_x(move.s3)

        s3col = 8 - get_y(move.s3)
        s3row = 8 - get_x(move.s3)

        ptdata = PromptTargetDataItem()
        ptdata.movedTilePoint = MovedTilePoint()
        ptdata.movedTilePoint.pointText = f"{s3x},{s3y}"
        ptdata.movedTilePoint.x = s3x
        ptdata.movedTilePoint.y = s3y
        ptdata.movedTilePoint.rowAndColumn = RowAndColumn()
        ptdata.movedTilePoint.rowAndColumn.x = s3x
        ptdata.movedTilePoint.rowAndColumn.y = s3y
        ptdata.movedTilePoint.rowAndColumn.row = s3row
        ptdata.movedTilePoint.rowAndColumn.col = s3col
        ptdata.movedTilePoint.rowAndColumn.notationPointString = f"{s3x},{s3y}"

        s4x = -get_y(move.s4)
        s4y = get_x(move.s4)

        s4col = 8 - get_y(move.s4)
        s4row = 8 - get_x(move.s4)

        ptdata.movedTileDestinationPoint = MovedTileDestinationPoint()
        ptdata.movedTileDestinationPoint.pointText = f"{s4x},{s4y}"
        ptdata.movedTileDestinationPoint.x = s4x
        ptdata.movedTileDestinationPoint.y = s4y
        ptdata.movedTileDestinationPoint.rowAndColumn = RowAndColumn()
        ptdata.movedTileDestinationPoint.rowAndColumn.x = s4x
        ptdata.movedTileDestinationPoint.rowAndColumn.y = s4y
        ptdata.movedTileDestinationPoint.rowAndColumn.row = s4row
        ptdata.movedTileDestinationPoint.rowAndColumn.col = s4col
        ptdata.movedTileDestinationPoint.rowAndColumn.notationPointString = f"{s4x},{s4y}"

        jmove.promptTargetData = {keyval.model_dump_json(): ptdata}
    elif move.swap: #swap

        keyval = ptKey()
        keyval.tileOwner = hg_letter
        keyval.tileCode = piece_map[move.piece]
        keyval.boardPoint = f"{s2x},{s2y}" #TODO: might need to be s2
        keyval.tileId = id_map[keyval.tileCode]

        ptdata = PromptTargetDataItem()
        ptdata.chosenCapturedTile = ChosenCapturedTile()
        ptdata.chosenCapturedTile.ownerName = host_guest
        ptdata.chosenCapturedTile.code = piece_map[move.swap_piece]
        ptdata.chosenCapturedTile.id = id_map[ptdata.chosenCapturedTile.code]

        jmove.promptTargetData = {keyval.model_dump_json(): ptdata}
    #assume this will only be called after pruning. Which will be host's move. Only update the move number after pruning
    
    return jmove

