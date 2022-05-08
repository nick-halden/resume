import os, sys
from typing import Iterable, List

from deepdiff.model import ResultDict

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import threading
import jsonpickle
from kivy.config import Config
from kivy.logger import Logger
from gaia_lib import faction
import network_client
from gaia_lib import maptools
import view
import sys
from gaia_lib import constants as c
import kivy.uix.screenmanager as screenmanager
from deepdiff import DeepDiff

class Gaia:
    '''This class is responsible for keeping the game status and also connecting to the other players to send / receive updates.'''

    # define constants

    def __init__(self):
        self.players = None
        (
            self.boosters,
            self.round_goals,
            self.end_goals,
            self.adv_tech,
            self.avail_adv,
            self.avail_boosters,
            self.tf_fedm
        ) = (None, None, None, None, None, None, None)
        self.tech = [
            c.TEC_CRE,
            c.TEC_GAI,
            c.TEC_KNW,
            c.TEC_ORE,
            c.TEC_PIA,
            c.TEC_POW,
            c.TEC_QIC,
            c.TEC_TYP,
            c.TEC_VPS,
        ]
        self.used_p_and_q = set()
        self.build_fed = {}
        self.choose_tech = False
        self.tech_cache = None
        self.choose_cover = False
        self.choose_lvlup = False
        self.action_started = None
        self.choose_fed_marker= False
        self.choose_fed_build = False
        self.choose_sats = False
        self.choose_mine_build = False
        self.choose_black_planet = False
        self.booster_phase = False
        self.app_view = view.GaiaGame(self)
        self.connect = None  # ths will be the instance of the Network Class
        self.player_at_turn = 0
        self.num_players = 0
        self.my_pos = 0
        self.round = -3
        self.initial_idx = 0
        self.lvl_5_free = [True] * 6
        self.avail_fed_markers = [3] * len(c.FED_MARKERS)
        self.gaia_map = {}  # [Planettype, Owner, Buildingtype, in federation, lantida]
        self.sector_pos = [8, 9, 10, 2, 4, 3, 1, 5, 6, 7]  # standard sector positions
        # standard sector rotation angle= i * (-60°)
        self.sector_rot = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.starting_player = 0
        self.starting_player_set = False
        self.pi_list = None


        # from now on all will be done via user input which will be through the app_view
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        Config.set('kivy','window_icon',f'{c.ASSETS_PATH}/icon_64.png')
        Config.set('kivy','exit_on_escape',0)
        Config.set('kivy', 'log_dir', f'{self.app_view.user_data_dir}/logs')
        Config.set('kivy', 'log_maxfiles', 24)
        Config.set('kivy','log_enable', 1)
        Config.write()
        try:
            self.app_view.run()
        except Exception as e:
            Logger.error(f'Recv Exception: {str(e)}')
        finally:
            Logger.info('Game has been closed')
            # app has been closed so the programm is finished
            sys.exit()

    # function which the gaia class will execute

    def my_turn(self):
        return self.player_at_turn == self.my_pos

    def current_player_popup(self):
        if self.my_turn():
            self.app_view.your_turn_popup(
                title=f'Runde {self.round}', text='Mache eine Aktion oder passe'
            )
        else:
            self.app_view.your_turn_popup(
                title=f'Runde {self.round}',
                text=f'{self.players[self.player_at_turn].name} ist dran',
            )

    def action_possible(self):
        if self.my_turn():
            if self.round > 0 and self.round < 7:
                if self.choose_cover:
                    return c.NEED_CHOOSE_COVER
                elif self.choose_lvlup:
                    return c.NEED_CHOOSE_TRACK
                elif self.choose_tech:
                    return c.NEED_CHOOSE_TECH
                elif self.choose_mine_build:
                    return c.NEED_BUILD_MINE
                elif self.choose_fed_marker:
                    return c.NEED_CHOOSE_FED_MARKER
                elif self.choose_fed_build:
                    return c.NEED_CHOOSE_FED_BUILD
                elif self.choose_black_planet:
                    return c.NEED_CHOOSE_BLACK_PLANET
                elif self.booster_phase:
                    return c.NEED_CHOOSE_BOOSTER
                elif self.action_started is not None:
                    return self.action_started
                else:
                    return c.POSSIBLE
            elif self.round == 0:
                return c.NEED_BUILD_MINE
        return c.NOT_YOUR_TURN
 
    # this function will also be called upon receiving the final map
    def save_final_map(self):
        self.app_view.root.get_screen('map').draw_map()
        for i in range(0, 10):
            offset_q, offset_r, _name = c.SECTOR_CENTERS[i]
            sector = c.SECTOR_TILES[self.sector_pos[i] - 1]
            for planet_coords in sector:
                q, r = planet_coords
                if self.sector_rot[i] > 0:
                    q, r = maptools.rotate_around_center(q, r, self.sector_rot[i])
                self.gaia_map[(offset_q + q, offset_r + r)] = [
                    sector[planet_coords],
                    None,
                    None,
                    False,
                    False,
                ]  # [Planettype, Owner, Buildingtype, in alliance, lantida]
        self.app_view.switch_screen(
            'setup', transition=screenmanager.SlideTransition(direction='up')
        )

    def round_booster_popup(self):
        self.app_view.show_booster_choice(self.avail_boosters)

    # functions which will be called from the view

    def enter_login(self, name, server_ip):
        self.connect = network_client.Client(self, server_ip)
        reply = self.connect.connect_to_server(name)
        if reply == c.NAME_IN_USE:
            self.app_view.error_popup('Der Name ist bereits vergeben')
        elif reply == c.ACKNOWLEDGE:
            # save configuration
            with open(f'{self.app_view.user_data_dir}/{c.CONFIG_PATH}', 'w') as config:
                config.write(f'name: {name}\n')
                config.write(f'server_ip: {server_ip}\n')
            config.close()
            # start thread for recieving data          
            _thread = threading.Thread(target=self.connect.receive_data_loop)
            _thread.daemon = True
            _thread.start()
        elif isinstance(reply, tuple) and len(reply) == 2 and reply[0] == c.REJOIN:            
            # save configuration
            with open(f'{self.app_view.user_data_dir}/{c.CONFIG_PATH}', 'w') as config:
                config.write(f'name: {name}\n')
                config.write(f'server_ip: {server_ip}\n')
            config.close()
            # save game_state
            self.rejoin_game(name, game_state=reply[1])
            # start thread for recieving data          
            _thread = threading.Thread(target=self.connect.receive_data_loop)
            _thread.daemon = True
            _thread.start()
        else:
            self.app_view.error_popup('Konnte nicht mit dem Server verbinden')
        self.app_view.root.get_screen('login').handle_login(reply)

    def req_new_map(self, sector_pos):
        self.sector_pos = sector_pos
        self.sector_rot = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        _thread = threading.Thread(
            target=self.connect.send_change_map, args=[self.sector_pos, self.sector_rot]
        )
        _thread.start()

    def req_switch_sectors(self, sector_1_pos, sector_2_pos):
        self.sector_pos[sector_1_pos], self.sector_pos[sector_2_pos] = (
        self.sector_pos[sector_2_pos], self.sector_pos[sector_1_pos],)
        self.sector_rot[sector_1_pos], self.sector_rot[sector_2_pos] = (
        self.sector_rot[sector_2_pos], self.sector_rot[sector_1_pos],)



        _thread = threading.Thread(
            target=self.connect.send_change_map, args=[self.sector_pos, self.sector_rot]
        )
        _thread.start()

    def req_rotate(self, sector_name):        
        _thread = threading.Thread(
            target=self.connect.send_rotate, args=[sector_name]
        )
        _thread.start()

    def req_final_map(self):
        self.save_final_map()
        _thread = threading.Thread(
            target=self.connect.send_change_map,
            args=[self.sector_pos, self.sector_rot, True],
        )
        _thread.start()

    def request_new_setup(self):
        strs_thread = threading.Thread(target=self.connect.send_request_new_setup)
        strs_thread.start()

    def switch_to_faction_setup(self):
        strs_thread = threading.Thread(target=self.connect.send_switch_to_faction_setup)
        strs_thread.start()

    def req_choose_faction(self, faction_value):
        _thread = threading.Thread(
                target=self.connect.send_faction, args=[faction_value]
            )
        _thread.start()    

    def choose_booster(self, boo):
        if boo in self.avail_boosters:
            thread = threading.Thread(target=self.connect.send_booster_pick, args=[boo])
            thread.start()         


    def req_build_mine(self, q, r):
        result = self.action_possible()
        if self.round == 0 or self.choose_mine_build or result == c.POSSIBLE:
            result = self.players[self.my_pos].build_mine_possible(q, r, self.gaia_map, initial=(self.round == 0))
            if result == c.POSSIBLE:
                thread = threading.Thread(
                        target=self.connect.send_build_mine, args=[q, r]
                    )
                thread.start()
            return result
        return c.ACTION_NOT_POSSIBLE

    def req_upgrade_building(self, q, r, decision=None):
        result = self.action_possible()
        if result == c.POSSIBLE:
            if self.gaia_map[(q, r)][1] != self.my_pos:
                if self.players[self.my_pos].faction_type == c.LANTIDA:
                    # Lantida mine build on other planet
                    return self.req_build_mine(q, r)
                else:
                    return c.NOT_OWNED_BY_YOU
            else:
                return_value = self.players[self.my_pos].upgrade_building_possible(q, r, self.gaia_map, decision=decision)
                if return_value == c.POSSIBLE or return_value== c.POSSIBLE_CHOOSE_TECH:
                    thread = threading.Thread(
                        target=self.connect.send_upgrade, args=[q, r, decision]
                    )
                    thread.start()
                return return_value
        elif result == c.AMBAS_PLI:
            if isinstance(self.players[self.my_pos], faction.Ambas):
                result = self.players[self.my_pos].pli_change_possible(self.gaia_map, q, r)
                if result == c.POSSIBLE:
                    thread = threading.Thread(target=self.connect.send_faction_special, args=[c.AMBAS_PLI,(q,r)])
                    thread.start()
                    return result
                else:
                    return result
        elif result == c.FIRAKS_PLI:
            if isinstance(self.players[self.my_pos], faction.Firaks):
                result = self.players[self.my_pos].lab_downgrade_possible(self.gaia_map, q, r)
                if result == c.POSSIBLE:
                    thread = threading.Thread(target=self.connect.send_faction_special, args=[c.FIRAKS_PLI,(q,r)])
                    thread.start()
                    return result
                else:
                    return result
        return c.ACTION_NOT_POSSIBLE

    def req_ivit_sat(self, q, r):
        result = c.NOT_POSSIBLE
        if self.players[self.my_pos].faction_type == c.DER_SCHWARM:
            result = self.action_possible()
            if result == c.DER_SCHWARM_PLI:
                result = self.players[self.my_pos].ivit_sat_possible(q,r, self.gaia_map)
                if result == c.POSSIBLE:
                    thread = threading.Thread(target=self.connect.send_faction_special, args=[c.DER_SCHWARM_PLI,(q,r)])
                    thread.start()
        return result

    def do_passive_income(self):
        thread = threading.Thread(target=self.connect.send_passive_income)
        thread.start()
        self.app_view.update_resources()

    def req_free_action(self, action_type):
        result = c.NOT_POSSIBLE
        if self.round > 0 and self.round < 7:
            if self.booster_phase:
                if self.players[self.my_pos].faction_type == c.TERRANER:
                    result = self.players[self.my_pos].gaia_free_action_possible(action_type)
            else:
                result = self.players[self.my_pos].free_action_possible(action_type)
            if result == c.POSSIBLE:
                thread = threading.Thread(
                    target=self.connect.send_free_action,
                    args=[action_type],
                )
                thread.start()
        return result
            

    def req_tech(self, tile, chosen_idx=None, cover=None):
        result = self.action_possible()
        if self.choose_tech:
            if (self.choose_cover or self.choose_lvlup) and not tile == self.tech_cache[0]:
                # player has choosen a different tech tile so reset status
                self.choose_cover = False
                self.choose_lvlup = False
            result = c.POSSIBLE
            if tile in [
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
                tech_idx = int(tile[-1]) - 1
                idx = tech_idx if tech_idx < 6 else chosen_idx
                result = self.players[self.my_pos].tech_tile_possible(
                    self.tech[tech_idx], index=idx, cover=cover, lvl_5_free=self.lvl_5_free
                )
                if result in [c.POSSIBLE, c.POSSIBLE_NO_LVL_UP]:
                    thread = threading.Thread(
                        target=self.connect.send_tech_chosen, args=[tile, idx]
                    )
                    thread.start()
                elif result == c.NEED_CHOOSE_TRACK:
                    self.choose_lvlup = True
                    self.choose_tech = True
                    self.tech_cache = (tile, None)
            elif tile in [
                c.ADV_TECH_1,
                c.ADV_TECH_2,
                c.ADV_TECH_3,
                c.ADV_TECH_4,
                c.ADV_TECH_5,
                c.ADV_TECH_6,
            ]:
                tech_idx = int(tile[-1]) - 1
                result = self.players[self.my_pos].tech_tile_possible(
                    self.adv_tech[tech_idx], avail_adv=self.avail_adv, adv_idx = tech_idx, index=chosen_idx, cover=cover, lvl_5_free=self.lvl_5_free
                )
                if result in [c.POSSIBLE, c.POSSIBLE_NO_LVL_UP]:
                    thread = threading.Thread(
                        target=self.connect.send_tech_chosen, args=[tile, chosen_idx, cover]
                    )
                    thread.start()
                elif result == c.NEED_CHOOSE_COVER:
                    self.choose_cover = True
                    self.choose_tech = True
                    self.tech_cache = (tile, None)
                    self.app_view.update_resources()
                elif result == c.NEED_CHOOSE_TRACK:
                    self.choose_cover = False
                    self.choose_lvlup = True
                    self.choose_tech = True
                    self.tech_cache = (tile, cover)
                    self.app_view.update_resources()
            else:
                result = c.NEED_CHOOSE_TECH
        return result

    def pick_cover(self, tech):        
        p = self.players[self.my_pos]
        if (tech in p.tech_tiles and
            p.adv_tiles[p.tech_tiles.index(tech)] is None
            ):
            return self.req_tech(self.tech_cache[0], cover=tech)
        return c.NOT_POSSIBLE

    def req_level_up(self, track):
        result = self.action_possible()
        if (self.choose_lvlup or result == c.POSSIBLE):
            result = c.POSSIBLE
            if track in [
                    c.TRACK_1,
                    c.TRACK_2,
                    c.TRACK_3,
                    c.TRACK_4,
                    c.TRACK_5,
                    c.TRACK_6,
                ]:
                branch = int(track[-1]) - 1
                if self.action_started == c.MAD_ANDROIDS_SPECIAL:
                        result = self.players[self.my_pos].free_level_up_possible(
                            branch
                        )
                        if not result == c.POSSIBLE:                            
                            return result
                # lvlup for 4 knowledge or free if choose_lvlup is True                
                result = self.players[self.my_pos].level_up_possible(
                    branch, self.lvl_5_free, need_resources=(not self.choose_lvlup)
                )                    
                if result in [c.POSSIBLE_TURN_MARKER_GRAY, c.POSSIBLE]:
                        # track choice for picked tech tile                    
                    if self.choose_tech:
                        if self.tech_cache[0] in [c.ADV_TECH_1,c.ADV_TECH_2,c.ADV_TECH_3,c.ADV_TECH_4,c.ADV_TECH_5,c.ADV_TECH_6]:
                            self.req_tech(self.tech_cache[0], cover=self.tech_cache[1], chosen_idx=branch)
                        else:
                            return self.req_tech(self.tech_cache[0], chosen_idx=branch)
                    else:
                        thread = threading.Thread(
                                target=self.connect.send_level_up, args=[track,(not self.choose_lvlup)]
                            )
                        thread.start()
                    return result
        return result

    def req_action(self, action_type):
        result = self.action_possible()
        if self.action_started == action_type or result == c.POSSIBLE:
            result = c.POSSIBLE 
            if self.round > 0:
                if action_type in [
                    c.PUB_2_GLD,
                    c.PUB_2_KNW_2,
                    c.PUB_2_KNW_3,
                    c.PUB_2_ORE,
                    c.PUB_2_PWS,
                    c.PUB_2_TRF_1,
                    c.PUB_2_TRF_2,
                    c.QIC_2_FED,
                    c.QIC_2_TEC,
                    c.QIC_2_VPS,
                ]:
                    if self.action_started is None:
                        if action_type not in self.used_p_and_q:
                            result = self.players[self.my_pos].p_and_q_possible(action_type)
                            if result == c.POSSIBLE:
                                thread = threading.Thread(
                                    target=self.connect.send_action_started,
                                    args=[action_type],
                                )
                                thread.start()
                            return result                               
                        else:
                            return c.ALREADY_USED
                    else:
                        thread = threading.Thread(
                            target=self.connect.send_action_canceled, args=[action_type]
                        )
                        thread.start()
                        return c.POSSIBLE
                if action_type in [c.AMBAS_PLI, c.FIRAKS_PLI, c.MAD_ANDROIDS_SPECIAL, c.DER_SCHWARM_PLI]:
                    if self.action_started is None:
                        result = self.players[self.player_at_turn].pli_orange_possible()
                        if result == c.POSSIBLE:
                            thread = threading.Thread(
                                    target=self.connect.send_action_started,
                                    args=[action_type],
                                )
                            thread.start()                            
                    else:
                        thread = threading.Thread(
                            target=self.connect.send_action_canceled, args=[action_type]
                        )
                        thread.start()
                        return c.POSSIBLE

            elif self.round == 0:
                result = c.NEED_BUILD_MINE
            return result
        if (result == c.NEED_CHOOSE_BOOSTER and
            action_type == c.ITAR_PLI and
            self.players[self.player_at_turn].faction_type == c.ITAR
            ):
            if self.action_started == action_type:
                thread = threading.Thread(
                    target=self.connect.send_action_canceled, args=[action_type]
                )
                thread.start()
                return c.POSSIBLE
            elif self.action_started is None:
                result = c.POSSIBLE if self.players[self.player_at_turn].gaia_phase_action_possible() else c.NOT_ENOUGH_POWERSTONES
                if result == c.POSSIBLE:
                    thread = threading.Thread(
                            target=self.connect.send_action_started,
                            args=[action_type],
                        )
                    thread.start() 
        return result

    def req_booster_action(self, action_type): 
        if action_type not in [c.BOO_TER, c.BOO_NAV]:
            return c.NOT_POSSIBLE       
        result = self.action_possible()
        if self.choose_mine_build and self.action_started == action_type:
            thread = threading.Thread(
                target=self.connect.send_action_canceled, args=[action_type]
            )
            thread.start()
            return c.CANCEL_ACTION
        elif result == c.POSSIBLE:
            if not self.players[self.my_pos].orange_used[2]:
                thread = threading.Thread(
                    target=self.connect.send_action_started, args=[action_type]
                )
                thread.start()
            else:
                return c.ALREADY_USED
        return result

    def tech_action(self, action_type):
        result = self.action_possible()
        if result == c.POSSIBLE:
            result = self.players[self.my_pos].tech_action_possible(action_type)
            if result == c.POSSIBLE:
                thread = threading.Thread(
                    target=self.connect.send_action_started, args=[action_type]
                )
                thread.start()
            return result
        else:
            return c.ACTION_NOT_POSSIBLE

    def ac_action(self):
        result = self.action_possible()
        if result == c.POSSIBLE:
            result = self.players[self.my_pos].ac_action_possible()
            if result == c.POSSIBLE:
                thread = threading.Thread(
                    target=self.connect.send_action_started, args=[c.ORANGE_QIC]
                )
                thread.start()
        return result

    def start_build_fed(self):
        if self.action_possible() == c.POSSIBLE:
            self.choose_fed_build = True
            self.build_fed = {}
            return True
        return False

    def cancel_build_fed(self):
        if self.choose_fed_build:
            self.choose_fed_build = False

    def build_fed_add_planet(self, q, r):
        result = [c.NOT_POSSIBLE, None]
        if (q, r) in self.build_fed and not (
            self.players[self.my_pos].faction_type == c.DER_SCHWARM and (q,r) in self.gaia_map and self.gaia_map[(q, r)][3]
            ):
            self.build_fed.pop((q, r))  # remove building from fed
            self.build_fed_remove_cluster(q, r)
            result[0] = c.SUCCESS
            result[1] = self.build_fed
        else:
            # if building belongs to player and is not in alliance
            if self.players[self.my_pos].faction_type == c.DER_SCHWARM:
                # ivit specific fed building
                if ((q,r) in self.gaia_map and self.gaia_map[(q, r)][1] == self.my_pos):
                    self.build_fed[(q, r)] = self.gaia_map[(q, r)]
                    self.build_fed_add_cluster(q, r)
                    result[0] = c.SUCCESS
                    result[1] = self.build_fed
                elif (q,r) in self.players[self.my_pos].ivit_sats:
                    # pretend its a planet
                    self.build_fed[(q, r)] = [None, self.my_pos, c.IVIT_SATELLITE, False, 0] 
                    self.build_fed_add_cluster(q, r)
                    result[0] = c.SUCCESS
                    result[1] = self.build_fed
            else:
                if self.gaia_map[(q, r)][1] == self.my_pos:
                    if not self.gaia_map[(q, r)][3]:
                        self.build_fed[(q, r)] = self.gaia_map[(q, r)]
                        self.build_fed_add_cluster(q, r)
                        result[0] = c.SUCCESS
                        result[1] = self.build_fed
                    else:
                        result[0] = c.ALREADY_IN_FED                
                elif self.players[self.my_pos].faction_type == c.LANTIDA:
                    if self.gaia_map[(q, r)][4] == 1:
                        self.build_fed[(q, r)] = self.gaia_map[(q, r)]
                        self.build_fed_add_cluster(q, r)
                        result[0] = c.SUCCESS
                        result[1] = self.build_fed
                    elif self.gaia_map[(q, r)][4] == 2:
                        result[0] = c.ALREADY_IN_FED
                    else:
                        result[0] = c.NOT_OWNED_BY_YOU
                else:
                    result[0] = c.NOT_OWNED_BY_YOU
        return result

    def build_fed_add_cluster(self, q, r):
        for new_q in range(q - 1, q + 2):
            for new_r in range(r - 1, r + 2):
                if maptools.hex_distance(q, r, new_q, new_r) == 1:
                    if (new_q, new_r) not in self.build_fed:
                        if ((new_q, new_r) in self.gaia_map and                        
                            (self.gaia_map[(new_q, new_r)][1] == self.my_pos or (
                                    self.players[self.my_pos].faction_type == c.LANTIDA
                                    and self.gaia_map[(new_q, new_r)][4] == 1
                                )
                            )):  
                            self.build_fed[(new_q, new_r)] = self.gaia_map[(new_q, new_r)]
                            self.build_fed_add_cluster(new_q, new_r)
                        elif (self.players[self.my_pos].faction_type == c.DER_SCHWARM and
                            (new_q, new_r) in self.players[self.my_pos].ivit_sats
                            ):
                            self.build_fed[(new_q, new_r)] = [None, self.my_pos, c.IVIT_SATELLITE, False, 0] 
                            self.build_fed_add_cluster(new_q, new_r)

    def build_fed_remove_cluster(self, q, r):
        for new_q in range(q - 1, q + 2):
            for new_r in range(r - 1, r + 2):
                if maptools.hex_distance(q, r, new_q, new_r) == 1:
                    if (new_q, new_r) in self.build_fed:
                        if ((new_q, new_r) in self.gaia_map and
                            not (self.players[self.my_pos].faction_type == c.DER_SCHWARM and self.gaia_map[(new_q, new_r)][3])
                            ):                            
                            self.build_fed.pop((new_q, new_r))
                            self.build_fed_remove_cluster(new_q, new_r)
                        elif (self.players[self.my_pos].faction_type == c.DER_SCHWARM and
                            (new_q, new_r) in self.players[self.my_pos].ivit_sats
                            ):
                            self.build_fed.pop((new_q, new_r))
                            self.build_fed_remove_cluster(new_q, new_r)

    def get_connected_fed(self, pos, sats, traversed):
        traversed.add(pos)
        q, r = pos
        for new_q in range(q - 1, q + 2):
            for new_r in range(r - 1, r + 2):
                if maptools.hex_distance(q, r, new_q, new_r) == 1:
                    if (((new_q, new_r) not in traversed) and
                        ((new_q, new_r) in self.build_fed or 
                        (new_q, new_r) in sats)
                        ):
                        traversed = self.get_connected_fed((new_q, new_r), sats, traversed)
        return traversed
                        



    def check_fed_ready(self, sats):
        # result is False or True
        # check if fed is large enough
        result = self.players[self.my_pos].get_fed_possible(self.gaia_map, submap=self.build_fed)
        if result == c.POSSIBLE:
            self.choose_sats = True
            # calculate satelites necessary and check if correct length is given
            # TODO @Johann possibly?
            num_sats = 100 
            if len(sats) > num_sats:
                return c.NUM_SATS_TOO_HIGH
            else:
                # check if fed is continuous
                pos = list(self.build_fed.keys())[0]
                if self.players[self.my_pos].faction_type == c.DER_SCHWARM:
                    all_sats = sats.copy()
                    all_sats.update(self.players[self.my_pos].satellites)
                    traversed = self.get_connected_fed(pos, all_sats, set())
                    if len(traversed) < (len(self.build_fed) + len(all_sats)):
                        return c.FED_NOT_CONNECTED
                else:
                    traversed = self.get_connected_fed(pos, sats, set())                
                    if len(traversed) < (len(self.build_fed) + len(sats)):
                        return c.FED_NOT_CONNECTED
                return c.POSSIBLE
        else:
            self.choose_sats = False
            return result  

    def req_fed(self, sats):
        if sats is not None:
            result = self.check_fed_ready(sats)
            if result == c.POSSIBLE: 
                thread = threading.Thread(target=self.connect.send_build_fed, args=[self.build_fed, sats])
                thread.start()
            return result
        return c.NEED_CHOOSE_SATS

    def req_fed_marker_choice(self, fed_marker):
        result = c.NOT_POSSIBLE
        if self.my_turn() and self.choose_fed_marker:
            if self.action_started == c.QIC_2_FED:
                if fed_marker in self.players[self.my_pos].fed_markers:            
                    self.connect.send_fed_marker_choice(fed_marker)
                    result = c.POSSIBLE
                else:
                    return c.NOT_POSSIBLE
            else:            
                if fed_marker in c.FED_MARKERS and self.avail_fed_markers[c.FED_MARKERS.index(fed_marker)] > 0:            
                    self.connect.send_fed_marker_choice(fed_marker)
                    result = c.POSSIBLE
        return result

    def req_black_planet(self, q, r):
        result = c.NOT_POSSIBLE
        if self.choose_black_planet:
            result = self.players[self.my_pos].black_planet_possible(self.gaia_map, q, r)
            if result == c.POSSIBLE: 
                thread = threading.Thread(target=self.connect.send_black_planet, args=[q,r])
                thread.start()
                return c.POSSIBLE
        return result

    def req_finish_round(self):
        result = self.action_possible()
        if result == c.POSSIBLE or (self.booster_phase and self.my_turn() and self.players[self.player_at_turn].faction_type == c.ITAR):            
            thread = threading.Thread(target=self.connect.send_finish_round)
            thread.start()

    def req_sync(self):
        self.store_game_state(self.connect.req_sync())

    def rejoin_game(self, my_name, game_state):
        if(isinstance(game_state, dict) and
            'players' in game_state):
            self.num_players = len(game_state['players'])
            self.player_names = [''] * self.num_players
            self.app_view.colors = [None] * self.num_players
            for p in game_state['players']:
                self.player_names[p.pos] = p.name
                self.app_view.colors[p.pos] = p.color
                if p.name == my_name:
                    self.my_pos = p.pos
                    self.app_view.root.get_screen('board').save_faction(self.my_pos, p.faction_type)
                else:
                    self.app_view.root.get_screen('others').add_player(p.pos, p.name, p.faction_type)
            self.store_game_state(game_state)            
            self.app_view.root.get_screen('map').draw_map()
            self.app_view.update_resources()
            fed_possible = (self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE)
            self.app_view.update_map(self.gaia_map, fed_possible)

    def req_undo(self):
        self.connect.req_undo()

    def store_game_state(self, game_state):
        if (isinstance(game_state, dict) and
            'round' in game_state and
            'pat' in game_state and
            'players' in game_state and
            'map' in game_state and
            'pandq' in game_state and
            'actns' in game_state and
            'lvlup' in game_state and
            'fedm' in game_state and
            'mneb' in game_state and
            'tech' in game_state and
            'boop' in game_state and
            'aadv' in game_state and
            'aboo' in game_state and
            'afed' in game_state and
            'blpl' in game_state and
            'lvl5' in game_state and
            'sply' in game_state and
            'spst' in game_state and
            'pilt' in game_state
            ):
            # for rejoin, these are included in game state
            if ('rgol' in game_state and
            'egol' in game_state and
            'atec' in game_state and
            'btec' in game_state and
            'tffm' in game_state and
            'boos' in game_state and
            'spos' in game_state and
            'srot' in game_state):
                self.adv_tech           = game_state['atec']
                self.tech               = game_state['btec']
                self.end_goals          = game_state['egol']
                self.round_goals        = game_state['rgol']
                self.tf_fedm            = game_state['tffm']
                self.booster_phase      = game_state['boos']
                self.sector_rot         = game_state['srot']
                self.sector_pos         = game_state['spos']
                self.boosters           = game_state['boos']
            self.round              = game_state['round']
            self.player_at_turn     = game_state['pat']
            self.players            = game_state['players']
            self.gaia_map           = game_state['map']
            self.used_p_and_q       = game_state['pandq']
            self.action_started     = game_state['actns']
            self.starting_player    = game_state['sply']
            self.starting_player_set= game_state['spst']
            self.pi_list            = game_state['pilt']
            if self.my_turn():
                self.choose_lvlup       = game_state['lvlup']
                self.choose_tech        = game_state['tech']
                self.choose_fed_marker  = game_state['fedm']
                self.choose_mine_build  = game_state['mneb']
                self.choose_black_planet= game_state['blpl']
            else:
                self.choose_lvlup       = False
                self.choose_tech        = False
                self.choose_fed_marker  = False
                self.choose_mine_build  = False
                self.choose_black_planet= False
            self.booster_phase      = game_state['boop']
            self.avail_adv          = game_state['aadv']
            self.avail_boosters     = game_state['aboo']
            self.lvl_5_free         = game_state['lvl5']
            self.avail_fed_markers  = game_state['afed']
            self.build_fed = {}
            self.choose_sats = False
            self.choose_fed_build = False
            self.choose_cover = False
            self.app_view.root.get_screen('map').cancel_fed((self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE))
            self.tech_cache = None
            if len(self.pi_list) == self.num_players and self.pi_list[self.my_pos] > 0:
                vcp_after = self.players[self.my_pos].vcp - self.pi_list[self.my_pos] + 1
                self.app_view.passive_income(self.pi_list[self.my_pos], vcp_after)                
            else:
                if self.my_turn():
                    # update status variable according to info
                    if self.choose_lvlup:
                        self.app_view.your_turn_popup(text= c.NEED_CHOOSE_TRACK)
                    elif self.choose_tech:
                        self.app_view.your_turn_popup(text=c.NEED_CHOOSE_TECH)
                    elif self.choose_mine_build:
                        self.app_view.your_turn_popup(c.NEED_BUILD_MINE)
                    elif self.choose_fed_marker:                    
                        fed_marker_choice = set()
                        for i in range(len(self.avail_fed_markers)):
                            if self.avail_fed_markers[i] > 0:
                                fed_marker_choice.add(c.FED_MARKERS[i])
                        self.app_view.root.get_screen('map').after_fed_finished((self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE))                     
                        self.app_view.fed_marker_popup(fed_marker_choice)
                    elif self.choose_fed_build:
                        self.app_view.your_turn_popup(c.NEED_CHOOSE_FED_BUILD)
                    elif self.booster_phase:
                        len_boo = self.num_players + 3
                        for pos in range(self.starting_player, (self.starting_player + self.num_players)):
                            if (pos % self.num_players) == self.my_pos:
                                break
                            len_boo -= 1
                        if len(self.avail_boosters) == len_boo:
                            self.round_booster_popup()
                    else:
                        self.app_view.your_turn_popup('Mache eine Aktion oder passe')
                else:
                    title_text = 'Rundenboosterwahl' if self.booster_phase else f'Runde {self.round}'
                    self.app_view.your_turn_popup(
                        title=title_text,
                        text=f'{self.player_names[self.player_at_turn]} ist dran',
                    )
        else:
            self.app_view.error_popup()

    def export_game_state(self):
        game_state = {}
        game_state['round'] = self.round              
        game_state['pat'] = self.player_at_turn     
        game_state['players'] = self.players           
        game_state['map'] = self.gaia_map           
        game_state['pandq'] = self.used_p_and_q      
        game_state['actns'] = self.action_started     
        game_state['lvlup'] = self.choose_lvlup    
        game_state['fedm'] = self.choose_fed_marker  
        game_state['mneb'] = self.choose_mine_build
        game_state['blpl'] = self.choose_black_planet
        game_state['tech'] = self.choose_tech 
        game_state['boop'] = self.booster_phase  
        game_state['aadv'] = self.avail_adv     
        game_state['aboo'] = self.avail_boosters
        game_state['afed'] = self.avail_fed_markers
        game_state['lvl5'] = self.lvl_5_free
        game_state['atec'] = self.adv_tech  
        game_state['btec'] = self.tech  
        game_state['egol'] = self.end_goals  
        game_state['rgol'] = self.round_goals
        game_state['tffm'] = self.tf_fedm
        game_state['boos'] = self.boosters
        game_state['srot'] = self.sector_rot
        game_state['spos'] = self.sector_pos
        game_state['sply'] = self.starting_player    
        game_state['spst'] = self.starting_player_set
        game_state['pilt'] = self.pi_list            
        with open(f'{self.app_view.user_data_dir}/exported_game_state.json', 'w') as outfile:
            json_state = jsonpickle.encode(game_state, keys=True)
            outfile.write(json_state)
        
                

    # function called from the network after receiving data

    def recv_player_list(self, players, my_pos):
        self.my_pos = my_pos
        self.num_players = len(players)
        self.player_names = players
        self.players = [None] * self.num_players
        for player in players:
                self.add_player_to_view(player)
    
    def recv_change_map(self, sector_pos, sector_rot):
        self.sector_pos = sector_pos
        self.sector_rot = sector_rot
        self.app_view.root.get_screen('map_setup').draw_map()

    def recv_setup(self, boosters, round_goals, end_goals, adv_tech, tech, tf_fedm):
        self.boosters = boosters
        self.avail_boosters = boosters.copy()
        self.round_goals = round_goals
        self.end_goals = end_goals
        self.adv_tech = adv_tech
        self.avail_adv = adv_tech
        self.tech = tech
        self.tf_fedm = tf_fedm
        self.app_view.root.get_screen('setup').new_setup(
            boosters, self.round_goals, self.end_goals
        )

    def recv_switch_to_faction_setup(self):
        self.app_view.switch_screen(
            'faction_setup', transition=screenmanager.SlideTransition(direction='up')
        )

    def recv_faction_picked(self, faction_obj):
        player_pos = faction_obj.pos
        self.players[player_pos] = faction_obj
        self.app_view.add_faction_picked(faction_obj.name, faction_obj.faction_type, (player_pos == self.my_pos))
        if player_pos == self.my_pos:
            self.app_view.root.get_screen('board').save_faction(self.my_pos, faction_obj.faction_type)
        else:
            self.app_view.root.get_screen('others').add_player(player_pos, faction_obj.name, faction_obj.faction_type)
        if player_pos == 0:            
            # save player colors in view            
            colors = [None] * self.num_players
            for p in self.players:
                colors[p.pos] = p.color
            self.app_view.save_colors(colors)
            self.app_view.switch_screen(
                'map', transition=screenmanager.SlideTransition(direction='up'), delay=(4 if self.num_players > 1 else 0)
            )
            # setup is finished so we update the round goals on the view
            self.app_view.update_resources()
            fed_possible = (self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE)
            self.app_view.update_map(self.gaia_map,fed_possible)
        
    def recv_undo(self, game_state):
        self.store_game_state(game_state)
        self.app_view.update_resources()        
        fed_possible = (self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE)
        self.app_view.update_map(self.gaia_map,fed_possible)

    def recv_player_at_turn(self, round, player_at_turn, info):
        self.round = round
        self.player_at_turn = player_at_turn
        if isinstance(info, tuple):
            if info[0] == c.NEED_CHOOSE_BOOSTER and isinstance(info[1], list):
                # update boosters and prevent free actions during booster phase
                self.booster_phase = True
                self.avail_boosters = info[1]
            if info[0] == c.NEED_CHOOSE_FED_MARKER and isinstance(info[1], list):
                self.avail_fed_markers = info[1]
                if self.my_turn():
                    self.choose_fed_marker= True
                    self.choose_fed_build = False
                    self.choose_sats = False
                    self.build_fed = {}
                    fed_marker_choice = set()
                    for i in range(len(self.avail_fed_markers)):
                        if self.avail_fed_markers[i] > 0:
                            fed_marker_choice.add(c.FED_MARKERS[i])
                    self.app_view.root.get_screen('map').after_fed_finished((self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE))                     
                    self.app_view.fed_marker_popup(fed_marker_choice)
        elif isinstance(info, str):
            if info == c.NEW_ROUND:                
                self.booster_phase = False
                self.used_p_and_q = set()
                self.starting_player_set = False
        if self.my_turn():
            if self.round == -1:
                self.app_view.your_turn_popup('[size=18sp]Wähle deine Fraktion[/size]')
            elif self.round == 0:
                if self.players[self.my_pos].faction_type == c.DER_SCHWARM:
                    yt_text = '[size=18sp][b]Setze deinen Regierungssitz[/b] \n klicke dafür den Planeten an[/size]'
                else:
                    yt_text = '[size=18sp][b]Setze eine Mine[/b] \n klicke dafür den Planeten an[/size]'
                self.app_view.your_turn_popup(
                    yt_text,
                    delay=(5 if (self.my_pos == 0 and self.initial_idx == 0) else 1) if self.num_players > 1 else 0,
                )
            else:
                if info is not None and isinstance(info, str):
                    # update status variable according to info
                    if info == c.NEED_CHOOSE_TECH:
                        self.choose_tech = True
                        self.app_view.switch_screen('research_board')
                    elif info == c.NEED_CHOOSE_TRACK:
                        self.choose_lvlup = True
                        self.app_view.switch_screen('research_board')
                    elif info == c.NEED_BUILD_MINE:
                        self.choose_mine_build = True
                        self.app_view.switch_screen('map')
                    elif info == c.NEED_CHOOSE_FED_BUILD:
                        self.choose_fed_build = True
                    elif info == c.NEED_CHOOSE_BLACK_PLANET:
                        self.choose_black_planet = True 
                        self.app_view.switch_screen('map')
                    elif info == c.ITAR_PLI:
                        self.app_view.show_itar_gaia_phase_btn()
                    if not info in [c.NEED_CHOOSE_FED_MARKER, c.NEW_ROUND]:
                        self.app_view.your_turn_popup(
                            title=f'Runde {self.round}', text=info
                        )
                # info contains more than just a string
                elif isinstance(info, tuple):
                    if info[0] == c.NEED_CHOOSE_BOOSTER and isinstance(info[1], list):
                        # open popup
                        self.round_booster_popup()
                else:
                    self.app_view.your_turn_popup(
                        title=f'Runde {self.round}', text='Mache eine Aktion oder passe'
                    )
        elif self.round == -1:
            title_text = 'Fraktionswahl'
            self.app_view.your_turn_popup(
                title=title_text,
                text=f'{self.player_names[self.player_at_turn]} ist dran',
            )
        if self.round > -1:
            self.app_view.update_pat_name()
                
    def recv_action(
        self,
        player,
        pi_list=None,
        gaia_map=None,
        used_p_and_q=None,
        avail_adv=None
    ):
        new_tech = None
        if (not isinstance(player, faction.Faction) or
            (gaia_map is not None and not isinstance(gaia_map, dict)) or
            (used_p_and_q is not None and not isinstance(used_p_and_q, set)) or
            (avail_adv is not None and not isinstance(avail_adv, set)) or
            (pi_list is not None and not isinstance(pi_list, list))):
            self.req_sync()
            return
        if player.pos == self.my_pos:
            if self.booster_phase:
                # booster choice was accepted so dismiss popup
                self.app_view.current_popup.dismiss()
                if (player.faction_type == c.ITAR and
                    player.pwr[3] == (self.players[self.my_pos].pwr[3] - 4) and
                    player.pwr[0] == self.players[self.my_pos].pwr[0]
                    ):
                    self.choose_tech = True
                    self.action_started = c.ITAR_PLI
                    self.app_view.your_turn_popup(c.NEED_CHOOSE_TECH)                   

            # remove status is necessary
            if len(player.tech_tiles) > len(self.players[self.my_pos].tech_tiles):
                self.action_started = None
                self.choose_tech = False
                self.choose_lvlup = False
                self.choose_cover = False
                self.tech_cache = None
                new_tech = set(player.tech_tiles).difference(set(self.players[self.my_pos].tech_tiles)).pop()
            else:
                for i in range(len(player.adv_tiles)):
                    # adv tech has been chosen and covers a standard tech tile
                    if player.adv_tiles[i] is not None and self.players[self.my_pos].adv_tiles[i] is None:
                        self.choose_tech = False
                        self.choose_cover = False
                        self.choose_lvlup = False
                        self.tech_cache = None
                        break
            for i in range(6):
                if player.research_branches[i] > self.players[self.my_pos].research_branches[i]:
                    self.choose_lvlup = False
                    self.action_started = None 
                    break
            if len(player.fed_markers) > len(self.players[self.my_pos].fed_markers):
                self.choose_fed_marker = False
                self.app_view.fed_m_popup.dismiss()
            if self.action_started == c.QIC_2_FED and (player.vcp > (self.players[self.my_pos].vcp + 5) or
                player.faction_type == c.GLEEN and (player.knw > self.players[self.my_pos].knw or
                    player.gld > self.players[self.my_pos].gld or
                    player.ore > self.players[self.my_pos].ore)
            ):
                # if player has gained victory points after starting QIC 2 FED, he has successfully
                # chosen a fed marker, so the action is finished
                self.action_started = None
                self.choose_fed_marker = False
                self.app_view.fed_m_popup.dismiss()
            if self.action_started == c.DER_SCHWARM_PLI:
                if len(player.ivit_sats) > len(self.players[self.my_pos].ivit_sats):
                    self.action_started = None
            if not (player.orange_used[2]  == self.players[self.my_pos].orange_used[2]):
                if player.orange_used[2]:
                    self.action_started = self.players[self.my_pos].current_booster
                    self.choose_mine_build = True
                    self.app_view.your_turn_popup(c.NEED_BUILD_MINE)
                else:
                    self.action_started = None
                    self.choose_mine_build = False
            if not player.orange_used[1]  == self.players[self.my_pos].orange_used[1]:
                if player.orange_used[1]:
                    if isinstance(player, faction.Ambas):
                        self.action_started = c.AMBAS_PLI
                        self.app_view.switch_screen('map')
                        self.app_view.your_turn_popup('Wähle den Planeten aus,\nauf den dein Regierungssitz soll')
                    if isinstance(player, faction.Firaks):
                        self.action_started = c.FIRAKS_PLI
                        self.app_view.switch_screen('map')
                        self.app_view.your_turn_popup('Wähle das Forschungslabor aus,\ndass du downgraden willst')
                    if isinstance(player, faction.MadAndroids):
                        self.action_started = c.MAD_ANDROIDS_SPECIAL
                        self.choose_lvlup = True
                        self.app_view.switch_screen('research_board')
                        self.app_view.your_turn_popup(c.NEED_CHOOSE_TRACK)
                    if isinstance(player, faction.DerSchwarm):
                        self.action_started = c.DER_SCHWARM_PLI
                        self.app_view.switch_screen('map')
                        self.app_view.your_turn_popup('Setze deine Raumstation\nauf ein freies Feld')
                else:
                    if self.action_started == c.MAD_ANDROIDS_SPECIAL:
                        self.choose_lvlup = False
                    self.action_started = None
            if  used_p_and_q is not None:
                 # if used_p_and_q is not a subset of old one, a new one has been used
                if not used_p_and_q.issubset(self.used_p_and_q):
                    new_used = used_p_and_q.difference(self.used_p_and_q)
                    if len(new_used) == 1:
                        action_type = new_used.pop()
                        if action_type in [c.PUB_2_TRF_1, c.PUB_2_TRF_2]:
                            self.action_started = action_type
                            self.choose_mine_build = True                            
                            
                            self.app_view.your_turn_popup(c.NEED_BUILD_MINE)
                        elif action_type == c.QIC_2_TEC:
                            self.action_started = action_type
                            self.choose_tech = True
                            self.app_view.your_turn_popup(c.NEED_CHOOSE_TECH)
                        elif action_type == c.QIC_2_FED:
                            self.action_started = action_type
                            self.choose_fed_marker= True
                            self.app_view.fed_marker_popup(self.players[self.player_at_turn].fed_markers)
                # an action has been canceled
                elif not self.used_p_and_q.issubset(used_p_and_q):
                    canceled = self.used_p_and_q.difference(used_p_and_q)
                    if len(canceled) == 1:
                        self.action_started = None
                        action_type = canceled.pop()
                        if action_type in [c.BOO_TER, c.BOO_NAV, c.PUB_2_TRF_1, c.PUB_2_TRF_2]:
                            self.choose_mine_build = False
                        elif action_type == c.QIC_2_TEC:
                            self.choose_tech = False
                        elif action_type == c.QIC_2_FED:
                            self.choose_fed_marker= False
                        self.app_view.your_turn_popup(c.CANCEL_ACTION)                  
        # check if lvl 5 is blocked
        for i in range(6):
            if player.research_branches[i] == 5:
                self.lvl_5_free[i] = False
        if not self.starting_player_set and player.has_finished and not self.players[player.pos].has_finished:
            self.starting_player_set = True
            self.starting_player = player.pos
                                                            
        self.players[player.pos] = player
        # update fed choice possible if player has gained the PIA tech        
        if new_tech == c.TEC_PIA:
            fed_possible = (self.players[player.pos].get_fed_possible(self.gaia_map) == c.POSSIBLE)
            self.app_view.update_map(self.gaia_map, fed_possible)
        if gaia_map is not None:
            map_diff = DeepDiff(self.gaia_map, gaia_map, ignore_type_in_groups=[(None, 1), (None, 'str')]).to_dict()
            if 'values_changed' in map_diff:
                for diff_item in map_diff['values_changed'].items():
                    # check if owner field (pos 1) has changed to my pos
                    if (diff_item[1] == {'new_value': self.my_pos, 'old_value': None} and 
                    diff_item[0][-2] == '1'):
                        self.choose_mine_build = False
                        if self.action_started in [c.PUB_2_TRF_1, c.PUB_2_TRF_2, c.BOO_TER, c.BOO_NAV]:
                            self.action_started = None
                            self.app_view.root.get_screen('board').boo_action_started = False
                        break                        
                    # check if ambas pli change has happend
                    if isinstance(player, faction.Ambas):
                        if (diff_item[1] == {'new_value': c.MINE, 'old_value': c.PLANETARY_INSTITUTE} and 
                            diff_item[0][-2] == '2'):
                            self.action_started = None
            if 'dictionary_item_added' in map_diff:
                new_tech =c.POSSIBLE
                for diff_item in map_diff['dictionary_item_added']:
                    q = int(diff_item[(diff_item.find('[') + 1):diff_item.find(']')])
                    r = int(diff_item[(diff_item.find(']') + 2):-1])
                    if gaia_map[(q,r)][0] == c.BLACK_PLANET:
                        self.app_view.root.get_screen('map').place_black_planet(q,r, gaia_map)
                        self.choose_black_planet = False
            self.gaia_map = gaia_map
            fed_possible = (self.players[self.my_pos].get_fed_possible(self.gaia_map) == c.POSSIBLE)
            self.app_view.update_map(gaia_map, fed_possible)
            if self.booster_phase:
                self.app_view.root.get_screen('map').update_gaia(self.gaia_map)
            if pi_list is not None:
                self.pi_list = pi_list
                possible_passive_income = pi_list[self.my_pos]
                if possible_passive_income:
                    if possible_passive_income > 1:
                        vcp_after = self.players[self.my_pos].vcp - possible_passive_income + 1
                        self.app_view.passive_income(possible_passive_income, vcp_after)
                    else:
                        self.app_view.your_turn_popup(text='Du hast automatisch 1 Macht erhalten', title='Passiver Machtgewinn')
                        self.do_passive_income()  
        if used_p_and_q is not None:
            self.used_p_and_q = used_p_and_q
        if avail_adv is not None:
            self.avail_adv = avail_adv
        self.app_view.update_resources()

    def recv_end_round(self, players):
        if isinstance(players, list):
            for p in players:
                if not isinstance(p, faction.Faction):
                    return
            self.players = players
            self.round += 1
            if self.round < 7:
                self.booster_phase = True
            else:
                self.player_at_turn = -1
                # game is finished, display end results
                self.app_view.root.get_screen('research_board').show_final_score()
           

    # functions for direct communication between network and view
    def add_player_to_view(self, player_name):
        self.app_view.root.get_screen('waiting').add_player(player_name)


if __name__ == '__main__':
    Gaia()
