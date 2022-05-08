import zmq
import threading
import os, sys, time
from kivy.logger import Logger
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from gaia_lib import constants as c


class Server:  

    def __init__(self, gaia_inst, server_ip, skip_join):
        self.context = zmq.Context()
        self.rep_srv = self.context.socket(zmq.REP)
        self.rep_srv.bind(f'tcp://{server_ip}:{c.PORT}')
        self.pub_srv = self.context.socket(zmq.PUB)
        self.pub_srv.bind(f'tcp://{server_ip}:{c.PUB_PORT}')        
        self.players = []
        self.gaia_inst = gaia_inst
        if skip_join:
            for p in self.gaia_inst.players:
                self.players.append(p.name)            
            rd_thread = threading.Thread(target=self.receive_data_loop, daemon=True)
            rd_thread.start()
        else:
            gp_thread = threading.Thread(target=self.get_players, daemon=True)
            gp_thread.start()

    # functions for initialisation

    def get_players(self):
        Logger.info('Waiting for players')
        while len(self.players) < self.gaia_inst.num_players:
            # this process is blocking
            self.receive_data()
        self.send_player_list()
        self.receive_data_loop()

    def send_player_list(self):  
        Logger.info(f'sending list to all players')
        msg = (c.PLYR_LIST, self.players) 
        self.send_to_all(msg)
        # resend after delay to give last joined player enough time to start listening  
        time.sleep(1.5)
        self.send_to_all(msg)

    # functions which will be called from the gaia class to send data

    def send_change_map(self, sector_pos, sector_rot, final=False):
        msg = (c.CHANGE_MAP, sector_pos, sector_rot, final)
        self.send_to_all(msg)

    def send_setup(self, boosters, round_goals, end_goals, adv_tech, tech, tf_fedm):
        msg = (c.NEW_SETUP, boosters, round_goals, end_goals, adv_tech, tech, tf_fedm) 
        self.send_to_all(msg)

    def send_switch_to_faction_setup(self):
        msg=(c.SWITCH_TO_FACTION_SETUP,)
        self.send_to_all(msg)

    def send_faction(self, faction):
        msg = (c.FACTION_PICKED, faction)
        self.send_to_all(msg)

    def send_player_at_turn(self, round, player_at_turn, info = None):
        msg = (c.PLAYER_AT_TURN, round, player_at_turn, info)
        self.send_to_all(msg)


    def send_action(self, player, gaia_map=None, pi_list=None, used_p_and_q=None, avail_adv=None):
        send_list = None
        if gaia_map is not None and pi_list is not None:
            send_list = (c.BUILD_EVENT, player, gaia_map, pi_list)
        elif gaia_map is not None:
            send_list = (c.MAP_EVENT, player, gaia_map)
        elif used_p_and_q is not None:
            send_list = (c.P_AND_Q_EVENT, player, used_p_and_q)
        elif avail_adv is not None:
            send_list = (c.ADV_EVENT, player, avail_adv)
        else:
            send_list = (c.PLAYER_EVENT, player)
        self.send_to_all(send_list)

    def send_finish_round(self, players):
        msg = (c.FINISH_ROUND, players)
        self.send_to_all(msg)

    def send_undo(self, game_state):
        msg = (c.REQ_UNDO, game_state)
        self.send_to_all(msg)


    # functions for sending and receiving data from others
    
    '''send a pyobj via the publisher'''
    def send_to_all(self, data):
        self.pub_srv.send_pyobj(data)
        Logger.info(f'sent to all players this python object: {data}')

    # should be ran as a new thread to not block the whole program
    def receive_data_loop(self):
        while True:
            self.receive_data()

    def receive_data(self):         
        # requests are sent in form (player_pos, (CONSTANT_ACTION_TYPE, additional args ...))       
        request = self.rep_srv.recv_pyobj()
        # TODO error handling ???
        # handle received data
        reply = c.DENY
        req_data = request[1]

        if req_data[0] == c.PLAYER:
            if isinstance(req_data, tuple) and len(req_data) == 2 and isinstance(req_data[1], str):
                if req_data[1] in self.players:
                    if self.gaia_inst.round > -1:
                        reply = (c.REJOIN, self.gaia_inst.get_game_state(rejoin=True))
                    else:
                        reply = c.NAME_IN_USE
                elif len(self.players) < self.gaia_inst.num_players:
                    self.players.append(req_data[1])
                    self.gaia_inst.add_player_to_view(req_data[1])
                    Logger.info(f'{req_data[1]} has joined the game')
                    reply=c.ACKNOWLEDGE
                else:
                    reply=c.DENY
        else:
            Logger.info(f'receiving request from {self.players[request[0]]} of type [{req_data[0]}]')
            reply = self.gaia_inst.handle_request(request[0], req_data)
        if reply == c.ACKNOWLEDGE or reply == c.NAME_IN_USE or reply[0] == c.REQ_SYNC or reply[0] == c.REJOIN:
            self.rep_srv.send_pyobj(reply)
        else:
            # if request is denied, send reason
            msg = (c.DENY, reply)
            self.rep_srv.send_pyobj(msg)


