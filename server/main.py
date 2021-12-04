from typing import List
from fastapi import FastAPI, WebSocket, status
from starlette.websockets import WebSocketDisconnect
import json


app = FastAPI()


def init_board():
    # create empty board
    return [
        None, None, None,
        None, None, None,
        None, None, None,
    ]


board = init_board()


def is_draw():
    # checks if a draw
    global board
    for cell in board:
        if not cell:
            return False
    board = init_board()
    return True


def if_won():
    global board
    if board[0] == board[1] == board[2] != None or \
            board[3] == board[4] == board[5] != None or \
            board[6] == board[7] == board[8] != None or \
            board[0] == board[3] == board[6] != None or \
            board[1] == board[4] == board[7] != None or \
            board[2] == board[5] == board[8] != None or \
            board[0] == board[4] == board[8] != None or \
            board[6] == board[4] == board[2] != None:
        board = init_board()
        return True
    return False


async def update_board(manager, data):
    ind = int(data['cell']) - 1
    data['init'] = False
    if not board[ind]:
        # cell is empty
        board[ind] = data['player']
        if is_draw():
            data['message'] = "draw"
        elif if_won():
            data['message'] = "won"
        else:
            data['message'] = "move"
    else:
        data['message'] = "choose another one"
    await manager.broadcast(data)
    if data['message'] in ['draw', 'won']:
        manager.connections = []


class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # dealing with incomming connections here
        if len(self.connections) >= 2:
            # denies connection for 3rd player
            await websocket.accept()
            await websocket.close(4000)
        else:
            await websocket.accept()
            # adding the connections to the connection's list
            self.connections.append(websocket)
            if len(self.connections) == 1:
                # the first connected persone plays by X and should wait for a second player
                await websocket.send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Waiting for another player',
                })
            else:
                # the second player plays by O
                await websocket.send_json({
                    'init': True,
                    'player': 'O',
                    'message': '',
                })
                # signals to the first player that the second player has just connected 
                await self.connections[0].send_json({
                    'init': True,
                    'player': 'X',
                    'message': 'Your turn!',
                })

    async def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, data: str):
        # broadcasting data to all connected clients
        for connection in self.connections:
            await connection.send_json(data)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # here we are waiting for an oncomming message from clients
            data = await websocket.receive_text()
            data = json.loads(data)
            # precessing the incomming message
            await update_board(manager, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except:
        pass
