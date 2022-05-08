from zmq.error import ZMQError
from gaia_lib.constants import BUILD_EVENT
from kivy.logger import Logger
import zmq
import threading
import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from gaia_lib import constants as c


class Client:
    def __init__(self, gaia_inst, server_ip):
        self.server_ip = server_ip
        self.req_srvr = f'tcp://{self.server_ip}:{c.PORT}'
        self.pub_srvr = f'tcp://{self.server_ip}:{c.PUB_PORT}'
        self.name = None
        self.players = []
        self.rcvd_p_list = False
        self.gaia_inst = gaia_inst
        self.context = zmq.Context()
        self.req_clnt = self.context.socket(zmq.REQ)
        self.sub_clnt = self.context.socket(zmq.SUB)
        self.sub_clnt.connect(self.pub_srvr)
        self.sub_clnt.setsockopt(zmq.SUBSCRIBE, b'')

    # functions for initialisation

    def connect_to_server(self, name):
        Logger.info('Attempt to connect to game server')
        self.name = name
        self.req_clnt.connect(self.req_srvr)
        msg = (c.PLAYER, self.name)
        result = self.send_req(msg)
        return result
    
    # functions which will be called from the gaia class to send requests

    def send_change_map(self, sector_pos, sector_rot, final=False):
        msg = (c.CHANGE_MAP, sector_pos, sector_rot, final)
        self.send_req(msg)

    def send_rotate(self, sector_name):
        msg = (c.ROTATE_SEC, sector_name)
        self.send_req(msg)

    def send_request_new_setup(self):
        msg = (c.NEW_SETUP,)
        self.send_req(msg)

    def send_switch_to_faction_setup(self):
        self.send_req((c.SWITCH_TO_FACTION_SETUP,))

    def send_faction(self, faction):
        msg = (c.FACTION_PICKED, faction)
        self.send_req(msg)

    def send_booster_pick(self, boo):
        msg = (c.BOOSTER_PICK, boo)
        self.send_req(msg)

    def send_build_mine(self, q, r):        
        msg = (c.BUILD_MINE, q, r)
        self.send_req(msg)

    def send_upgrade(self, q, r, decision):
        msg = (c.BUILDING_UPGRADE, q, r, decision)
        self.send_req(msg)

    def send_passive_income(self):
        msg = (c.PASSIVE_INCOME,)
        self.send_req(msg)

    def send_free_action(self, action_type):
        msg = (c.FREE_ACTION, action_type)
        self.send_req(msg)

    def send_tech_chosen(self, tech, chosen_idx, cover=None):
        # arg2 is either index of chosen research branch or tech tile to cover up if it is an advanced tech
        msg = (c.TECH_CHOSEN, tech, chosen_idx, cover)
        self.send_req(msg)

    def send_action_started(self, action_type):
        msg = (c.ACTION_STARTED, action_type)
        self.send_req(msg)

    def send_action_canceled(self, action_type):
        msg = (c.ACTION_CANCELED, action_type)
        self.send_req(msg)

    def send_level_up(self, track, need_resources):
        msg = (c.LEVEL_UP, track, need_resources)
        self.send_req(msg)

    def send_finish_round(self):
        self.send_req((c.FINISH_ROUND,))

    def send_build_fed(self, fed, num_sats):
        self.send_req((c.BUILD_FED, fed, num_sats))

    def send_fed_marker_choice(self, fed_marker):
        self.send_req((c.FED_MARKER_CHOICE, fed_marker))

    def send_faction_special(self, action_type, args):
        self.send_req((c.FACTION_SPECIAL, action_type, args))

    def send_black_planet(self, q, r):
        self.send_req((c.BLACK_PLANET, q, r))

    def req_sync(self):
        return self.send_req((c.REQ_SYNC,))

    def req_undo(self):
        return self.send_req((c.REQ_UNDO,))

    
    # functions for sending and receiving data from the server
    # both are blocking

    def send_req(self, data):
        retries_left = c.REQUEST_RETRIES
        # add player number to send request so the server knows the sender
        request = (self.gaia_inst.my_pos, data)
        try:
            self.req_clnt.send_pyobj(request) 
            Logger.info(f'request sent to the server, request is: {data}')
            # adapting lazy pirate scheme for reliability
            while True:
                if (self.req_clnt.poll(c.REQUEST_TIMEOUT) & zmq.POLLIN) != 0:
                    reply = self.req_clnt.recv_pyobj()
                    if reply == c.ACKNOWLEDGE:
                        Logger.info('request accepted the server')
                        # expect result of this action to be published
                        return c.ACKNOWLEDGE
                    if reply == c.NAME_IN_USE:
                        # this happens only for initial connection
                        return c.NAME_IN_USE 
                    if len(reply) == 2:
                        if reply[0] == c.DENY:
                            Logger.info('request denied by the server')
                            msg = 'Deine Anfrage wurde vom Server abgelehnt' if reply[1] == c.DENY else reply[1]
                            self.gaia_inst.app_view.error_popup(msg)
                            return c.DENY
                        if reply[0] == c.REQ_SYNC:
                            Logger.info(f'received game state: {reply[1]}')
                            return reply[1]  
                        if reply[0] == c.REJOIN:
                            Logger.info(f'Rejoining game with game state: {reply[1]}')
                            return reply

                    else:
                        Logger.error(f'malformed server response, received: {reply}')
                        continue
                retries_left -= 1
                self.req_clnt.setsockopt(zmq.LINGER, 0)
                self.req_clnt.close()
                if not retries_left:
                    Logger.warning('unable to connect to server')
                    # TODO: react accordingly
                    self.req_clnt = self.context.socket(zmq.REQ)
                    self.req_clnt.connect(self.req_srvr)
                    break
                Logger.warning(f'server did not respond, trying to connect again ({retries_left} left)')
                self.req_clnt = self.context.socket(zmq.REQ)
                self.req_clnt.connect(self.req_srvr)
                Logger.info('resending request')
                self.req_clnt.send_pyobj(request)
        except ZMQError:
            Logger.error('Das hat nicht geklappt')
            self.gaia_inst.app_view.error_popup('Deine Anfrage konnte nicht gesendet\n werden, versuche es nochmal.')
            return c.DENY

    # should be ran as a new thread to not block the whole program
    def receive_data_loop(self):
        while self.gaia_inst.round < 7:
            self.receive_data()

    def receive_data(self):
        data = self.sub_clnt.recv_pyobj()
        # TODO Error handling ???
        # call the function for the received message type
        event = data[0]
        Logger.info(f'receiving data from the server of type [{event}]')
        if(event == c.PLYR_LIST and len(data) == 2):
            if not self.rcvd_p_list:
                self.rcvd_p_list = True
                my_pos = 0
                self.players = data[1]
                for i in range(len(self.players)):
                    if self.players[i] == self.name:
                        my_pos = i
                        break
                self.gaia_inst.recv_player_list(self.players, my_pos)            
        if(event == c.CHANGE_MAP and len(data) == 4):
            self.gaia_inst.recv_change_map(data[1], data[2])
            if(data[3]):
                self.gaia_inst.save_final_map()
        elif(event == c.NEW_SETUP and len(data) == 7):
            self.gaia_inst.recv_setup(boosters=data[1], round_goals=data[2], end_goals=data[3], adv_tech=data[4], tech=data[5], tf_fedm=data[6])
        elif(event == c.SWITCH_TO_FACTION_SETUP and len(data) == 1):
            self.gaia_inst.recv_switch_to_faction_setup()
        elif (event == c.FACTION_PICKED and len(data) == 2):
            self.gaia_inst.recv_faction_picked(data[1])
        elif(event == c.PLAYER_AT_TURN and len(data) == 4):
            self.gaia_inst.recv_player_at_turn(data[1], data[2], data[3])
        elif(event == c.FINISH_ROUND and len(data) == 2):
            self.gaia_inst.recv_end_round(players = data[1])
        elif(event == c.REQ_UNDO and len(data) == 2):
            self.gaia_inst.recv_undo(game_state = data[1])
        else:
            if len(data) >= 2:
                player = data[1]
            else:
                # TODO maybe request a resending of the action?
                pass            
            if data[0] == c.BUILD_EVENT and len(data) == 4:
                self.gaia_inst.recv_action(
                    player,
                    pi_list=data[3],
                    gaia_map=data[2],
                )
            elif data[0] == c.MAP_EVENT and len(data) == 3:
                self.gaia_inst.recv_action(player, gaia_map=data[2])
            elif data[0] == c.P_AND_Q_EVENT and len(data) == 3:
                self.gaia_inst.recv_action(player, used_p_and_q=data[2])
            elif data[0] == c.PLAYER_EVENT and len(data) == 2:
                self.gaia_inst.recv_action(player)
            elif data[0] == c.ADV_EVENT and len(data) == 3:
                self.gaia_inst.recv_action(player, avail_adv=data[2])
            else:
                # TODO maybe request a resending of the action?
                pass
