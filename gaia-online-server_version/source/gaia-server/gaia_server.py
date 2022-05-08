from logging import info
from deepdiff import DeepDiff
import threading
from kivy.uix.label import Label
from kivy.logger import Logger
import random
import copy 
import os, sys
import jsonpickle
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
import network_server
from gaia_lib import maptools
from gaia_lib import faction
import view_server
from gaia_lib import constants as c
import kivy.uix.screenmanager as screenmanager

class Gaia:
    '''This class is responsible for keeping the game status and also.server.ng to the other players to send / receive updates.'''

    # define constants

    def __init__(self):
        self.players = []
        self.boosters, self.round_goals, self.end_goals, self.adv_tech, self.avail_adv, self.avail_boosters, self.tf_fedm = None, None, None, None, None, None, None
        self.tech = [c.TEC_CRE, c.TEC_GAI, c.TEC_KNW, c.TEC_ORE, c.TEC_PIA, c.TEC_POW, c.TEC_QIC, c.TEC_TYP, c.TEC_VPS]
        self.used_p_and_q = set()
        self.choose_tech = False
        self.choose_lvlup = False
        self.choose_fed_marker= False
        self.choose_mine_build = False
        self.choose_black_planet = False
        self.action_started = None
        self.booster_phase = False
        self.app_view = view_server.GaiaServer(self)
        self.server = None  # ths will be the instance of the Network Class
        self.mutex = threading.Lock()
        self.player_at_turn = 0
        self.starting_player = 0
        self.starting_player_set = False
        self.num_players = 0
        self.round = -3 # -3 = map setup, -2 = booster setup, -1 = faction setup # 0 = initial mine placing
        self.initial_index = 0
        self.initial_turn = []
        self.pi_list = []
        self.lvl_5_free = [True] * 6
        self.avail_fed_markers = [3] * len(c.FED_MARKERS)
        self.gaia_map = {} # [Planettype, Owner, Buildingtype, in federation, lantida] # lantida is 0 if not, 1 if not in fed, 2 if in fed
        self.sector_pos = [8, 9, 10, 2, 4, 3, 1,
                           5, 6, 7]  # standard sector positions
        # standard sector rotation angle= i * (-60°)
        self.sector_rot = [0, 0,  0, 0, 0, 0, 0, 0, 0, 0]
        # game log variables
        self.backlog = [None] * c.BACKLOG_LEN
        self.blg_idx = 0
        # from now on all will be done via user input which will be through the app_view
        self.app_view.run()
        Logger.info('game server has been closed')
        # app has been closed so the programm is finished
        sys.exit()

    # function which the gaia class will execute

    def set_up_init_turn(self):
        # remove fed marker put on tf branch from available ones
        self.avail_fed_markers[c.FED_MARKERS.index(self.tf_fedm)] -= 1
        after_list = []
        for i in range(0, len(self.players)):
            if self.players[i].faction_type == c.DER_SCHWARM:
                after_list.append(i)
            else:                
                self.initial_turn.insert(0, i)
                self.initial_turn.append(i)
            if self.players[i].faction_type == c.XENOS:
                after_list.insert(0, i)
        if len(after_list):
            self.initial_turn += after_list
        self.player_at_turn = self.initial_turn[self.initial_index]
        self.round += 1
        self.save_game_state()
        self.send_plat()

    def send_plat(self, info=None):
        self.server.send_player_at_turn(self.round, self.player_at_turn, info)

    def next_player_at_turn(self):
        if self.round == 0:
            if self.initial_index == len(self.initial_turn) - 1:
                self.player_at_turn = 0   
                self.avail_boosters = self.boosters.copy()
                self.round = 1
                self.booster_phase = True              
                self.send_plat((c.NEED_CHOOSE_BOOSTER, self.avail_boosters))
            else:
                self.initial_index += 1
                self.player_at_turn = self.initial_turn[self.initial_index]
                self.send_plat()
        else:
            self.player_at_turn = (self.player_at_turn + 1) % self.num_players
            if self.booster_phase:
                if self.player_at_turn == self.starting_player:
                    # all players have picked a booster
                    # start actual round
                    self.booster_phase = False
                    self.avail_boosters = self.boosters.copy()
                    self.used_p_and_q = set()
                    self.update_resources()
                    self.send_plat(c.NEW_ROUND)
                else:                    
                    self.send_plat((c.NEED_CHOOSE_BOOSTER, self.avail_boosters))
            else:
                while self.players[self.player_at_turn].has_finished:
                    self.player_at_turn = (self.player_at_turn + 1) % self.num_players
                self.send_plat()
                  

    def update_resources(self):
        pass
        #self.app_view.root.get_screen('research_board').update_resources()
    
    def action_possible(self):
        if self.round > 0:
            if self.choose_tech:
                return c.NEED_CHOOSE_TECH
            elif self.choose_lvlup:
                 return c.NEED_CHOOSE_TRACK
            elif self.choose_mine_build:
                 return c.NEED_BUILD_MINE
            elif self.choose_fed_marker:
                 return c.NEED_CHOOSE_FED_MARKER
            elif self.booster_phase:
                return c.NEED_CHOOSE_BOOSTER
            elif self.action_started is not None:
                return self.action_started
            else:
                return c.POSSIBLE
        elif self.round == 0:
            return c.NEED_BUILD_MINE
        return c.NOT_POSSIBLE
                    
    # functions which will be called from the view

    def enter_login(self, ip, num_players):
        self.server = network_server.Server(self, ip, False)
        self.num_players = int(num_players)
        self.players = [None] * self.num_players
        self.pi_list = [0] * self.num_players
        with open('../server_config', 'w') as config:
            config.write(f'num_players: {self.num_players}\n')
            config.write(f'ip: {ip}\n')
        config.close()

    def send_new_map(self, sector_pos):
        self.sector_pos = sector_pos
        self.sector_rot = [0, 0,  0, 0, 0, 0, 0, 0, 0, 0]
        self.app_view.root.get_screen('setup').update_values()
        _thread = threading.Thread(target=self.server.send_change_map, args=[
                                   self.sector_pos, self.sector_rot])
        _thread.start()
      

    def send_final_map(self):
        self.server.send_change_map(self.sector_pos, self.sector_rot, True) 

    def handle_pick_random_setup(self):
        self.boosters = random.sample([c.BOO_GAI, c.BOO_KNW, c.BOO_LAB, c.BOO_MIN, c.BOO_NAV,
                                       c.BOO_PIA, c.BOO_PWT, c.BOO_QIC, c.BOO_TER, c.BOO_TRS], self.num_players + 3)
        self.round_goals = random.sample(
            [c.RND_FED, c.RND_GAI3, c.RND_GAI4, c.RND_MIN, c.RND_PIA, c.RND_PIA, c.RND_STP, c.RND_TER, c.RND_TRS3, c.RND_TRS4], 6)
        self.end_goals = random.sample(
            [c.FIN_BLD, c.FIN_FED, c.FIN_GAI, c.FIN_SAT, c.FIN_SEC, c.FIN_TYP], 2)
        self.adv_tech = random.sample([c.ADV_FEDP, c.ADV_FEDV, c.ADV_GAI, c.ADV_KNW, c.ADV_LAB, c.ADV_MINB, c.ADV_MINV, c.ADV_ORE, c.ADV_QIC, c.ADV_SECO, c.ADV_SECV, c.ADV_STP, c.ADV_TRSB, c.ADV_TRSV, c.ADV_TYP], 6)
        self.avail_adv = set(self.adv_tech)
        self.tf_fedm = random.sample(c.FED_MARKERS, 1)[0]
        random.shuffle(self.tech)  
        _thread = threading.Thread(target=self.server.send_setup, args=[self.boosters, self.round_goals, self.end_goals, self.adv_tech, self.tech, self.tf_fedm])
        _thread.start()
        self.app_view.root.get_screen('setup').update_values()

    def server_change_setup(self, new_boo, new_rnd, new_end):
        if(len(new_boo) == (self.num_players + 3) and len(new_rnd) == 6 and len(new_end) == 2):
            verify_values = True
            for boo in new_boo:
                if not boo in [c.BOO_GAI, c.BOO_KNW, c.BOO_LAB, c.BOO_MIN, c.BOO_NAV,
                                       c.BOO_PIA, c.BOO_PWT, c.BOO_QIC, c.BOO_TER, c.BOO_TRS]:
                    verify_values = False
                    break
            for rnd in new_rnd:
                if not rnd in [c.RND_FED, c.RND_GAI3, c.RND_GAI4, c.RND_MIN, c.RND_PIA, c.RND_STP, c.RND_TER, c.RND_TRS3, c.RND_TRS4]:
                    verify_values = False
                    break
            for end in new_end:
                if not end in [c.FIN_BLD, c.FIN_FED, c.FIN_GAI, c.FIN_SAT, c.FIN_SEC, c.FIN_TYP]:
                    verify_values = False
                    break
            if verify_values:
                self.boosters = new_boo
                self.round_goals = new_rnd
                self.end_goals = new_end
                self.server.send_setup(self.boosters, self.round_goals, self.end_goals, self.adv_tech, self.tech)
                return c.ACKNOWLEDGE                          
        self.app_view.root.get_screen('setup').update_values()
        return c.DENY
    
    

    def handle_choose_faction(self, faction_value):
        # check if faction value is valid
        if not faction_value in faction.FACTIONS:
            return c.DENY
        # and not in use
        for player in self.players:
            if(player and faction_value == player.faction_type):
                return c.DENY
        # create faction of correct class
        player = faction.FACTIONS[faction_value](self.server.players[self.player_at_turn], self.player_at_turn)
        self.players[self.player_at_turn] = player
        self.app_view.root.get_screen('setup').update_values()
        self.server.send_faction(player)
        if self.player_at_turn == 0:
            self.set_up_init_turn()
            self.update_resources()
            self.app_view.switch_screen('game')
        else:
            self.player_at_turn -= 1
            self.send_plat()
        return c.ACKNOWLEDGE
                
    def others_passive_income(self, q, r):
        pi_list = [0] * self.num_players
        for i in range(self.num_players):
            if i == self.player_at_turn:
                continue
            else:
                pi_list[i] = self.players[i].passive_income_possible(q, r, self.gaia_map.items())
        return pi_list

    def handle_build_mine(self, q, r):
        result = self.action_possible()
        if self.round == 0 or self.choose_mine_build or (result == c.POSSIBLE):
            result = self.players[self.player_at_turn].build_mine_possible(q, r, self.gaia_map, initial=(self.round == 0))
            if result == c.POSSIBLE:            
                thread = threading.Thread(target=self.do_build_mine, args=[q, r])
                thread.start()
                return c.ACKNOWLEDGE         
        return result

    def do_build_mine(self, q, r):
        self.save_game_state()
        self.players[self.player_at_turn].build_mine(q, r, self.gaia_map, initial=(self.round == 0))
        self.choose_mine_build = False
        self.action_started = None
        # check if mine was built and not gaiaformer
        if self.gaia_map[(q,r)][2] == c.MINE or self.gaia_map[(q,r)][4] == 1:
            self.pi_list = [0] * self.num_players
            if self.round > 0:
                # add mine to fed if existing
                self.neighbors_in_fed(q, r)
                self.pi_list = self.others_passive_income(q, r)
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map, pi_list=self.pi_list)
        else:
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
        self.update_resources()
        self.next_player_at_turn()

    def neighbors_in_fed(self, q, r, checked=None):
        '''If necessary: Add this planet and all direct and indirect neighbors to fed.'''
        if checked is not None:
            checked.append((q, r))
        else:
            checked = [(q,r)]
        output = False
        for neigh_q in range(q - 1, q + 2):
            for neigh_r in range(r - 1, r + 2):
                if maptools.hex_distance(q, r, neigh_q, neigh_r) == 1:
                    neigh_pos = (neigh_q, neigh_r)
                    if neigh_pos in self.gaia_map:
                        if (self.gaia_map[neigh_pos][1] == self.player_at_turn 
                         and self.gaia_map[neigh_pos][3]):
                            if self.gaia_map[(q,r)][1] == self.player_at_turn:
                                self.gaia_map[(q,r)][3] = True
                            else: # Lantida mine was built
                                self.gaia_map[(q,r)][4] = 2
                            output = True
                        elif (self.players[self.player_at_turn].faction_type == c.LANTIDA and 
                        self.gaia_map[neigh_pos][4] == 2):
                            if self.gaia_map[(q,r)][1] == self.player_at_turn:
                                self.gaia_map[(q,r)][3] = True
                            else: # Lantida mine was built
                                self.gaia_map[(q,r)][4] = 2
                            output = True
        if output:  
            for neigh_q in range(q - 1, q + 2):
                for neigh_r in range(r - 1, r + 2):
                    if maptools.hex_distance(q, r, neigh_q, neigh_r) == 1:
                        neigh_pos = (neigh_q, neigh_r)
                        if (neigh_pos not in checked and
                            neigh_pos in self.gaia_map and
                            (self.gaia_map[neigh_pos][1] == self.player_at_turn or
                            (self.players[self.player_at_turn].faction_type == c.LANTIDA and 
                            self.gaia_map[neigh_pos][4]))
                            ):
                            checked = self.neighbors_in_fed(neigh_q, neigh_r, checked)
        return checked 

    def handle_upgrade_building(self, q, r, decision = None):
        result = self.action_possible()
        if result == c.POSSIBLE: 
            if self.gaia_map[(q,r)][1] != self.player_at_turn:
                if self.players[self.player_at_turn].faction_type == c.LANTIDA:
                    # Lantida mine build on other planet
                    return self.handle_build_mine(q, r)
                else:
                    return c.NOT_OWNED_BY_YOU
            else:
                result = self.players[self.player_at_turn].upgrade_building_possible(q,r, self.gaia_map, decision=decision)
                if result in [c.POSSIBLE, c.POSSIBLE_CHOOSE_TECH]:                   
                    thread = threading.Thread(target=self.do_upgrade_building, args=[q, r, decision])
                    thread.start()
                    return c.ACKNOWLEDGE
                else:
                    return result
        else:
            return result

    def do_upgrade_building(self, q, r, decision):
        self.save_game_state()
        result = self.players[self.player_at_turn].upgrade_building_possible(q,r, self.gaia_map, decision=decision)
        if result == c.POSSIBLE_CHOOSE_TECH:
            self.choose_tech = True 
        self.players[self.player_at_turn].upgrade_building(q, r, self.gaia_map, decision)
        self.pi_list = self.others_passive_income(q,r)
        self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map, pi_list=self.pi_list)
        self.update_resources()
        # check if tech needs to be chosen
        if not self.choose_tech:
            self.next_player_at_turn()
        else:
            self.send_plat(c.NEED_CHOOSE_TECH)
            
    def handle_passive_income(self, player_pos):
        if self.pi_list[player_pos] > 0:            
            thread = threading.Thread(target=self.do_passive_income, args=[player_pos])
            thread.start()
            return c.ACKNOWLEDGE
        else:
            return c.NOT_POSSIBLE

    def do_passive_income(self, player_pos):
        self.save_game_state()
        self.players[player_pos].execute_passive_income(self.pi_list[player_pos])
        self.pi_list[player_pos] = 0
        self.server.send_action(self.players[player_pos])
        self.update_resources()

    def handle_booster_pick(self, boo):
        if boo in self.avail_boosters and self.booster_phase:          
            thread = threading.Thread(target=self.do_booster_pick, args=[boo])
            thread.start()
            return c.ACKNOWLEDGE            
        else:
            return c.NOT_POSSIBLE

    def do_booster_pick(self, boo):
        self.save_game_state()
        self.players[self.player_at_turn].current_booster = boo
        # perform income and gaia phase for the player who has chosen a booster
        self.players[self.player_at_turn].income_phase(self.round_goals[self.round - 1])                
        self.players[self.player_at_turn].gaia_phase()
        self.avail_boosters.remove(boo)
        self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
        if self.players[self.player_at_turn].faction_type == c.TERRANER and self.players[self.player_at_turn].gaia_phase_action_possible():
            self.send_plat(info=c.TERRANER_PLI)
        elif self.players[self.player_at_turn].faction_type == c.ITAR and self.players[self.player_at_turn].gaia_phase_action_possible():
            self.send_plat(info=c.ITAR_PLI)
        else:
            self.next_player_at_turn()
        self.update_resources()



    def handle_free_action(self, player_pos, action_type):
        if self.round > 0 and self.round < 7:
            if self.booster_phase:
                if (self.players[player_pos].faction_type == c.TERRANER and
                    action_type in [c.TER_TO_GLD, c.TER_TO_KNW, c.TER_TO_ORE, c.TER_TO_QIC]
                    ):
                    result = self.players[player_pos].gaia_free_action_possible(action_type)
                    if result == c.POSSIBLE:
                        thread = threading.Thread(target=self.do_free_action, args=[player_pos, action_type])
                        thread.start()
                        return c.ACKNOWLEDGE
                    return result
                else:
                    return c.NOT_POSSIBLE
            else:
                result = self.players[player_pos].free_action_possible(action_type)
                if result == c.POSSIBLE:
                    thread = threading.Thread(target=self.do_free_action, args=[player_pos, action_type])
                    thread.start()
                    return c.ACKNOWLEDGE
                return result
        else:
            return c.NOT_POSSIBLE

    def do_free_action(self, player_pos, action_type):
        self.save_game_state()
        if action_type in [c.TER_TO_GLD, c.TER_TO_KNW, c.TER_TO_ORE, c.TER_TO_QIC]:
            self.players[player_pos].execute_gaia_free_action(action_type)
            self.server.send_action(self.players[player_pos])
            if not self.players[player_pos].gaia_phase_action_possible():
                self.next_player_at_turn()
        else:
            self.players[player_pos].execute_free_action(action_type)
            self.server.send_action(self.players[player_pos])
        self.update_resources()    
  

    def handle_tech_chosen(self, tech, chosen_idx, cover):
        result = self.action_possible()
        if result == c.NEED_CHOOSE_TECH:            
            if tech in [
                    c.TECH_1,
                    c.TECH_2,
                    c.TECH_3,
                    c.TECH_4,
                    c.TECH_5,
                    c.TECH_6,
                    c.TECH_7,
                    c.TECH_8,
                    c.TECH_9,
                ]:
                tech_idx = int(tech[-1]) - 1
                result = self.players[self.player_at_turn].tech_tile_possible(
                        self.tech[tech_idx], index=chosen_idx, lvl_5_free=self.lvl_5_free
                    )
                if result in [c.POSSIBLE, c.POSSIBLE_NO_LVL_UP]:
                    thread = threading.Thread(
                        target=self.do_tech_chosen, args=[self.tech[tech_idx], chosen_idx, cover, None]
                    )
                    thread.start()
                    return c.ACKNOWLEDGE
                else:
                    return result
            elif tech in [
                c.ADV_TECH_1,
                c.ADV_TECH_2,
                c.ADV_TECH_3,
                c.ADV_TECH_4,
                c.ADV_TECH_5,
                c.ADV_TECH_6,
            ]:
                tech_idx = int(tech[-1]) - 1
                result = self.players[self.player_at_turn].tech_tile_possible(
                        self.adv_tech[tech_idx], avail_adv=self.avail_adv, adv_idx=tech_idx, cover=cover, index=chosen_idx, lvl_5_free=self.lvl_5_free
                    )
                if result in [c.POSSIBLE, c.POSSIBLE_NO_LVL_UP]:
                    thread = threading.Thread(
                        target=self.do_tech_chosen, args=[self.adv_tech[tech_idx], chosen_idx, cover, tech_idx]
                    )
                    thread.start()
                    return c.ACKNOWLEDGE
                else:
                    return result
            
        else:
            return c.DENY

    def do_tech_chosen(self, tech, chosen_idx, cover, adv_idx):
        self.save_game_state()
        # execute level up if possible
        result = self.players[self.player_at_turn].tech_tile_possible(tech, self.avail_adv, adv_idx=adv_idx, index=chosen_idx, cover=cover, lvl_5_free=self.lvl_5_free)
        if not result == c.POSSIBLE_NO_LVL_UP:   
            self.players[self.player_at_turn].execute_level_up(chosen_idx, self.gaia_map, need_resources=False) 
        # execute tech tile
        self.players[self.player_at_turn].execute_tech_tile(self.gaia_map, tech, cover=cover)       
        self.update_resources()
        self.action_started = None
        self.choose_tech = False
        self.choose_lvlup = False 
        if tech in self.avail_adv:            
            self.avail_adv.discard(tech)       
            self.server.send_action(self.players[self.player_at_turn], avail_adv=self.avail_adv)
        else:
            self.server.send_action(self.players[self.player_at_turn])
        if not result == c.POSSIBLE_NO_LVL_UP and chosen_idx == 1 and self.players[self.player_at_turn].research_branches[1] == 5:
            # player needs to choose where to place the black planet
            self.choose_black_planet = True
            self.send_plat(info=c.NEED_CHOOSE_BLACK_PLANET)
        else:
            self.next_player_at_turn()

    def handle_level_up(self, track, need_resources):
        result = self.action_possible()
        if (self.choose_lvlup or result == c.POSSIBLE):
            if track in [
                    c.TRACK_1,
                    c.TRACK_2,
                    c.TRACK_3,
                    c.TRACK_4,
                    c.TRACK_5,
                    c.TRACK_6,
                ]:
                # check if correctly requested without resource need               
                branch = int(track[-1]) - 1
                if (not need_resources) and (not self.choose_lvlup):
                        return c.DENY     
                if self.action_started == c.MAD_ANDROIDS_SPECIAL:
                    result = self.players[self.player_at_turn].free_level_up_possible(branch)
                    if not result == c.POSSIBLE:
                        return result
                # lvlup for 4 knowledge or free if choose_lvlup is True
                result = self.players[self.player_at_turn].level_up_possible(
                    branch, self.lvl_5_free, need_resources=(not self.choose_lvlup)
                )
                if result in [c.POSSIBLE_TURN_MARKER_GRAY, c.POSSIBLE]:
                    thread = threading.Thread(
                            target=self.do_level_up, args=[branch,(not self.choose_lvlup)]
                        )
                    thread.start()
                    return c.ACKNOWLEDGE
        return result

    def do_level_up(self, branch, need_resources):
        self.save_game_state()
        self.choose_lvlup = False
        self.action_started = None
        self.players[self.player_at_turn].execute_level_up(branch, self.gaia_map, need_resources=need_resources)
        if self.players[self.player_at_turn].research_branches[branch] == 5:
            self.lvl_5_free[branch] = False
            if branch == 0:
                self.players[self.player_at_turn].add_fed_marker(self.tf_fedm)
            elif branch == 1:
                # player needs to choose where to place the black planet
                self.choose_black_planet = True
                self.server.send_action(self.players[self.player_at_turn])
                self.send_plat(info=c.NEED_CHOOSE_BLACK_PLANET)
                self.update_resources()
                return
        self.server.send_action(self.players[self.player_at_turn])
        self.next_player_at_turn()
        self.update_resources()

    def handle_action_started(self, action_type):
        result = self.action_possible()
        if result == c.POSSIBLE:
            if self.round > 0: 
                # p and q actions               
                if action_type in [c.PUB_2_GLD, c.PUB_2_KNW_2, c.PUB_2_KNW_3, c.PUB_2_ORE, c.PUB_2_PWS, c.PUB_2_TRF_1, c.PUB_2_TRF_2, c.QIC_2_FED, c.QIC_2_TEC, c.QIC_2_VPS]:
                    if self.action_started is None:
                        if action_type not in self.used_p_and_q:
                            result = self.players[self.player_at_turn].p_and_q_possible(action_type)
                            if result == c.POSSIBLE:                              
                                thread = threading.Thread(target =self.do_action_started,args=[action_type])
                                thread.start()
                                return c.ACKNOWLEDGE                                
                        else:
                            return c.ALREADY_USED
                # booster action
                elif action_type in [c.BOO_TER, c.BOO_NAV]:
                    result = self.players[self.player_at_turn].booster_action_possible(action_type)
                    if result == c.POSSIBLE:                                                    
                        thread = threading.Thread(target =self.do_action_started,args=[action_type])
                        thread.start()
                        return c.ACKNOWLEDGE
                # tech action
                elif action_type in [c.TEC_POW, c.ADV_QIC, c.ADV_ORE, c.ADV_KNW]:
                    result = self.players[self.player_at_turn].tech_action_possible(action_type)
                    if result == c.POSSIBLE:                                                    
                        thread = threading.Thread(target =self.do_action_started,args=[action_type])
                        thread.start()
                        return c.ACKNOWLEDGE
                # right ac QIC action
                elif action_type == c.ORANGE_QIC:
                    result = self.players[self.player_at_turn].ac_action_possible()
                    if result == c.POSSIBLE:                                              
                        thread = threading.Thread(target =self.do_action_started,args=[action_type])
                        thread.start()
                        return c.ACKNOWLEDGE 
                # faction specific actions
                elif action_type in [c.AMBAS_PLI, c.FIRAKS_PLI, c.MAD_ANDROIDS_SPECIAL, c.DER_SCHWARM_PLI]:
                    if (isinstance(self.players[self.player_at_turn], faction.Ambas) or 
                         isinstance(self.players[self.player_at_turn], faction.Firaks)or 
                         isinstance(self.players[self.player_at_turn], faction.MadAndroids)or 
                         isinstance(self.players[self.player_at_turn], faction.DerSchwarm)):
                        result = self.players[self.player_at_turn].pli_orange_possible()
                        if result == c.POSSIBLE:
                            thread = threading.Thread(target =self.do_action_started,args=[action_type])
                            thread.start()
                            return c.ACKNOWLEDGE
        elif (result == c.NEED_CHOOSE_BOOSTER and
            action_type == c.ITAR_PLI and
            self.players[self.player_at_turn].faction_type == c.ITAR and
            self.players[self.player_at_turn].gaia_phase_action_possible
            ): 
            thread = threading.Thread(target =self.do_action_started,args=[action_type])
            thread.start()
            return c.ACKNOWLEDGE            
        return result

    def do_action_started(self, action_type):
        self.save_game_state()
        if action_type in [c.PUB_2_GLD, c.PUB_2_KNW_2, c.PUB_2_KNW_3, c.PUB_2_ORE, c.PUB_2_PWS, c.PUB_2_TRF_1, c.PUB_2_TRF_2, c.QIC_2_FED, c.QIC_2_TEC, c.QIC_2_VPS]:
            self.used_p_and_q.add(action_type)
            self.players[self.player_at_turn].execute_p_and_q(self.gaia_map, action_type)
            self.server.send_action(self.players[self.player_at_turn], used_p_and_q=self.used_p_and_q)
            if action_type in [c.PUB_2_TRF_1, c.PUB_2_TRF_2]:
                self.action_started = action_type
                self.choose_mine_build = True
            elif action_type == c.QIC_2_TEC:
                self.action_started = action_type
                self.choose_tech = True
            elif action_type == c.QIC_2_FED:
                self.action_started = action_type
                self.choose_fed_marker= True
            else:
                self.next_player_at_turn() 
        elif action_type in [c.BOO_TER, c.BOO_NAV]:
            self.choose_mine_build = True
            self.action_started = action_type
            self.players[self.player_at_turn].execute_booster_action()
            self.server.send_action(self.players[self.player_at_turn])
        elif action_type in [c.TEC_POW, c.ADV_QIC, c.ADV_ORE, c.ADV_KNW]:
            self.players[self.player_at_turn].execute_tech_action(action_type)
            self.server.send_action(self.players[self.player_at_turn])
            self.next_player_at_turn()
        elif action_type == c.ORANGE_QIC:
            self.players[self.player_at_turn].execute_ac_action()
            self.server.send_action(self.players[self.player_at_turn])
            self.next_player_at_turn()
        elif action_type in [c.AMBAS_PLI, c.FIRAKS_PLI, c.MAD_ANDROIDS_SPECIAL, c.DER_SCHWARM_PLI]:
            if action_type == c.MAD_ANDROIDS_SPECIAL:
                self.choose_lvlup = True
            self.action_started = action_type
            self.players[self.player_at_turn].execute_start_faction_action()
            self.server.send_action(self.players[self.player_at_turn])
        elif action_type == c.ITAR_PLI:
            self.action_started = action_type
            self.choose_tech = True
            self.players[self.player_at_turn].execute_start_gaia_phase_action()
            self.server.send_action(self.players[self.player_at_turn])
        self.update_resources() 

    def handle_action_canceled(self, action_type):
        if self.action_started is not None:
            if self.action_started == action_type:
                thread = threading.Thread(target=self.do_action_canceled, args=[action_type])
                thread.start()
                return c.ACKNOWLEDGE
        return c.NOT_POSSIBLE
        
    def do_action_canceled(self, action_type):
        self.save_game_state()
        self.players[self.player_at_turn].execute_cancel_action(action_type)
        # remove item from used if it was there (nothing happens if it isnt in set)
        self.used_p_and_q.discard(action_type) 
        self.action_started = None
        if action_type == c.QIC_2_FED:
            self.choose_fed_marker= False 
        if action_type == c.MAD_ANDROIDS_SPECIAL:
            self.choose_lvlup = False             
        elif action_type in [c.QIC_2_TEC, c.ITAR_PLI]:
            self.choose_tech = False 
        elif action_type in [c.BOO_TER, c.BOO_NAV, c.PUB_2_TRF_1, c.PUB_2_TRF_2]:
            self.choose_mine_build = False
        self.server.send_action(self.players[self.player_at_turn], used_p_and_q=self.used_p_and_q)

    def get_connected_fed(self, pos, fed, sats, traversed):
        traversed.add(pos)
        q, r = pos
        for new_q in range(q - 1, q + 2):
            for new_r in range(r - 1, r + 2):
                if maptools.hex_distance(q, r, new_q, new_r) == 1:
                    if (((new_q, new_r) not in traversed) and
                        ((new_q, new_r) in fed or 
                        (new_q, new_r) in sats) 
                        ):
                        traversed = self.get_connected_fed((new_q, new_r), fed, sats, traversed)
        return traversed
 
    def handle_build_fed(self, fed, sats):
        if isinstance(fed, dict) and isinstance(sats, set):
                # check if planets are possible for fed building
            for pos in fed:
                if pos not in self.gaia_map and not (
                    self.players[self.player_at_turn].faction_type == c.DER_SCHWARM and 
                    pos in self.players[self.player_at_turn].ivit_sats
                    ):
                    return c.FED_IMPOSSIBLE
            for planet in fed.values():
                if (not planet[1] == self.player_at_turn):
                    if (self.players[self.player_at_turn].faction_type == c.LANTIDA and
                        planet[4] == 1):
                        continue
                    return c.FED_IMPOSSIBLE
                elif planet[3] and not self.players[self.player_at_turn].faction_type == c.DER_SCHWARM:
                    return c.FED_IMPOSSIBLE
            result = self.players[self.player_at_turn].get_fed_possible(self.gaia_map, submap=fed, num_sats=len(sats))
            if result == c.POSSIBLE:
                # calculate satelites necessary and check if correct length is given
                # TODO @Johann possibly?
                num_sats = 100 
                if len(sats) > num_sats:
                    return c.NUM_SATS_TOO_HIGH
                else:
                    # check if fed is continuous                        
                    pos = list(fed.keys())[0]
                    if self.players[self.player_at_turn].faction_type == c.DER_SCHWARM:
                        all_sats = sats.copy()
                        all_sats.update(self.players[self.player_at_turn].satellites)
                        traversed = self.get_connected_fed(pos, fed, all_sats, set())
                        if len(traversed) < (len(fed) + len(all_sats)):
                            return c.FED_NOT_CONNECTED
                    else:
                        traversed = self.get_connected_fed(pos, fed, sats, set())                
                        if len(traversed) < (len(fed) + len(sats)):
                            return c.FED_NOT_CONNECTED
                    # if we get here, fed is possible
                    thread = threading.Thread(target=self.do_build_fed, args=[fed, sats])
                    thread.start()
                    return c.ACKNOWLEDGE
            return result

    def do_build_fed(self, fed, sats):
        self.save_game_state()
        if isinstance(fed, dict):
            for pos in fed:
                if pos in self.gaia_map: # ivit sats are in fed but not in gaia_map
                    if self.gaia_map[pos][1] == self.player_at_turn:
                        self.gaia_map[pos][3] = True
                    elif (self.players[self.player_at_turn].faction_type == c.LANTIDA and
                        self.gaia_map[pos][4] == 1
                        ):
                        self.gaia_map[pos][4] = 2                
            self.players[self.player_at_turn].execute_build_fed(sats)
            self.choose_fed_marker = True
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
            self.server.send_player_at_turn(self.round, self.player_at_turn, info=(c.NEED_CHOOSE_FED_MARKER, self.avail_fed_markers))

    def handle_fed_marker_choice(self, fed_marker):
        result = c.NOT_POSSIBLE
        if self.choose_fed_marker:
            if self.action_started == c.QIC_2_FED:
                if fed_marker in self.players[self.player_at_turn].fed_markers:
                    thread = threading.Thread(target=self.do_fed_marker_choice, args=[fed_marker, False])
                    thread.start()
                    result = c.ACKNOWLEDGE
            elif fed_marker in c.FED_MARKERS and (self.avail_fed_markers[c.FED_MARKERS.index(fed_marker)] > 0):            
                    thread = threading.Thread(target=self.do_fed_marker_choice, args=[fed_marker, True])
                    thread.start()
                    result = c.ACKNOWLEDGE
        return result

    def do_fed_marker_choice(self, fed_marker, new_marker):
        self.save_game_state()
        self.action_started = None
        self.choose_fed_marker = False
        if new_marker:
            self.avail_fed_markers[c.FED_MARKERS.index(fed_marker)] -= 1
            self.players[self.player_at_turn].add_fed_marker(fed_marker)
        else:
            self.players[self.player_at_turn].execute_fed_marker(fed_marker)
        self.server.send_action(self.players[self.player_at_turn])
        self.next_player_at_turn()

    def handle_faction_special(self, action_type, args):
        result = self.action_possible()
        p = self.players[self.player_at_turn]
        # check if action_possible returns the action_type of the requested action
        if result == action_type:
            # AMBAS pli change
            if action_type == c.AMBAS_PLI:
                if isinstance(p, faction.Ambas):
                    if isinstance(args, tuple) and len(args) == 2:
                        (q,r) = args
                        result = p.pli_change_possible(self.gaia_map, q, r)
                        if result == c.POSSIBLE:          
                            thread = threading.Thread(target=self.do_faction_special, args=[action_type, args])
                            thread.start()
                            result = c.ACKNOWLEDGE
                        else:
                            return result
            elif action_type == c.FIRAKS_PLI:
                if isinstance(p, faction.Firaks):
                    if isinstance(args, tuple) and len(args) == 2:
                        (q,r) = args
                        result = p.lab_downgrade_possible(self.gaia_map, q, r)
                        if result == c.POSSIBLE:          
                            thread = threading.Thread(target=self.do_faction_special, args=[action_type, args])
                            thread.start()
                            result = c.ACKNOWLEDGE
                        else:
                            return result
            elif action_type == c.DER_SCHWARM_PLI:
                if isinstance(p, faction.DerSchwarm):
                    if isinstance(args, tuple) and len(args) == 2:
                        (q,r) = args
                        result = p.ivit_sat_possible(q, r, self.gaia_map)
                        if result == c.POSSIBLE:          
                            thread = threading.Thread(target=self.do_faction_special, args=[action_type, args])
                            thread.start()
                            result = c.ACKNOWLEDGE
                        else:
                            return result
        return result

    def do_faction_special(self, action_type, args):
        self.save_game_state()
        # AMBAS pli change
        if action_type == c.AMBAS_PLI:
            (q,r) = args
            self.players[self.player_at_turn].execute_pli_change(self.gaia_map, q, r)
            self.action_started = None
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
            self.next_player_at_turn()
        # FIRAKS lab downgrade
        elif action_type == c.FIRAKS_PLI:
            (q,r) = args
            self.players[self.player_at_turn].execute_lab_downgrade(self.gaia_map, q, r)
            self.action_started = None
            self.choose_lvlup = True
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
            self.send_plat(c.NEED_CHOOSE_TRACK)
        # SCHWARM place ivit sat
        elif action_type == c.DER_SCHWARM_PLI:
            (q,r) = args
            self.players[self.player_at_turn].execute_ivit_sat(q, r)
            self.action_started = None
            self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
            self.next_player_at_turn()


    def handle_black_planet(self, q, r):
        result = c.NOT_POSSIBLE
        if self.choose_black_planet:
            result = self.players[self.player_at_turn].black_planet_possible(self.gaia_map, q, r)
            if result == c.POSSIBLE:
                thread = threading.Thread(target=self.do_black_planet, args=[q,r])
                thread.start()
                return c.ACKNOWLEDGE
        return result

    def do_black_planet(self, q, r):
        self.save_game_state()
        self.gaia_map[(q,r)] = [c.BLACK_PLANET, self.player_at_turn, c.MINE, False, 0]
        self.neighbors_in_fed(q,r)
        self.choose_black_planet = False
        self.server.send_action(self.players[self.player_at_turn], gaia_map=self.gaia_map)
        self.next_player_at_turn()
   

    def handle_finish_round(self):
        result = self.action_possible()
        if result == c.POSSIBLE:
            thread = threading.Thread(target=self.do_finish_round)
            thread.start()
            return c.ACKNOWLEDGE
        elif (self.booster_phase and self.players[self.player_at_turn].faction_type == c.ITAR):
            thread = threading.Thread(target=self.do_finish_gaia)
            thread.start()
            return c.ACKNOWLEDGE
        return result            

    def do_finish_gaia(self):
        self.save_game_state()
        if self.action_started == c.ITAR_PLI:
            self.action_started = None
            self.choose_tech = False
            self.players[self.player_at_turn].execute_cancel_action(c.ITAR_PLI)
        self.players[self.player_at_turn].finish_gaia_phase()
        self.server.send_action(self.players[self.player_at_turn])
        self.next_player_at_turn()

    def do_finish_round(self):
        self.save_game_state()
        self.players[self.player_at_turn].has_finished = True
        if not self.starting_player_set:
            self.starting_player = self.player_at_turn
            self.starting_player_set = True
        p_fin = 0
        for p in self.players:
            if p.has_finished:
                p_fin += 1
        if p_fin == self.num_players:
            for p in self.players:
                p.end_round_phase(self.gaia_map)  
            if self.round < 6:            
                self.round += 1
                self.booster_phase = True
                self.starting_player_set = False
                self.player_at_turn = self.starting_player
                self.avail_boosters = self.boosters.copy()
                self.server.send_finish_round(self.players)
                # change transdim with gaiaformer planet type         
                for planet in self.gaia_map.values():
                    if planet[0] == c.TRANSDIM_GFM:
                        planet[0] = c.GAIAFORMED
                self.send_plat((c.NEED_CHOOSE_BOOSTER, self.avail_boosters))
            else:          
                self.round += 1
                self.player_at_turn = -1
                self.finish_game()
        else:
            self.server.send_action(self.players[self.player_at_turn])
            self.next_player_at_turn()
        self.update_resources()

  

    def finish_game(self):
        for p in self.players:
            p.finish_game_phase()
        # add end goal scores
        for end_goal in self.end_goals:
            # gather and sort end goal scores
            scores = [self.players[0].get_goal_score(self.gaia_map, end_goal)]
            pos_list = [0]
            for pos in range(1, self.num_players):
                score = self.players[pos].get_goal_score(self.gaia_map, end_goal)
                for i in range(len(scores)):
                    if score > scores[i]:
                        scores.insert(i, score)
                        pos_list.insert(i, pos)
                    elif i == (len(scores) - 1):
                        scores.append(score)
                        pos_list.append(pos)
            # for testing purposes add a second player
            if self.num_players == 1:
                scores.append(0)
                pos_list.append(-2)
            # add neutral third for ranks with 2 players
            if self.num_players < 3:
                neutral_third = 0
                if end_goal == c.FIN_BLD:
                    neutral_third = 11
                elif end_goal == c.FIN_FED:
                    neutral_third = 10
                elif end_goal == c.FIN_GAI:
                    neutral_third = 4
                elif end_goal == c.FIN_SAT:
                    neutral_third = 8
                elif end_goal == c.FIN_SEC:
                    neutral_third = 6
                elif end_goal == c.FIN_TYP:
                    neutral_third = 5
                for i in range(2):
                    if neutral_third > scores[i]:
                        scores.insert(i, neutral_third)
                        pos_list.insert(i, -1)
                        break
                    elif i == (len(scores) - 1):
                        scores.append(neutral_third)
                        pos_list.append(-1)
            # calculate vcp gain for all possible score rankings
            if scores[0] > scores[1]:
                # not shared first place
                if pos_list[0] > -1:
                    self.players[pos_list[0]].vcp += 18
                    self.players[pos_list[0]].end_details[end_goal] = 18
                if scores[1] > scores[2]:
                    # not shared second place
                    if pos_list[1] > -1:
                        self.players[pos_list[1]].vcp += 12
                        self.players[pos_list[1]].end_details[end_goal] = 12
                    if self.num_players < 4 or score[2] > scores[3]:
                        # not shared third place
                        if pos_list[2] > -1:
                            self.players[pos_list[2]].vcp += 6
                            self.players[pos_list[2]].end_details[end_goal] = 6
                    else:
                        # two players share third place
                        for i in range(2,4):
                            self.players[pos_list[i]].vcp += 3
                            self.players[pos_list[i]].end_details[end_goal] = 3
                elif self.num_players < 4 or scores[2] > scores[3]:
                    # two players share second place
                    for i in range(1,3):
                        if pos_list[i] > -1:
                            self.players[pos_list[i]].vcp += 9
                            self.players[pos_list[i]].end_details[end_goal] = 9
                else:
                    # three players share second place
                    for i in range(1,4):
                        self.players[pos_list[i]].vcp += 6
                        self.players[pos_list[i]].end_details[end_goal] = 6
            elif scores[1] > scores[2]:
                for i in range(2):
                    if pos_list[i] > -1:
                        self.players[pos_list[i]].vcp += 15
                        self.players[pos_list[i]].end_details[end_goal] = 15
                if self.num_players < 4 or score[2] > scores[3]:
                    # not shared third place
                    if pos_list[2] > -1:
                        self.players[pos_list[2]].vcp += 6
                        self.players[pos_list[2]].end_details[end_goal] = 6
                else:
                    # two players share third place
                    for i in range(2,4):
                        self.players[pos_list[i]].vcp += 3
                        self.players[pos_list[i]].end_details[end_goal] = 3
            elif self.num_players < 4 or scores[2] > scores[3]:
                # three players share first place
                for i in range(3):
                    if pos_list[i] > -1:
                        self.players[pos_list[i]].vcp += 12
                        self.players[pos_list[i]].end_details[end_goal] = 12
            else:
                # all 4 players share the same score
                for i in range(4):
                    self.players[pos_list[i]].vcp += 9
                    self.players[pos_list[i]].end_details[end_goal] = 9
        # end goals have been calculated, send results to players
        self.server.send_finish_round(self.players)
        self.update_resources()               

    def do_sync(self):
        return (c.REQ_SYNC, self.get_game_state())

    def get_game_state(self, rejoin=False):
        game_state = {}
        game_state['round'] = self.round              
        game_state['pat'] = self.player_at_turn     
        game_state['players'] = self.players           
        game_state['map'] = self.gaia_map           
        game_state['pandq'] = self.used_p_and_q      
        game_state['actns'] = self.action_started     
        game_state['lvlup'] = self.choose_lvlup
        game_state['tech'] = self.choose_tech    
        game_state['fedm'] = self.choose_fed_marker  
        game_state['mneb'] = self.choose_mine_build
        game_state['blpl'] = self.choose_black_planet
        game_state['boop'] = self.booster_phase
        game_state['pilt'] = self.pi_list  
        game_state['aadv'] = self.avail_adv     
        game_state['aboo'] = self.avail_boosters
        game_state['afed'] = self.avail_fed_markers
        game_state['lvl5'] = self.lvl_5_free
        game_state['sply'] = self.starting_player    
        game_state['spst'] = self.starting_player_set 
        if self.round == 0:
            game_state['iidx'] = self.initial_index
            game_state['iturn']= self.initial_turn
        if rejoin:
            game_state['atec'] = self.adv_tech
            game_state['btec'] = self.tech   
            game_state['egol'] = self.end_goals  
            game_state['rgol'] = self.round_goals
            game_state['tffm'] = self.tf_fedm
            game_state['boos'] = self.boosters
            game_state['srot'] = self.sector_rot
            game_state['spos'] = self.sector_pos
        return game_state

    def save_game_state(self):
        self.mutex.acquire()
        self.blg_idx = (self.blg_idx + 1) % c.BACKLOG_LEN
        self.backlog[self.blg_idx] = copy.deepcopy(self.get_game_state())
        self.mutex.release()

    def return_to_prev_state(self):
        prev_state = self.backlog[self.blg_idx]
        self.round              = prev_state['round']
        self.player_at_turn     = prev_state['pat']
        self.players            = prev_state['players']
        self.gaia_map           = prev_state['map']
        self.used_p_and_q       = prev_state['pandq']
        self.action_started     = prev_state['actns']
        self.choose_lvlup       = prev_state['lvlup']
        self.choose_fed_marker  = prev_state['fedm']
        self.choose_mine_build  = prev_state['mneb']
        self.choose_black_planet= prev_state['blpl']
        self.choose_tech        = prev_state['tech']
        self.pi_list            = prev_state['pilt']
        self.booster_phase      = prev_state['boop']
        self.avail_adv          = prev_state['aadv']
        self.avail_boosters     = prev_state['aboo']
        self.lvl_5_free         = prev_state['lvl5']
        self.avail_fed_markers  = prev_state['afed']
        self.starting_player    = prev_state['sply']
        self.starting_player_set= prev_state['spst']        
        if 'iidx' in prev_state:
            self.initial_index = prev_state['iidx']
            self.initial_turn  = prev_state['iturn']
        self.blg_idx = (self.blg_idx - 1) % c.BACKLOG_LEN
        return prev_state

    def handle_undo(self, pos):
        self.mutex.acquire()        
        prev_state = self.backlog[(self.blg_idx - 1) % c.BACKLOG_LEN]
        if prev_state == None:
            self.mutex.release()
            return c.NOT_POSSIBLE
        if pos == prev_state['pat']: # should be ==  
            thread = threading.Thread(target=self.do_undo)
            thread.start()
            return c.ACKNOWLEDGE
        else:
            state_diff = DeepDiff(prev_state, self.get_game_state()).to_dict()
            for diff_key in state_diff:
                if diff_key == 'values_changed':
                    for key in state_diff[diff_key]:
                        if f"root['players'][{pos}]" == key[:18]:
                            thread = threading.Thread(target=self.do_undo)
                            thread.start()
                            return c.ACKNOWLEDGE
            # requesting player did nothing so deny undo
            self.mutex.release()
            return c.DENY

    def do_undo(self):
        prev_state = self.return_to_prev_state()
        self.mutex.release()
        self.server.send_undo(prev_state)

    def import_game_state(self, path, filename, start_server = None):
        with open(os.path.join(path, filename[0]), 'r') as infile:
            game_state = jsonpickle.decode(infile.read(), keys=True)
        if 'iidx' in game_state:
            self.initial_index = game_state['iidx']
            self.initial_turn  = game_state['iturn']        
        self.round              = game_state['round']   
        self.player_at_turn     = game_state['pat']     
        self.players            = game_state['players'] 
        self.gaia_map           = game_state['map']     
        self.used_p_and_q       = game_state['pandq']   
        self.action_started     = game_state['actns']   
        self.choose_lvlup       = game_state['lvlup']   
        self.choose_fed_marker  = game_state['fedm']    
        self.choose_mine_build  = game_state['mneb']    
        self.choose_black_planet= game_state['blpl']    
        self.choose_tech        = game_state['tech']    
        self.booster_phase      = game_state['boop']    
        self.avail_adv          = game_state['aadv']    
        self.avail_boosters     = game_state['aboo']    
        self.avail_fed_markers  = game_state['afed']    
        self.lvl_5_free         = game_state['lvl5']    
        self.adv_tech           = game_state['atec']    
        self.tech               = game_state['btec']    
        self.end_goals          = game_state['egol']    
        self.round_goals        = game_state['rgol']    
        self.tf_fedm            = game_state['tffm']    
        self.boosters           = game_state['boos'] 
        self.sector_rot         = game_state['srot']
        self.sector_pos         = game_state['spos']
        self.backlog = [None] * c.BACKLOG_LEN
        self.blg_idx = 0
        
        if isinstance(start_server, tuple) and len(start_server) == 2:
            ip, num_players = start_server
            self.num_players = int(num_players)
            self.server = network_server.Server(self, ip, True)

    def export_game_state(self):
        game_state = self.get_game_state(rejoin=True)
        with open('exported_game_state.json', 'w') as outfile:
            json_state = jsonpickle.encode(game_state, keys=True)
            outfile.write(json_state)   


    # function called from the network after receiving data

    def handle_request(self, player_pos, req_data):   
        req_type = req_data[0]
        reply = c.DENY
        # check if player_pos is a possible value
        if not isinstance(player_pos, int) or player_pos < 0 or player_pos >= self.num_players:
            return reply
        if req_type == c.REQ_SYNC:
            return self.do_sync()
        # Map Setup
        if(self.round == -3):
            if(req_type == c.CHANGE_MAP and (len(req_data) == 4)): 
                reply = self.handle_change_map(sector_pos=req_data[1],sector_rot=req_data[2], final=req_data[3])                                
            if(req_type == c.ROTATE_SEC and (len(req_data) == 2)): 
                reply = self.handle_rotate(sector_name=req_data[1])  
            # Map has been changed by players so update server view 
            if reply == c.ACKNOWLEDGE:         
                self.app_view.root.get_screen('setup').update_values()
        # Booster and Goals Setup
        elif(self.round == -2):
            if(req_type == c.NEW_SETUP and (len(req_data) == 1)):
                self.handle_pick_random_setup()
                reply = c.ACKNOWLEDGE
            if(req_type == c.SWITCH_TO_FACTION_SETUP and (len(req_data) == 1) and self.boosters):
                # additionally checks if a setup has been picked by ensuring boosters != None
                self.handle_switch_to_faction_setup()
                reply = c.ACKNOWLEDGE
        # Faction Setup
        elif(self.round == -1):                
            if(req_type == c.FACTION_PICKED and (len(req_data) == 2) and player_pos == self.player_at_turn):
                reply = self.handle_choose_faction(req_data[1])
        # from here on, undo is possible
        elif(req_type == c.REQ_UNDO):
            reply = self.handle_undo(player_pos)
        # Initial Mine Placement
        elif(self.round == 0):
            if(req_type == c.BUILD_MINE and (len(req_data) == 3)): 
                reply = self.handle_build_mine(q=req_data[1], r=req_data[2])
        # Game
        elif(self.round > 0):            
            if(req_type == c.PASSIVE_INCOME and (len(req_data) == 1)): 
                reply = self.handle_passive_income(player_pos)            
            elif(req_type == c.FREE_ACTION and (len(req_data) == 2)):
                reply = self.handle_free_action(player_pos, action_type=req_data[1])
            # all other actions need the player to be the player_at_turn
            elif(player_pos == self.player_at_turn):
                if(req_type == c.BUILD_MINE and (len(req_data) == 3)):
                    reply = self.handle_build_mine(q=req_data[1], r=req_data[2])
                elif(req_type == c.BUILDING_UPGRADE and (len(req_data) == 4)):
                    reply =  self.handle_upgrade_building(q=req_data[1], r=req_data[2], decision=req_data[3])
                elif(req_type == c.BOOSTER_PICK and (len(req_data) == 2)):
                    reply = self.handle_booster_pick(boo=req_data[1])
                elif(req_type == c.TECH_CHOSEN and (len(req_data) == 4)):
                    reply = self.handle_tech_chosen(tech=req_data[1], chosen_idx=req_data[2], cover=req_data[3])
                elif(req_type == c.LEVEL_UP and (len(req_data) == 3)):
                    reply = self.handle_level_up(track=req_data[1], need_resources=req_data[2])
                elif(req_type == c.ACTION_STARTED and (len(req_data) == 2)):
                    reply = self.handle_action_started(action_type=req_data[1])
                elif(req_type == c.ACTION_CANCELED and (len(req_data) == 2)):
                    reply = self.handle_action_canceled(action_type=req_data[1])
                elif(req_type == c.BUILD_FED and (len(req_data) == 3)):
                    reply = self.handle_build_fed(fed=req_data[1], sats=req_data[2])
                elif(req_type == c.FED_MARKER_CHOICE and (len(req_data) == 2)):
                    reply = self.handle_fed_marker_choice(fed_marker=req_data[1])
                elif(req_type == c.FACTION_SPECIAL and (len(req_data) == 3)):
                    reply = self.handle_faction_special(action_type=req_data[1], args=req_data[2])
                elif(req_type == c.BLACK_PLANET and (len(req_data) == 3)):
                    reply = self.handle_black_planet(q=req_data[1], r=req_data[2])
                elif(req_type == c.FINISH_ROUND and (len(req_data) == 1)):
                    reply = self.handle_finish_round()
        return reply
        

    

    def handle_rotate(self, sector_name):
        if(isinstance(sector_name, str) and sector_name in c.SECTOR_LIST_POS.keys()):
            i = c.SECTOR_LIST_POS[sector_name]
            self.sector_rot[i] = (self.sector_rot[i] + 1) % 6
            self.server.send_change_map(self.sector_pos, self.sector_rot, False)
            return c.ACKNOWLEDGE
        return c.DENY

    def server_change_map(self, sector_pos, sector_rot):
        # map has been modified from server
        # check if input is correct
        if (len(sector_pos) == 10 and len(sector_rot) == 10):
            for i in sector_rot:
                if  ((not isinstance(i, int)) or (i > 5) or (i < 0)):
                    self.app_view.root.get_screen('setup').update_values()                    
                    return c.DENY
            # ensure each sector is included exactly once
            sector_pos_check = sector_pos.copy()
            sector_pos_check.sort()
            if(sector_pos_check == [1,2,3,4,5,6,7,8,9,10]):
                self.sector_pos = sector_pos
                self.sector_rot = sector_rot
                self.server.send_change_map(self.sector_pos, self.sector_rot, False)
                return c.ACKNOWLEDGE        
        self.app_view.root.get_screen('setup').update_values()
        return c.DENY

    def handle_change_map(self, sector_pos, sector_rot, final):
        # check if data is okay
        if (len(sector_pos) == 10 and len(sector_rot) == 10):
            for i in sector_rot:
                if  ((not isinstance(i, int)) or (i > 5) or (i < 0)):
                    return c.DENY
            # ensure each sector is included exactly once
            sector_pos_check = sector_pos.copy()
            sector_pos_check.sort()
            if(sector_pos_check == [1,2,3,4,5,6,7,8,9,10]):
                self.sector_pos = sector_pos
                self.sector_rot = sector_rot
                if (final == True):
                    self.save_final_map()

                self.server.send_change_map(self.sector_pos, self.sector_rot, final)
                return c.ACKNOWLEDGE
        return c.DENY

        
    def save_final_map(self):    
        self.round += 1    
        self.app_view.root.get_screen('setup').next_phase()
        for i in range(0, 10):
            offset_q, offset_r, _name = c.SECTOR_CENTERS[i]
            sector = c.SECTOR_TILES[self.sector_pos[i] - 1]
            for planet_coords in sector:
                q, r = planet_coords
                if self.sector_rot[i] > 0:
                    q, r = maptools.rotate_around_center(q, r, self.sector_rot[i])
                self.gaia_map[(offset_q + q, offset_r + r)] = [sector[planet_coords], None, None, False, 0]  # [Planettype, Owner, Buildingtype, in alliance, lantida]
        
    def handle_switch_to_faction_setup(self):
        self.app_view.root.get_screen('setup').next_phase()
        self.server.send_switch_to_faction_setup()
        self.player_at_turn = self.num_players - 1
        self.round += 1
        self.send_plat()

    def handle_faction_picked(self, name, faction_value, final):
        peer = faction.FACTIONS[faction_value](self, name, self.player_at_turn)
        self.players.insert(0, peer)
        self.app_view.add_faction_picked(name, faction_value)
        self.app_view.root.get_screen('others').add_player(self.player_at_turn, faction_value)
        if final:
            self.app_view.switch_screen(
                'map', transition=screenmanager.SlideTransition(direction='up'), delay=4)            
            self.set_up_init_turn()
            # setup is finished so we update the round goals on the view
            self.update_resources()
            if self.my_turn():
                self.app_view.your_turn_popup(
                    '[size=18sp][b]Setze deine erste Mine[/b] \n klicke dafür den Planeten an[/size]', delay=5)
        else:
            # change player counter clockwise
            self.player_at_turn -= 1
            if self.my_turn():
                self.app_view.your_turn_popup(
                    '[size=18sp]Wähle deine Fraktion[/size]')

       

    # functions for direct communication between network and view

    def add_player_to_view(self, player_name):
        self.app_view.root.get_screen('waiting').add_player(player_name)



if __name__ == '__main__':
    Gaia()
