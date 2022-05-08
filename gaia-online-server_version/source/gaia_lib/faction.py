import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from gaia_lib import constants as c
from gaia_lib import maptools


class Faction:
    '''Top-Class'''

    def __init__(self, name, pos, color, faction_type, tf_table):
        # General:
        self.name = name
        self.pos = pos
        self.color = color
        self.faction_type = faction_type
        self.tf_table = tf_table
        # values copied from gaia instance to work without reference to it
        # TODO fix this
        self.level_fives = [None] * 6
        # Resources:
        self.inc_ore = [1, 2, 3, 3, 4, 5, 6, 7, 8]
        self.inc_gld = [0, 3, 7, 11, 16]
        self.inc_knw = [1, 2, 3, 4]
        self.inc_res = [0] * 6  # Amount of income per resource per round [ore, gold, knowledge, qic, power, powerstone]
        self.ore = 4  # Standard Amount of Ore
        self.gld = 15  # Standard Amount of Gold
        self.knw = 3  # Standard Amount of Ore
        self.qic = 1  # Standard Amount of Q.I.C.s
        self.pwr = [
            2,
            4,
            0,
            0,
        ]  # Standard Amount of available power [Sector 1, Sector 2, Sector 3, Gaia Sector]
        # Research:
        self.research_branches = [0] * 6
        # Buildings:
        self.mne = 8  # Standard Amount of free Mines.
        self.trd = 4  # Standard Amount of free Trading Stations.
        self.lab = 3  # Standard Amount of free Research Labs.
        self.pli_built = False  # Planetary Institute build?
        self.left_ac_built = False  # Left University build?
        self.right_ac_built = False
        # Range and terraforming:
        self.range = 1  # Standard Range
        self.tf_cost = 3  # The Amount of Ores needed for one Terraforming step.
        # Gaiaforming:
        self.gfm = 0  # Standard Amount of available Gaiaformers
        self.gfm_in_gaia = 0
        self.gfm_pws_needed = 6
        # Other:
        self.vcp = 10  # Standard Amount of Victory Points
        self.end_details = {}
        self.fed_markers = []  # The Alliance Markers the player will gather
        self.green_fed_markers = 0  # Amount of green alliance markers.
        self.current_booster, self.round_goal = None, None
        self.orange_used = [
            False
        ] * 7  # [c.RIGHT_ACADEMY, c.PLANETARY_INSTITUTE, Rundenbooster, c.TEC_POW, c.ADV_QIC, c.ADV_ORE, c.ADV_KNW]
        self.satellites = set()
        self.tech_tiles = []
        self.adv_tiles = []
        # Boolean:
        self.has_finished = False
        self.free_tf = 0  # Amount of temporarily free terraforming steps.
        self.free_range = 0  # Amount of temporarily free range.

    def income_phase(self, round_goal):
        '''Handles income phase for a player.'''
        # Gain Resources by Faction Board.
        self.ore += self.inc_ore[8 - self.mne]
        self.gld += self.inc_gld[4 - self.trd]
        self.knw += self.inc_knw[3 - self.lab]
        if self.left_ac_built:
            self.knw += 2
        # Resource income by tech, research, etc.
        self.ore += self.inc_res[0]
        self.gld += self.inc_res[1]
        self.knw += self.inc_res[2]
        self.qic += self.inc_res[3]
        # Resource income by booster.
        leftover_pwr_movement = 0        
        if self.current_booster == c.BOO_GAI:
            self.gld += 4
        elif self.current_booster == c.BOO_LAB:
            self.knw += 1
        elif self.current_booster == c.BOO_MIN:
            self.ore += 1
        elif self.current_booster == c.BOO_NAV:
            leftover_pwr_movement += self.handle_pwr_movement(2)
        elif self.current_booster == c.BOO_PIA:
            leftover_pwr_movement += self.handle_pwr_movement(4)
        elif self.current_booster == c.BOO_TER:
            self.gld += 2
        elif self.current_booster == c.BOO_TRS:
            self.ore += 1
        elif self.current_booster == c.BOO_KNW:
            self.ore += 1
            self.knw += 1
        elif self.current_booster == c.BOO_PWT:
            self.pwr[0] += 2
            self.ore += 1
        elif self.current_booster == c.BOO_QIC:
            self.gld += 2
            self.qic += 1
        # Gain Power.
        leftover_pwr_movement += self.handle_pwr_movement(self.inc_res[4])
        new_stones = self.inc_res[5]
        # algorithm to maximize pwr stones in level 3
        while leftover_pwr_movement > 0:
            if new_stones > 0:
                self.pwr[0] += 1
                new_stones -= 1
                leftover_pwr_movement = self.handle_pwr_movement(leftover_pwr_movement)
            else:
                break
        self.pwr[0] += new_stones

        self.ore = min(self.ore, 15)
        self.gld = min(self.gld, 30)
        self.knw = min(self.knw, 15)

        self.orange_used = [False] * 7
        self.round_goal = round_goal
        return

    def gaia_phase(self):
        '''Handles gaia phase for a player. To be modified for some faction.'''
        self.pwr[0] += self.pwr[3]
        self.pwr[3] = 0
        self.gfm += self.gfm_in_gaia
        self.gfm_in_gaia = 0
        return

    def end_round_phase(self, gaia_map):
        ''' Handle end of round (add victory points by boosters or tech tiles). '''
        if c.ADV_FEDP in self.tech_tiles:
            self.vcp += 3 * len(self.fed_markers)
        if c.ADV_LAB in self.tech_tiles:
            self.vcp += 3 * (3 - self.lab)
        if c.ADV_TYP in self.tech_tiles:
            self.vcp += self.get_different_planet_types(gaia_map)
        if self.current_booster == c.BOO_GAI:
            self.vcp += self.get_amount_gaia_planets(gaia_map)
        if self.current_booster == c.BOO_LAB:
            self.vcp += 3 * (3 - self.lab)
        if self.current_booster == c.BOO_MIN:
            self.vcp += 8 - self.mne
        if self.current_booster == c.BOO_PIA:
            self.vcp += 4 * (self.left_ac_built + self.right_ac_built + self.pli_built)
        if self.current_booster == c.BOO_TRS:
            self.vcp += 2 * (4 - self.trd)
        self.has_finished = False
        self.current_booster = None

    def finish_game_phase(self):
        self.end_details['ingame'] = self.vcp
        # accumulate resources in gold to calculate vcp gain
        acc_res = self.gld
        acc_res += self.ore
        acc_res += self.knw
        acc_res += self.qic
        acc_res += self.pwr[2]
        acc_res = int(acc_res/3)
        self.vcp += acc_res
        self.end_details['acc_res'] = acc_res
        # calculate vcp gained through research
        acc_lvl = 0
        for lvl in self.research_branches:
            if lvl > 2:
                acc_lvl += 4*(lvl - 2)
        self.vcp += acc_lvl
        self.end_details['acc_lvl'] = acc_lvl
        


    # Power:
    def handle_pwr_movement(self, moves):
        '''Handle general power movement. Returns leftover movement'''
        diff = min(moves, self.pwr[0])  # 1 to 2.
        moves -= diff
        self.pwr[0] -= diff
        self.pwr[1] += diff
        diff = min(moves, self.pwr[1])  # 2 to 3.
        self.pwr[1] -= diff
        self.pwr[2] += diff
        moves -= diff
        return moves

    def pay_power(self, amount):
        self.pwr[2] -= amount
        self.pwr[0] += amount

    def remove_power_stones(self, amount):
        removed = min(self.pwr[0], amount)
        self.pwr[0] -= removed
        amount -= removed
        removed = min(amount, self.pwr[1])
        self.pwr[1] -= removed
        amount -= removed
        removed = min(amount, self.pwr[2])
        self.pwr[2] -= removed

    def passive_income_possible(self, q, r, map_items):
        '''Gets called if other player built on q, r. Returns possible passive income for players self.
        0 means not possible.'''
        income = 0
        for pos, planet in map_items:
            if (maptools.hex_distance(q, r, pos[0], pos[1]) <= 2
                and planet[1] == self.pos):
                income = max(income, self.get_power_value({pos: planet}))
        # Maximum power movements possible = self.pwr[0] * 2 + self.pwr[1]
        income = min(income, self.pwr[0] * 2 + self.pwr[1])  
        income
        return income

    def execute_passive_income(self, pi_value):
        ''' Gets called if player would like to receive passive income. 
        Execute passive income.'''
        self.vcp -= pi_value - 1
        self.handle_pwr_movement(pi_value)

    def build_mine_possible(self, q, r, gaia_map, initial=False):
        planet = gaia_map[(q,r)]
        planet_type = planet[0]
        if initial:
            # check if player tries to build on a home planet
            if planet_type == self.color:
                if planet[1] == None:                
                    return c.POSSIBLE
                return c.NOT_POSSIBLE
            return c.INIT_NOT_HOME_PLANET
        else:
            if self.mne == 0 and planet[0] != c.TRANSDIM:
                return c.NO_MORE_FREE_BUILDINGS
            if self.is_in_range(q, r, gaia_map) == c.OUT_OF_RANGE:
                return c.OUT_OF_RANGE
            if planet_type == c.TRANSDIM_GFM:
                return c.NOT_POSSIBLE
            if planet[1] != None and planet_type != c.GAIAFORMED:
                return c.NOT_OWNED_BY_YOU
            # Gaiaforming:
            if planet_type == c.TRANSDIM:
                if (self.pwr[0] + self.pwr[1] + self.pwr[2]) < self.gfm_pws_needed:
                    return c.NOT_ENOUGH_POWERSTONES
                if self.gfm < 1:
                    return c.NO_MORE_FREE_GAIAFORMERS                
                return c.POSSIBLE
            if planet_type == c.GAIAFORMED:
                if planet[1] != self.pos:
                    return c.NOT_POSSIBLE
                if self.ore < 1 or self.gld < 2:
                    return c.NOT_ENOUGH_RESOURCES
                return c.POSSIBLE
            if planet_type == c.GAIA:
                if self.qic < 1 or self.gld < 2 or self.ore < 1:
                    return c.NOT_ENOUGH_RESOURCES
                return c.POSSIBLE
            if planet_type not in [c.GAIA, c.TRANSDIM, c.TRANSDIM_GFM]:
                cost_ore = (
                    1 + max(0, self.tf_table[planet_type] - self.free_tf) * self.tf_cost
                )
                if self.ore < cost_ore or self.gld < 2:
                    return c.NOT_ENOUGH_RESOURCES
                return c.POSSIBLE            
    
    # Construction business:
    def build_mine(self, q, r, gaia_map, initial=False):
        ''' this function tries to build a mine and removes resources if possible '''
        planet = gaia_map[(q,r)]
        planet_type = planet[0]
        if initial:            
            self.mne -= 1
            planet[1] = self.pos
            planet[2] = c.MINE 
            return 
        else:
            # Gaiaforming:
            if planet_type == c.TRANSDIM:
                planet[1] = self.pos
                planet[0] = c.TRANSDIM_GFM
                planet[2] = c.GAIAFORMER
                # remove resources                
                self.remove_power_stones(self.gfm_pws_needed)
                self.pwr[3] += self.gfm_pws_needed
                self.gfm -= 1
                return
            # Mine Placing on different planets (gold cost and mine is after conditions for ore)
            elif planet_type == c.GAIAFORMED:
                # return gaiaformer
                self.ore -= 1
                self.gfm += 1
            elif planet_type == c.GAIA:
                self.qic -= 1
                self.ore -= 1
                if c.TEC_GAI in self.tech_tiles:
                    self.vcp += 3
                if self.round_goal == c.RND_GAI3:
                    self.vcp += 3
                if self.round_goal == c.RND_GAI4:
                    self.vcp += 4
            else:
                cost_ore = (
                    1 + max(0, self.tf_table[planet_type] - self.free_tf) * self.tf_cost
                )
                self.ore -= cost_ore
            # this holds true for all planet types (except transdim which does not reach this code)
            self.gld -= 2
            self.mne -= 1
            if c.ADV_MINB in self.tech_tiles:
                self.vcp += 3
            if self.round_goal == c.RND_MIN:
                self.vcp += 2
            if self.round_goal == c.RND_TER:
                self.vcp += self.tf_table[planet_type] * 2
            self.free_range = 0
            self.free_tf = 0
            planet[1] = self.pos
            planet[2] = c.MINE
            return

    def black_planet_possible(self, gaia_map, q, r):
        if self.research_branches[1] < 5:
            return c.NOT_POSSIBLE
        if (q,r) in gaia_map:
            return c.CANT_PLACE_HERE            
        if self.is_in_range(q, r, gaia_map) == c.OUT_OF_RANGE:
            return c.OUT_OF_RANGE
        return c.POSSIBLE
        

    def execute_black_planet(self, q, r):        
        if c.ADV_MINB in self.tech_tiles:
            self.vcp += 3
        if self.round_goal == c.RND_MIN:
            self.vcp += 2
        self.free_range = 0


    def upgrade_building_possible(self, q, r, gaia_map, decision=None):
        '''Try to upgrade existing building to new_building_type.
        decision= PLI or LAB.
        decision= LEFT_ACADEMY or RIGHT_ACADEMY.'''
        planet = gaia_map[(q,r)]
        if planet[1] != self.pos:
            return c.NOT_OWNED_BY_YOU
        if planet[0] == c.BLACK_PLANET:
            return c.FULLY_UPGRADED
        old_type = planet[2]
        if old_type == c.GAIAFORMER:
            if planet[0] != c.GAIAFORMED:
                return c.NOT_POSSIBLE
            return self.build_mine_possible(q, r, gaia_map)
        if old_type == c.MINE:
            if self.trd == 0:
                return c.NO_MORE_FREE_BUILDINGS
            cost_gld = 3 if self.are_neighbors_nearby(q, r, gaia_map) else 6
            if self.gld >= cost_gld and self.ore >= 2:
                return c.POSSIBLE
            else:
                return c.NOT_ENOUGH_RESOURCES
        if old_type == c.TRADING_STATION:
            if self.pli_built and self.lab == 0:
                return c.NO_MORE_FREE_BUILDINGS
            if self.pli_built:
                decision = c.LAB
            if self.lab == 0:
                decision = c.PLANETARY_INSTITUTE
            if decision == None:
                return c.NEED_FEEDBACK_TRD
            if decision == c.PLANETARY_INSTITUTE:
                if self.pli_built:
                    return c.NOT_POSSIBLE
                if self.gld >= 6 and self.ore >= 4:                    
                    return c.POSSIBLE
                return c.NOT_ENOUGH_RESOURCES
            else:  # LAB
                if self.lab == 0:
                    return c.NO_MORE_FREE_BUILDINGS
                if self.gld >= 5 and self.ore >= 3:
                    return c.POSSIBLE_CHOOSE_TECH
                return c.NOT_ENOUGH_RESOURCES            
        if old_type == c.LAB:
            if self.left_ac_built and self.right_ac_built:
                return c.NO_MORE_FREE_BUILDINGS
            if not (self.left_ac_built or self.right_ac_built or decision):
                return c.NEED_FEEDBACK_AC
            if self.gld >= 6 and self.ore >= 6:
                return c.POSSIBLE_CHOOSE_TECH
            return c.NOT_ENOUGH_RESOURCES
        else:
            return c.FULLY_UPGRADED


    def upgrade_building(self, q, r, gaia_map, decision):
        '''Try to upgrade existing building to new_building_type.
        decision= PLI or LAB.
        decision= LEFT_ACADEMY or RIGHT_ACADEMY.'''
        planet=gaia_map[(q,r)]
        old_type = planet[2]
        if old_type == c.GAIAFORMER:
            return self.build_mine(q, r, gaia_map)
        if old_type == c.MINE:
            cost_gld = 3 if self.are_neighbors_nearby(q, r, gaia_map) else 6
            self.gld -= cost_gld
            self.ore -= 2
            self.mne += 1
            self.trd -= 1
            planet[2] = c.TRADING_STATION
            if c.ADV_TRSB in self.tech_tiles:
                self.vcp += 3
            if self.round_goal == c.RND_TRS3:
                self.vcp += 3
            if self.round_goal == c.RND_TRS4:
                self.vcp += 4
            return
        elif old_type == c.TRADING_STATION:
            # decision is None if there is no more option
            if self.pli_built:
                decision == c.LAB
            if not self.lab:
                decision == c.PLANETARY_INSTITUTE
            if decision == c.PLANETARY_INSTITUTE:
                self.gld -= 6
                self.ore -= 4
                self.trd += 1
                self.pli_built = True
                self.activate_pli()
                planet[2] = c.PLANETARY_INSTITUTE
                if self.round_goal == c.RND_PIA:
                    self.vcp += 5
                return
            else:  # LAB               
                self.gld -= 5
                self.ore -= 3
                self.trd += 1
                self.lab -= 1
                planet[2] = c.LAB
                return             
        if old_type == c.LAB:
            self.gld -= 6
            self.ore -= 6
            self.lab += 1
            planet[2] = c.ACADEMY
            if self.round_goal == c.RND_PIA:
                self.vcp += 5            
            # decision is None if there is no more option
            if self.left_ac_built:
                decision = c.RIGHT_ACADEMY
            elif self.right_ac_built:
                decision = c.LEFT_ACADEMY
            if decision == c.RIGHT_ACADEMY:                
                self.right_ac_built = True                
            else:  # Left Academy
                self.left_ac_built = True          
            return  

    def activate_pli(self):
        ''' this behavior is defined in the faction the player has chosen'''
        pass

    # Research and Techs:
    def tech_tile_possible(self, tile, avail_adv=None, adv_idx=None, index=None, lvl_5_free = None, cover=None):
        if tile in self.tech_tiles:
            return c.TECH_NOT_AVAILABLE
        if tile in c.ADVANCED_TECH_TILES:
            if tile not in avail_adv:
                return c.TECH_NOT_AVAILABLE
            if self.research_branches[adv_idx] < 4:
                return c.TECH_NOT_AVAILABLE
            if self.green_fed_markers < 1:
                return c.TECH_NOT_AVAILABLE
            if cover is not None and cover in self.tech_tiles:
                idx = list.index(self.tech_tiles, cover)
                if self.adv_tiles[idx] is None:
                    if index is not None and 0 <= index and index < 6 and lvl_5_free is not None:
                        output = self.level_up_possible(index, lvl_5_free, False)
                        if output in [c.POSSIBLE_TURN_MARKER_GRAY, c.POSSIBLE]:
                            return c.POSSIBLE
                        else:                    
                            return c.POSSIBLE_NO_LVL_UP
                    else:
                        return c.NEED_CHOOSE_TRACK
                else:
                    return c.NOT_POSSIBLE
            else:
                return c.NEED_CHOOSE_COVER

        else:
            if index is not None and 0 <= index and index < 6:
                output = self.level_up_possible(index, lvl_5_free, False)
                if output in [c.POSSIBLE_TURN_MARKER_GRAY, c.POSSIBLE]:
                    return c.POSSIBLE
                else:                    
                    return c.POSSIBLE_NO_LVL_UP
                    
            else:
                return c.NEED_CHOOSE_TRACK

    def execute_tech_tile(self, gaia_map, tile, cover=None):
        ''' Gets called if player chose the tech tile. '''
        if cover is None:
            # its a basic tech tile
            self.tech_tiles.append(tile)
            self.adv_tiles.append(None)
            if tile == c.TEC_CRE:
                self.inc_res[1] += 4
            elif tile == c.TEC_VPS:
                self.vcp += 7
            elif tile == c.TEC_TYP:
                self.knw = min(self.knw + self.get_different_planet_types(gaia_map), 15)
            elif tile == c.TEC_KNW:
                self.inc_res[1] += 1
                self.inc_res[2] += 1
            elif tile == c.TEC_ORE:
                self.inc_res[0] += 1
                self.inc_res[4] += 1
            elif tile == c.TEC_QIC:
                self.ore = min(self.ore + 1, 15)
                self.qic += 1
        else:
            # Advanced:
            # cover chosen tile with advanced tile
            self.adv_tiles[list.index(self.tech_tiles, cover)] = tile
            self.green_fed_markers -= 1
            if tile == c.ADV_FEDV:
                self.vcp += 5 * len(self.fed_markers)
            elif tile == c.ADV_GAI:
                self.vcp += 2 * self.get_amount_gaia_planets(gaia_map)
            elif tile == c.ADV_MINV:
                self.vcp += 2 * (8 - self.mne)
            elif tile == c.ADV_SECO:
                self.ore = min(self.ore + self.get_amount_sectors(gaia_map), 15)
            elif tile == c.ADV_SECV:
                self.vcp += 2 * self.get_amount_sectors(gaia_map)
            elif tile == c.ADV_TRSV:
                self.vcp += 4 * (4 - self.trd)

    def level_up_possible(self, index, lvl_5_free, need_resources=True):
        if need_resources and self.knw < 4:
            return c.NOT_ENOUGH_RESOURCES
        if self.research_branches[index] == 5:
            return c.NOT_POSSIBLE
        if self.research_branches[index] == 4:
            if self.green_fed_markers < 1 or not lvl_5_free[index]:
                return c.NOT_POSSIBLE
            return c.POSSIBLE_TURN_MARKER_GRAY
        return c.POSSIBLE

    def execute_level_up(self, index, gaia_map, need_resources=True):
        if need_resources:
            self.knw -= 4
        if self.research_branches[index] == 4:
            self.green_fed_markers -= 1
        if self.research_branches[index] <= 4:
            self.research_branches[index] += 1
        # Execute gains:
        new_level = self.research_branches[index]
        if new_level == 3:  # After leveling up.
            self.handle_pwr_movement(3)
        if index == 0:
            if new_level == 1:
                self.ore = min(self.ore + 2, 15)
            elif new_level == 2:
                self.tf_cost = 2
            elif new_level == 3:
                self.tf_cost = 1
            elif new_level == 4:
                self.ore = min(self.ore + 2, 15)
            elif new_level == 5:
                pass # fed marker is added in GaiaServer
        elif index == 1:
            if new_level == 1:
                self.qic += 1
            elif new_level == 2:
                self.range = 2
            elif new_level == 3:
                self.qic += 1
            elif new_level == 4:
                self.range = 3
            elif new_level == 5:
                self.range = 4
        elif index == 2:
            if new_level == 1:
                self.qic += 1
            elif new_level == 2:
                self.qic += 1
            elif new_level == 3:
                self.qic += 2
            elif new_level == 4:
                self.qic += 2
            elif new_level == 5:
                self.qic += 4
        elif index == 3:
            if new_level == 1:
                self.gfm = 1
            elif new_level == 2:
                self.pwr[0] += 3
            elif new_level == 3:
                self.gfm += 1
                self.gfm_pws_needed = 4
            elif new_level == 4:
                self.gfm += 1
                self.gfm_pws_needed = 3
            elif new_level == 5:
                self.vcp += self.get_amount_gaia_planets(gaia_map) + 4
        elif index == 4:
            if new_level == 1:
                self.inc_res[1] += 2
                self.inc_res[4] += 1
            elif new_level == 2:
                self.inc_res[0] += 1
                self.inc_res[4] += 1
            elif new_level == 3:
                self.inc_res[1] += 1
                self.inc_res[4] += 1
            elif new_level == 4:
                self.inc_res[0] += 1
                self.inc_res[1] += 1
                self.inc_res[4] += 1
            elif new_level == 5:
                self.inc_res[0] -= 2
                self.inc_res[1] -= 4
                self.inc_res[4] -= 4
                self.ore = min(self.ore + 3, 15)
                self.gld = min(self.gld + 6, 30)
                self.handle_pwr_movement(6)
        elif index == 5:
            if new_level == 1:
                self.inc_res[2] += 1
            elif new_level == 2:
                self.inc_res[2] += 1
            elif new_level == 3:
                self.inc_res[2] += 1
            elif new_level == 4:
                self.inc_res[2] += 1
            elif new_level == 5:
                self.knw = min(self.knw + 9, 15)
                self.inc_res[2] -= 4
        # Round goal bonus:
        if self.round_goal == c.RND_STP:
            self.vcp += 2


    # Federation stuff:
    def execute_build_fed(self, sats):
        self.remove_power_stones(len(sats))
        self.satellites.update(sats)

    def add_fed_marker(self, fed_marker):
        self.fed_markers.append(fed_marker)
        self.execute_fed_marker(fed_marker)
        if not fed_marker == c.FED_VPS:
            self.green_fed_markers += 1
        if self.round_goal == c.RND_FED:
            self.vcp += 5

    def execute_fed_marker(self, marker):
        if marker == c.FED_CRE:
            self.gld = min(30, self.gld + 6)
            self.vcp += 7
        if marker == c.FED_KNW:
            self.knw = min(15, self.knw + 2)
            self.vcp += 6
        elif marker == c.FED_PWT:
            self.pwr[0] += 2
            self.vcp += 8
        elif marker == c.FED_QIC:
            self.qic += 1
            self.vcp += 8
        elif marker == c.FED_ORE:
            self.ore = min(15, self.ore + 2)
            self.vcp += 7
        elif marker == c.FED_VPS:
            self.vcp += 12
        elif marker == c.FED_GLE:
            self.ore = min(self.ore + 1, 15)
            self.knw = min(self.knw + 1, 15)
            self.gld = min(self.gld + 2, 30)



    # Gaiaforming:
    def gaiaform(self, q, r, gaia_map):
        ''' Gaiaform a transdim planet. To be modified for Taklons. '''
        if self.gfm == 0:
            return c.NO_MORE_FREE_GAIAFORMERS
        if self.is_in_range(q, r, gaia_map) == c.OUT_OF_RANGE:
            return c.OUT_OF_RANGE
        if self.pwr[0] + self.pwr[1] + self.pwr[2] < self.gfm_pws_needed:
            return c.NOT_ENOUGH_POWERSTONES
        demand = self.gfm_pws_needed
        self.pwr[3] += demand
        value = min(demand, self.pwr[0])
        demand -= value
        self.pwr[0] -= value
        value = min(demand, self.pwr[1])
        demand -= value
        self.pwr[1] -= value
        value = min(demand, self.pwr[2])
        demand -= value
        self.pwr[2] -= value
        self.gfm -= 1
        self.free_range = 0
        return c.SUCCESS

    # Research board public actions and orange buttons:
    def p_and_q_possible(self, action_type):
        '''Power and Q.I.C. Actions on research board. For some indexes, another function
        must get called (in view.py) after c.SUCCESS return'''
        if action_type == c.PUB_2_KNW_3:
            if self.pwr[2] < 7:
                return c.NOT_ENOUGH_RESOURCES            
        elif action_type == c.PUB_2_TRF_2:
            if self.pwr[2] < 5:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.PUB_2_ORE:
            if self.pwr[2] < 4:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.PUB_2_GLD:
            if self.pwr[2] < 4:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.PUB_2_KNW_2:
            if self.pwr[2] < 4:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.PUB_2_TRF_1:
            if self.pwr[2] < 3:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.PUB_2_PWS:
            if self.pwr[2] < 3:
                return c.NOT_ENOUGH_RESOURCES
        # Q.I.C. Actions:
        elif action_type == c.QIC_2_TEC:
            if self.qic < 4:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.QIC_2_FED:
            if self.qic < 3:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.QIC_2_VPS:
            if self.qic < 2:
                return c.NOT_ENOUGH_RESOURCES
        else:
            return c.NOT_POSSIBLE
        return c.POSSIBLE

    def execute_p_and_q(self, gaia_map, action_type):
        '''Power and Q.I.C. Actions on research board. For some indexes, another function
        must get called (in view.py) after c.SUCCESS return'''
        if action_type == c.PUB_2_KNW_3:
            self.pay_power(7)
            self.knw = min(15, self.knw + 3)
        elif action_type == c.PUB_2_TRF_2:
            self.pay_power(5)
            self.free_tf = 2
        elif action_type == c.PUB_2_ORE:
            self.pay_power(4)
            self.ore = min(self.ore + 2, 15)
        elif action_type == c.PUB_2_GLD:
            self.pay_power(4)
            self.gld = min(self.gld + 7, 30)
        elif action_type == c.PUB_2_KNW_2:
            self.pay_power(4)
            self.knw = min(self.knw + 2, 15)
        elif action_type == c.PUB_2_TRF_1:
            self.pay_power(3)
            self.free_tf = 1
        elif action_type == c.PUB_2_PWS:
            self.pay_power(3)
            self.pwr[0] += 2
        # Q.I.C. Actions:
        elif action_type == c.QIC_2_TEC:
            self.qic -= 4
        elif action_type == c.QIC_2_FED:
            self.qic -= 3
        elif action_type == c.QIC_2_VPS:
            self.qic -= 2
            self.vcp += 3 + self.get_different_planet_types(gaia_map)

    def execute_cancel_action(self, action_type):
        if action_type == c.BOO_TER:
            self.orange_used[2] = False
            self.free_tf = max(0, (self.free_tf - 1))        
        elif action_type == c.BOO_NAV:
            self.orange_used[2] = False
            self.free_range = max(0, (self.free_range - 3))
        else:
            if action_type == c.PUB_2_TRF_1:
                self.free_tf = max(0, (self.free_tf - 1)) 
                self.pwr[2] += 3
                self.pwr[0] -= 3
            elif action_type == c.PUB_2_TRF_2:
                self.free_tf = max(0, (self.free_tf - 2)) 
                self.pwr[2] += 5
                self.pwr[0] -= 5
            elif action_type == c.QIC_2_FED:
                self.qic += 3                
            elif action_type == c.QIC_2_TEC:
                self.qic += 4

    def booster_action_possible(self, boo_type):
        if boo_type in [c.BOO_TER, c.BOO_NAV]:
            if self.current_booster == boo_type:
                if self.orange_used[2]:
                    return c.ALREADY_USED
                else:
                    return c.POSSIBLE
        return c.NOT_POSSIBLE

    def execute_booster_action(self):
        self.orange_used[2] = True
        if self.current_booster == c.BOO_TER:
            self.free_tf += 1
        elif self.current_booster == c.BOO_NAV:
            self.free_range += 3

    def tech_action_possible(self, tech_type):
        if tech_type not in [c.TEC_POW, c.ADV_QIC, c.ADV_ORE, c.ADV_KNW]:
            return c.NOT_POSSIBLE
        if tech_type == c.TEC_POW and not self.orange_used[3]:
            return c.POSSIBLE
        elif tech_type == c.ADV_QIC and not self.orange_used[4]:
            return c.POSSIBLE
        elif tech_type == c.ADV_ORE and not self.orange_used[5]:
            return c.POSSIBLE
        elif tech_type == c.ADV_KNW and not self.orange_used[6]:
            return c.POSSIBLE    
        return c.ALREADY_USED

    def execute_tech_action(self, tech_type):
        if tech_type == c.TEC_POW:
            self.handle_pwr_movement(4)
            self.orange_used[3] = True
        if tech_type == c.ADV_QIC:
            self.gld = min(30, self.gld + 5)
            self.qic += 1
            self.orange_used[4] = True
        if tech_type == c.ADV_ORE:            
            self.ore = min(15, self.ore + 3)
            self.orange_used[5] = True
        if tech_type == c.ADV_KNW:
            self.knw = min(15, self.knw + 3)
            self.orange_used[6] = True

    def ac_action_possible(self):
        if self.orange_used[0]:
            return c.ALREADY_USED
        elif self.right_ac_built:
            return c.POSSIBLE
        else:
            return c.NOT_POSSIBLE

    def execute_ac_action(self):
        self.qic += 1
        self.orange_used[0] = True

    # Range stuff:
    def is_in_range(self, q, r, gaia_map):
        my_planets = self.get_buildings(gaia_map).keys()
        for my_pos in my_planets:
            if (
                maptools.hex_distance(my_pos[0], my_pos[1], q, r)
                <= self.range + self.free_range
            ):
                return True
        return c.OUT_OF_RANGE

    def are_neighbors_nearby(self, my_q, my_r, gaia_map):
        ''' Check whether colonized planets of other players are in range 2 of my_q, r. '''
        for pos, planet in gaia_map.items():
            q, r = pos
            if (
                not (planet[1] is None)
                and planet[1] != self.pos
                and maptools.hex_distance(
                    q, r, my_q, my_r
                )
                <= 2
            ):
                return True
        return False

    

    # 'Getter' functions:
    def get_buildings(self, gaia_map, exclude_fed=False, no_gfm=False):
        ''' Returns subdictionary of map containing only containing planets owned by player himself. '''
        my_map = {}
        for pos, planet in gaia_map.items():
            if (
                planet[1] == self.pos
                and not (exclude_fed and planet[3])
                and not (no_gfm and planet[2] == c.GAIAFORMER)
            ):
                my_map[pos] = planet
        return my_map

    def get_different_planet_types(self, gaia_map, ret_list = False):
        ''' Return amount of different planet types colonized by player. '''
        my_map, my_types = self.get_buildings(gaia_map), set()
        for planet in my_map.values():
            if planet[1] == self.pos:
                if planet[0] == c.GAIAFORMED:
                    my_types.add(c.GAIA)
                elif planet[0] not in [c.TRANSDIM, c.TRANSDIM_GFM]:
                    my_types.add(planet[0])
        return len(my_types) if not ret_list else my_types

    def get_amount_gaia_planets(self, gaia_map):
        ''' Return amount of gaia planets colonized by player. '''
        my_map, amount = self.get_buildings(gaia_map), 0
        for planet in my_map.values():
            if planet[1] == self.pos and planet[0] in [c.GAIA, c.GAIAFORMED] and not planet[2] == c.GAIAFORMER:
                amount += 1
        return amount

    def get_amount_sectors(self, gaia_map):
        ''' Calculate and return the amount of dfferent sectors colonized by player. '''
        my_map, my_sectors = self.get_buildings(gaia_map), set()
        for pos in my_map.keys():
            my_sectors.add(maptools.get_sector(pos[0], pos[1])[2])
        return len(my_sectors)

    def get_power_value(self, submap):
        ''' Returns power value of buildings in submap. '''
        value = 0
        for planet in submap.values():
            if planet[2] == c.MINE:
                value += 1
            elif planet[2] == c.TRADING_STATION or planet[2] == c.LAB:
                value += 2
            elif planet[2] == c.PLANETARY_INSTITUTE or planet[2] == c.ACADEMY:
                value += 4 if c.TEC_PIA in self.tech_tiles else 3
        return value

    def get_fed_possible(self, gaia_map, num_sats=None, submap=None):
        if submap == None:
            submap = self.get_buildings(gaia_map, exclude_fed=True)
        if num_sats is None:
            if self.get_power_value(submap) > 6:
                return c.POSSIBLE
            return c.FED_IMPOSSIBLE
        else:
            if self.get_power_value(submap) > 6:
                if (self.pwr[0] + self.pwr[1] + self.pwr[2]) >= num_sats:
                    return c.POSSIBLE
                return c.NOT_ENOUGH_POWERSTONES
            return c.FED_IMPOSSIBLE

    def get_goal_score(self, gaia_map, fin_goal):
        if fin_goal == c.FIN_BLD:
            return len(self.get_buildings(gaia_map, no_gfm=True))
        elif fin_goal == c.FIN_FED:
            n = 0
            for planet in self.get_buildings(gaia_map).values():
                if planet[3]:
                    n += 1
            return n
        elif fin_goal == c.FIN_GAI:
            return self.get_amount_gaia_planets(gaia_map)
        elif fin_goal == c.FIN_SAT:
            return len(self.satellites)
        elif fin_goal == c.FIN_SEC:
            return self.get_amount_sectors(gaia_map)
        elif fin_goal == c.FIN_TYP:
            return self.get_different_planet_types(gaia_map)
        return 0

    def free_action_possible(self, action_type):
        if action_type == c.PWR_TO_GLD:
            if self.pwr[2] < 1:
                return c.NOT_ENOUGH_RESOURCES
            if self.gld > 29:
                return c.NOT_POSSIBLE
        elif action_type == c.PWR_TO_KNW:
            if self.pwr[2] < 4:
                return c.NOT_ENOUGH_RESOURCES
            if self.knw > 14:
                return c.NOT_POSSIBLE
        elif action_type == c.PWR_TO_ORE:
            if self.pwr[2] < 3:
                return c.NOT_ENOUGH_RESOURCES
            if self.ore > 14:
                return c.NOT_POSSIBLE
        elif action_type == c.PWR_TO_QIC:
            if self.pwr[2] < 4:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.MOVE_PWR_3:
            if self.pwr[1] < 2:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.KNW_TO_GLD:
            if self.knw < 1:
                return c.NOT_ENOUGH_RESOURCES
            if self.gld > 29:
                return c.NOT_POSSIBLE
        elif action_type == c.ORE_TO_GLD:
            if self.ore < 1:
                return c.NOT_ENOUGH_RESOURCES
            if self.gld > 29:
                return c.NOT_POSSIBLE
        elif action_type == c.ORE_TO_PST:
            if self.ore < 1:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.QIC_TO_RNG:
            if self.qic < 1:
                return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.QIC_TO_ORE:
            if self.qic < 1:
                return c.NOT_ENOUGH_RESOURCES
        else:
            # action type is not defined
            return c.NOT_POSSIBLE
        # no edge case has been hit so action is possible
        return c.POSSIBLE

    def execute_free_action(self, action_type):
        if action_type == c.MOVE_PWR_3:
            self.pwr[2] += 1
            self.pwr[1] -= 2
        elif action_type == c.PWR_TO_ORE:        
            self.pay_power(3)
            self.ore = min(15, (self.ore + 1))
        elif action_type == c.PWR_TO_QIC:
            self.pay_power(4)
            self.qic += 1
        elif action_type == c.QIC_TO_ORE:
            self.qic -= 1
            self.ore = min(15, (self.ore + 1))
        elif action_type == c.PWR_TO_KNW:
            self.pay_power(4)
            self.knw = min(15, (self.knw + 1))
        elif action_type == c.PWR_TO_GLD:
            self.pay_power(1)
            self.gld = min(30, (self.gld + 1))
        elif action_type == c.KNW_TO_GLD:
            self.knw -= 1
            self.gld = min(30, (self.gld + 1))
        elif action_type == c.ORE_TO_GLD:
            self.ore -= 1
            self.gld = min(30, (self.gld + 1))
        elif action_type == c.ORE_TO_PST:
            self.ore -= 1
            self.pwr[0] += 1
        elif action_type == c.QIC_TO_RNG:
            self.free_range += 2
            self.qic -= 1
        elif action_type == c.QIC_TO_ORE:
            self.ore = min(15, (self.ore + 1))


class Terraner(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BLUE,
            c.TERRANER,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BLUE: 0,
                c.WHITE: 1,
                c.RED: 1,
                c.BLACK: 2,
                c.ORANGE: 2,
                c.BROWN: 3,
                c.YELLOW: 3,
            },
        )
        self.pwr = [4, 4, 0, 0]
        self.research_branches[3] = 1
        self.gfm = 1

    #def __reduce__(self):
    #    return (self.__class__,(None, self.name, self.pos),)

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def gaia_phase(self):
        ''' The part of the gaia-phase that is not affected by pli. '''
        if not self.pli_built:
            self.pwr[1] += self.pwr[3]  # Directly move into sector 2.
            self.pwr[3] = 0
        return

    def gaia_phase_action_possible(self):
        return self.pli_built and self.pwr[3]

    def gaia_free_action_possible(self, action_type):        
        if action_type == c.TER_TO_QIC and self.pwr[3] >= 4:
            return c.POSSIBLE
        elif action_type == c.TER_TO_ORE and self.pwr[3] >= 3:
            return c.POSSIBLE
        elif action_type == c.TER_TO_KNW and self.pwr[3] >= 4:
            return c.POSSIBLE
        elif action_type == c.TER_TO_GLD and self.pwr[3]:
            return c.POSSIBLE
        return c.NOT_ENOUGH_RESOURCES

    def execute_gaia_free_action(self, action_type):
        '''The part of the gaia-phase that needs feedback from player.
        To be executed before or after gaia_phase and only if pli is built.'''
        if action_type == c.TER_TO_QIC and self.pwr[3] >= 4:
            self.pwr[3] -= 4
            self.pwr[1] += 4
            self.qic += 1
        elif action_type == c.TER_TO_ORE and self.pwr[3] >= 3:
            self.pwr[3] -= 3
            self.pwr[1] += 3
            self.ore = min(self.ore + 1, 15)
        elif action_type == c.TER_TO_KNW and self.pwr[3] >= 4:
            self.pwr[3] -= 4
            self.pwr[1] += 4
            self.knw = min(self.knw + 1, 15)
        elif action_type == c.TER_TO_GLD and self.pwr[3]:
            self.pwr[3] -= 1
            self.pwr[1] += 1
            self.gld = min(self.gld + 1, 30)
        if self.pwr[3] < 3:
            # only gold is possible, so convert all to gold
            self.pwr[1] += self.pwr[3]
            self.gld = min(self.gld + self.pwr[3], 30)
            self.pwr[3] = 0


class Lantida(Faction):
    ''' Finished here. Implementation in gaia/view to be done. '''

    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BLUE,
            c.LANTIDA,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BLUE: 0,
                c.WHITE: 1,
                c.RED: 1,
                c.BLACK: 2,
                c.ORANGE: 2,
                c.BROWN: 3,
                c.YELLOW: 3,
            },
        )
        self.pwr = [4, 0, 0, 0]
        self.gld = 13

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4

    def lantida_mine(self, planet):
        ''' Builds mine on a planet already colonized. '''
        self.ore -= 1
        self.gld -= 2
        self.mne -= 1
        if self.pli_built:
            self.knw = min(self.knw + 2, 15)
        self.free_range = 0
        self.free_tf = 0
        planet[4] = 1

    def build_mine_possible(self, q, r, gaia_map, initial):
        result = super().build_mine_possible(q, r, gaia_map, initial=initial)
        # not owned by you is returned if planet belongs to someone else
        if result == c.NOT_OWNED_BY_YOU:
            if gaia_map[(q,r)][4] == 0:
                # if mine is still available for building has been checked by factions method already
                if self.ore < 1 or self.gld < 2:
                    return c.NOT_ENOUGH_RESOURCES
                else:
                    return c.POSSIBLE
            else:
                return c.NOT_POSSIBLE
        return result
            
    
    def build_mine(self, q, r, gaia_map, initial=False):
        planet = gaia_map[(q,r)]
        if not initial and planet[1] is not None:
            return self.lantida_mine(planet)
        else:
            return super().build_mine(q, r, gaia_map, initial)

    # 'Getter' functions:    
    
    def get_buildings(self, gaia_map, exclude_fed=False):
        ''' Returns subdictionary of map containing only containing planets owned by player himself. '''
        my_map = {}
        for pos, planet in gaia_map.items():
            if planet[1] == self.pos and not (exclude_fed and planet[3]):
                my_map[pos] = planet
            if planet[4] > 0 and not (exclude_fed and planet[4] == 2):
                my_map[pos] = planet
        return my_map

    def get_power_value(self, submap):
        ''' Returns power value of buildings in submap. '''
        value = 0
        for planet in submap.values():
            if planet[1] == self.pos:
                if planet[2] == c.MINE:
                    value += 1
                elif planet[2] == c.TRADING_STATION or planet[2] == c.LAB:
                    value += 2
                elif planet[2] == c.PLANETARY_INSTITUTE or planet[2] == c.ACADEMY:
                    value += 4 if c.TEC_PIA in self.tech_tiles else 3
            elif planet[4] > 0:
                value += 1
        return value
    
    def get_goal_score(self, gaia_map, fin_goal):
        '''rework for lantida'''
        if fin_goal == c.FIN_FED:
            n = 0
            for planet in self.get_buildings(gaia_map).values():
                if planet[1] == self.pos and planet[3]:
                    n += 1
                elif planet[4] == 2:
                    n += 1
            return n
        else:
            return super().get_goal_score(gaia_map, fin_goal)


class Xenos(Faction):

    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.YELLOW,
            c.XENOS,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.YELLOW: 0,
                c.ORANGE: 1,
                c.BROWN: 1,
                c.BLACK: 2,
                c.RED: 2,
                c.BLUE: 3,
                c.WHITE: 3,
            },
        )
        self.research_branches[2] = 1
        self.qic += 1  # due to qic branch level 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[3] += 1

    def get_fed_possible(self, gaia_map, num_sats=None, submap=None):
        if submap == None:
            submap = self.get_buildings(gaia_map, exclude_fed=True)
        if num_sats is None:
            if self.get_power_value(submap) > (5 if self.pli_built else 6):
                return c.POSSIBLE
            return c.FED_IMPOSSIBLE
        else:
            if self.get_power_value(submap) > (5 if self.pli_built else 6):
                if (self.pwr[0] + self.pwr[1] + self.pwr[2]) >= num_sats:
                    return c.POSSIBLE
                return c.NOT_ENOUGH_POWERSTONES
            return c.FED_IMPOSSIBLE


class Gleen(Faction):
    ''' Finished here. '''

    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.YELLOW,
            c.GLEEN,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.YELLOW: 0,
                c.ORANGE: 1,
                c.BROWN: 1,
                c.BLACK: 2,
                c.RED: 2,
                c.BLUE: 3,
                c.WHITE: 3,
            },
        )
        self.research_branches[1] = 1
        self.ore = min(self.ore + 1, 15)  # Due to navigation branch level 1
        self.qic = 0

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[0] += 1
        self.add_fed_marker(c.FED_GLE)

    def build_mine_possible(self, q, r, gaia_map, initial):
        ''' If planet_type is gaia, one ore will be temporarily converted into one qic as cost for building mine. '''
        if gaia_map[(q,r)][0] == c.GAIA:
            self.qic += 1
            self.ore -= 1
            result = super().build_mine_possible(q, r, gaia_map, initial=initial)
            self.qic -= 1
            self.ore += 1
            return result
        else:
            return super().build_mine_possible(q, r, gaia_map, initial=initial)

    def build_mine(self, q, r, gaia_map, initial=False):
        ''' If planet_type is gaia, one ore will be converted into one qic as cost for building mine. '''
        if gaia_map[(q,r)][0] == c.GAIA:
            self.vcp += 2
            self.qic += 1
            self.ore -= 1
        super().build_mine(q, r, gaia_map, initial)

    def income_phase(self, round_goal):
        super().income_phase(round_goal)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0

    def execute_tech_tile(self, gaia_map, tile, cover=None):
        super().execute_tech_tile(gaia_map, tile, cover)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0

    def execute_level_up(self, index, gaia_map, need_resources=True):
        super().execute_level_up(index, gaia_map, need_resources=need_resources)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0

    def execute_fed_marker(self, marker):
        super().execute_fed_marker(marker)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0

    def execute_tech_action(self, tech_type):
        super().execute_tech_action(tech_type)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0

    def execute_free_action(self, action_type):
        super().execute_free_action(action_type)
        if not self.right_ac_built:
            self.ore = min(self.ore + self.qic, 15)
            self.qic = 0


class Taklons(Faction):

    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BROWN,
            c.TAKLONS,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BROWN: 0,
                c.YELLOW: 1,
                c.BLACK: 1,
                c.ORANGE: 2,
                c.WHITE: 2,
                c.BLUE: 3,
                c.RED: 3,
            },
        )
        self.brainstone = 0  # Position of special powerstone
        self.pi_pws_before = False
        self.maximize_pwr_gain = True # strategy for passive income

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def build_mine_possible(self, q, r, gaia_map, initial=False):
        result = super().build_mine_possible(q, r, gaia_map, initial=initial)
        if result == c.NOT_ENOUGH_POWERSTONES and (self.pwr[0] + self.pwr[1] + self.pwr[2] + 1) == self.gfm_pws_needed:
            return c.POSSIBLE # brainstone can help gaiaform
        return result

    def build_mine(self, q, r, gaia_map, initial=False):
        if gaia_map[(q,r)][0] == c.TRANSDIM and (self.pwr[0] + self.pwr[1] + self.pwr[2] + 1) == self.gfm_pws_needed:
            gaia_map[(q,r)][1] = self.pos
            gaia_map[(q,r)][0] = c.TRANSDIM_GFM
            gaia_map[(q,r)][2] = c.GAIAFORMER
            # remove resources                
            self.remove_power_stones(self.gfm_pws_needed - 1)
            self.pwr[3] += (self.gfm_pws_needed - 1)
            self.brainstone = 3
            self.gfm -= 1
            return
        else:
            super().build_mine(q, r, gaia_map, initial=initial)

    def gaia_phase(self):
        super().gaia_phase()
        if self.brainstone == 3:
            self.brainstone = 0

    def remove_power_stones(self, amount):
        removed = min(self.pwr[0], amount)
        self.pwr[0] -= removed
        amount -= removed
        removed = min(amount, self.pwr[1])
        self.pwr[1] -= removed
        amount -= removed
        removed = min(amount, self.pwr[2])
        self.pwr[2] -= removed
        amount -= removed
        if amount == 1:
            self.brainstone = -1 # brainstone is lost

    def passive_income_possible(self, q, r, map_items):
        '''Gets called if other player built on q, r. Returns possible passive income for players self.
        0 means not possible.'''
        income = 0
        for pos, planet in map_items:
            if (
                maptools.hex_distance(q, r, pos[0], pos[1]) <= 2
                and planet[1] == self.pos
            ):
                income = max(income, self.get_power_value({pos: planet}))
        possible_movement = self.pwr[0] * 2 + self.pwr[1] + (2 - self.brainstone)
        if self.pli_built:
            if income <= possible_movement:
                self.pi_pws_before = False
                return income
            elif self.maximize_pwr_gain:
                income = min(income, possible_movement + 2)
                self.pi_pws_before = True
            else:
                income = min(income, possible_movement)
                self.pi_pws_before = False
        else:
            income = min(income, possible_movement) 
        return income

    def execute_passive_income(self, pi_value):
        if self.pli_built and self.pi_pws_before:
            self.pwr[0] += 1
        super().execute_passive_income(pi_value)
        if self.pli_built and not self.pi_pws_before:
            self.pwr[0] += 1

    def handle_pwr_movement(self, moves):
        '''Taklon specified power movement.'''
        if moves and self.brainstone == 0:
            self.brainstone = 1
            moves -= 1

        diff = min(moves, self.pwr[0])  # 1 to 2.
        moves -= diff
        self.pwr[0] -= diff
        self.pwr[1] += diff

        if moves and self.brainstone == 1:
            self.brainstone = 2
            moves -= 1

        diff = min(moves, self.pwr[1])  # 2 to 3.
        self.pwr[1] -= diff
        self.pwr[2] += diff
        moves -= diff
        return moves

    def pay_power(self, amount):
        ''' Strategy: always pay with brainstone unless amount <= 2. '''
        if self.brainstone == 2:
            if amount > 2:
                self.brainstone = 0
                self.pwr[2] -= amount - 3
                self.pwr[0] += amount - 3
                return
            elif self.pwr[2] < amount:
                self.brainstone = 0
                return
        self.pwr[2] -= amount
        self.pwr[0] += amount

    def free_action_possible(self, action_type):
        if action_type == c.MOVE_PWR_3:
            if (self.pwr[1] > 0 and self.brainstone == 1) or self.pwr[1] > 1:
                return c.POSSIBLE
            return c.NOT_ENOUGH_RESOURCES
        elif action_type == c.TAKLONS_PLI:
            if self.pli_built:
                return c.POSSIBLE
            return c.NOT_POSSIBLE
        else:
            if self.brainstone == 2:
                self.pwr[2] += 3
            result = super().free_action_possible(action_type)
            if self.brainstone == 2:
                self.pwr[2] -= 3
            return result

    def p_and_q_possible(self, action_type):
        if self.brainstone == 2:
                self.pwr[2] += 3
        result = super().p_and_q_possible(action_type)
        if self.brainstone == 2:
            self.pwr[2] -= 3
        return result

    def execute_free_action(self, action_type):
        if action_type == c.MOVE_PWR_3:
            if self.brainstone == 1:
                self.brainstone = 2
                self.pwr[1] -= 1
            else:
                self.pwr[2] += 1
                self.pwr[1] -= 2
        elif action_type == c.TAKLONS_PLI:
            # change strategy
            self.maximize_pwr_gain = not self.maximize_pwr_gain
        else:
            super().execute_free_action(action_type)    
    


class Ambas(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BROWN,
            c.AMBAS,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BROWN: 0,
                c.YELLOW: 1,
                c.BLACK: 1,
                c.ORANGE: 2,
                c.WHITE: 2,
                c.BLUE: 3,
                c.RED: 3,
            },
        )
        self.inc_ore = [2, 3, 4, 4, 5, 6, 7, 8, 9]
        self.research_branches[1] = 1
        self.qic += 1  # Due to navigation branch level 1
        self.pli_change_started = False

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 2

    

    def pli_orange_possible(self):
        if not self.pli_built:
            return c.BUILD_PLI_FIRST
        if self.mne == 8:
            return c.NOT_POSSIBLE
        if self.orange_used[1]:
            return c.ALREADY_USED
        return c.POSSIBLE

    def execute_start_faction_action(self):
        self.orange_used[1] = True

    def execute_cancel_action(self, action_type):
        if action_type == c.AMBAS_PLI:
            self.orange_used[1] = False
        else:
            super().execute_cancel_action(action_type)    

    def pli_change_possible(self, gaia_map, q, r):
        if self.pli_built:
            if (q,r) in gaia_map.keys():
                if gaia_map[(q,r)][1] == self.pos:
                    if gaia_map[(q,r)][2] == c.MINE:
                        return c.POSSIBLE
                    return 'Du kannst nur mit einer Mine tauschen'
                return c.NOT_OWNED_BY_YOU
        return c.NOT_POSSIBLE

    def execute_pli_change(self, gaia_map, q, r):
        for _pos, planet in self.get_buildings(gaia_map).items():
            if planet[1] == self.pos and planet[2] == c.PLANETARY_INSTITUTE:
                planet[2] = c.MINE
                break
        gaia_map[(q,r)][2] = c.PLANETARY_INSTITUTE


class HadschHalla(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.RED,
            c.HADSCH_HALLA,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.RED: 0,
                c.BLUE: 1,
                c.ORANGE: 1,
                c.YELLOW: 2,
                c.WHITE: 2,
                c.BLACK: 3,
                c.BROWN: 3,
            },
        )
        self.inc_gld = [3, 6, 10, 14, 19]
        self.research_branches[4] = 1
        self.inc_res[1] += 2
        self.inc_res[4] += 1  # due to resource branch level 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def free_action_possible(self, action_type):
        if action_type in [c.HH_GLD_TO_KNW, c.HH_GLD_TO_ORE, c.HH_GLD_TO_QIC]:
            if self.pli_built:
                if action_type == c.HH_GLD_TO_KNW:
                    if self.gld < 4:
                        return c.NOT_ENOUGH_RESOURCES
                    if self.knw > 14:
                        return c.NOT_POSSIBLE
                elif action_type == c.HH_GLD_TO_ORE:
                    if self.gld < 3:
                        return c.NOT_ENOUGH_RESOURCES
                    if self.ore > 14:
                        return c.NOT_POSSIBLE
                elif action_type == c.HH_GLD_TO_QIC:
                    if self.gld < 4:
                        return c.NOT_ENOUGH_RESOURCES
                return c.POSSIBLE                    
            else:
                return c.BUILD_PLI_FIRST
        else:
            return super().free_action_possible(action_type)

    def execute_free_action(self, action_type):
        if action_type == c.HH_GLD_TO_QIC:
            self.gld -= 4
            self.qic += 1
        elif action_type == c.HH_GLD_TO_ORE:
            self.gld -= 3
            self.ore = min(self.ore + 1, 15)
        elif action_type == c.HH_GLD_TO_KNW:
            self.gld -= 4
            self.knw = min(self.knw + 1, 15)
        else:
            super().execute_free_action(action_type)     


class DerSchwarm(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.RED,
            c.DER_SCHWARM,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.RED: 0,
                c.BLUE: 1,
                c.ORANGE: 1,
                c.YELLOW: 2,
                c.WHITE: 2,
                c.BLACK: 3,
                c.BROWN: 3,
            },
        )
        self.inc_res[3] += 1
        self.ivit_sats = set()
        self.gained_fed_markers = 0
        self.expand_fed = False

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def build_mine(self, q, r, gaia_map, initial=False):
        if initial:
            self.pli_built = True
            gaia_map[(q,r)][1] = self.pos
            gaia_map[(q,r)][2] = c.PLANETARY_INSTITUTE
        else:
            super().build_mine(q, r, gaia_map)

    def passive_income_possible(self, q, r, map_items):
        income = super().passive_income_possible(q, r, map_items)
        if income == 0 and (self.pwr[0] * 2 + self.pwr[1]) > 0:
            # check if ivit sat is in range, which would gain 1 passive income
            for pos in self.ivit_sats:
                if maptools.hex_distance(q, r, pos[0], pos[1]) <= 2:
                    income = 1
                    break
        return income


    def pli_orange_possible(self):
        if not self.pli_built:
            return c.BUILD_PLI_FIRST
        if self.orange_used[1]:
            return c.ALREADY_USED
        return c.POSSIBLE

    def execute_start_faction_action(self):
        self.orange_used[1] = True

    def execute_cancel_action(self, action_type):
        if action_type == c.DER_SCHWARM_PLI:
            self.orange_used[1] = False
        else:
            super().execute_cancel_action(action_type)

    def ivit_sat_possible(self, q, r, gaia_map):
        if (q,r) in gaia_map or (q,r) in self.ivit_sats or (q,r) in self.satellites:
            return c.CANT_PLACE_HERE
        if self.is_in_range(q,r, gaia_map) == c.OUT_OF_RANGE:
            return c.OUT_OF_RANGE
        return c.POSSIBLE

    def execute_ivit_sat(self, q, r):
        self.ivit_sats.add((q,r))   

    def execute_build_fed(self, sats):
        self.qic -= len(sats)
        self.satellites.update(sats)
        self.expand_fed = True 

    def add_fed_marker(self, fed_marker):
        if self.expand_fed:
            self.gained_fed_markers += 1
            self.expand_fed = False
        super().add_fed_marker(fed_marker)

    def is_in_range(self, q, r, gaia_map):
        for pos in self.get_buildings(gaia_map):
            if (
                maptools.hex_distance(
                    pos[0], pos[1], q, r
                )
                <= self.range + self.free_range
            ):
                return True
        for satelite in self.ivit_sats:
            if (
                maptools.hex_distance(
                    satelite[0], satelite[1], q, r
                )
                <= self.range + self.free_range
            ):
                return True
        return c.OUT_OF_RANGE

    def get_power_value(self, submap):
        ''' Der Schwarm specififc due to ivit satelites. '''
        value = 0
        for planet in submap.values():
            if planet[2] == c.IVIT_SATELLITE:
                value += 1
            elif planet[2] == c.MINE:
                value += 1
            elif planet[2] == c.TRADING_STATION or planet[2] == c.LAB:
                value += 2
            elif planet[2] == c.PLANETARY_INSTITUTE or planet[2] == c.ACADEMY:
                value += 4 if c.TEC_PIA in self.tech_tiles else 3
            # add neighboring 
        return value

    def get_fed_possible(self, gaia_map, num_sats=None, submap=None):
        if submap == None:
            submap = self.get_buildings(gaia_map)            
            for pos in self.ivit_sats:
                submap[pos] = [None, None, c.IVIT_SATELLITE]
        if num_sats is None:
            if self.get_power_value(submap) >= (7 * (1 + self.gained_fed_markers)):
                return c.POSSIBLE
            return c.FED_IMPOSSIBLE
        else:
            if self.get_power_value(submap) >= (7 * (1 + self.gained_fed_markers)):
                if self.qic >= num_sats:
                    return c.POSSIBLE
                return c.NOT_ENOUGH_RESOURCES

class Geoden(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.ORANGE,
            c.GEODEN,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.ORANGE: 0,
                c.RED: 1,
                c.YELLOW: 1,
                c.BLUE: 2,
                c.BROWN: 2,
                c.BLACK: 3,
                c.WHITE: 3,
            },
        )
        self.research_branches[0] += 1
        self.ore = min(self.ore + 2, 15)  # due to terraforming branch level 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def build_mine(self, q, r, gaia_map, initial=False):
        planet_types = self.get_different_planet_types(gaia_map, ret_list=True)
        super().build_mine(q, r, gaia_map, initial)
        if self.pli_built and gaia_map[(q,r)][0] not in planet_types:
            self.knw = min(self.knw + 3, 15)


class BalTak(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.ORANGE,
            c.BAL_TAK,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.ORANGE: 0,
                c.RED: 1,
                c.YELLOW: 1,
                c.BLUE: 2,
                c.BROWN: 2,
                c.BLACK: 3,
                c.WHITE: 3,
            },
        )
        self.pwr = [2, 2, 0, 0]
        self.qic = 0

        self.gfm_in_gaia = 0 # Amount of gaiaformers in green space due to special ability.
        self.research_branches[3] += 1
        self.gfm += 1  # due to gaiaforming branch level 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def gaia_phase(self):
        super().gaia_phase()
        self.gfm += self.gfm_in_gaia 
        self.gfm_in_gaia = 0
        return

    def free_action_possible(self, action_type):
        if action_type == c.BAL_TAK_SPECIAL:
            if self.gfm > 0:
                return c.POSSIBLE
            return c.NOT_POSSIBLE
        else:
            return super().free_action_possible(action_type)

    def execute_free_action(self, action_type):
        if action_type == c.BAL_TAK_SPECIAL:
            self.gfm -= 1
            self.qic += 1
            self.gfm_in_gaia += 1
        else:
            super().execute_free_action(action_type)

    def level_up_possible(self, index, lvl_5_free, need_resources=True):
        if (not self.pli_built) and index == 1:
            return c.BUILD_PLI_FIRST
        return super().level_up_possible(index, lvl_5_free, need_resources=need_resources)

    def execute_level_up(self, index, gaia_map, need_resources=True):
        if (not self.pli_built) and index == 1:
            return # level up is not performed if pli is not built
        super().execute_level_up(index, gaia_map, need_resources=need_resources)

    def execute_ac_action(self):
        self.gld = min(self.gld + 4, 30)
        self.orange_used[0] = True      

class Itar(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.WHITE,
            c.ITAR,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.WHITE: 0,
                c.BLACK: 1,
                c.BLUE: 1,
                c.RED: 2,
                c.BROWN: 2,
                c.YELLOW: 3,
                c.ORANGE: 3,
            },
        )
        self.pwr = [4, 4, 0, 0]
        self.inc_res[5] += 1
        self.ore = 5

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def gaia_phase(self):
        '''Handles gaia phase for a player. To be modified for some faction.'''
        if self.pli_built:
            self.pwr[0] += (self.pwr[3] % 4)
            self.pwr[3] -= (self.pwr[3] % 4)
        else:
            self.pwr[0] += self.pwr[3]
            self.pwr[3] = 0
        return

    def execute_free_action(self, action_type):
        if action_type == c.MOVE_PWR_3:
            self.pwr[2] += 1
            self.pwr[3] += 1
            self.pwr[1] -= 2
        else:
            super().execute_free_action(action_type)            

    def upgrade_building(self, q, r, gaia_map, decision):
        # standard resource increase for left ac is 2, Itar has 3 so increase by 1
        if gaia_map[(q,r)] == c.LAB and (decision == c.LEFT_ACADEMY or self.right_ac_built):
            self.inc_res[2] += 1
        super().upgrade_building(q, r, gaia_map, decision)

    def gaia_phase_action_possible(self):
        return self.pwr[3] > 3

    def execute_start_gaia_phase_action(self):
        self.pwr[3] -= 4

    def execute_cancel_action(self, action_type):
        if action_type == c.ITAR_PLI:
            self.pwr[3] += 4
        else:
            super().execute_cancel_action(action_type)

    def finish_gaia_phase(self):
        self.pwr[0] += self.pwr[3]
        self.pwr[3] = 0
        


class Nevla(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.WHITE,
            c.NEVLA,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.WHITE: 0,
                c.BLACK: 1,
                c.BLUE: 1,
                c.RED: 2,
                c.BROWN: 2,
                c.YELLOW: 3,
                c.ORANGE: 3,
            },
        )
        self.inc_knw = [1, 1, 1, 1]
        self.knw = 2
        self.research_branches[5] += 1
        self.inc_res[2] += 1  # due to knw branch level 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1   

    def upgrade_building(self, q, r, gaia_map, decision):
        super().upgrade_building(q, r, gaia_map, decision)
        if gaia_map[(q,r)][2] == c.LAB:
            self.inc_res[4] += 2
        elif gaia_map[(q,r)][2] == c.ACADEMY:
            self.inc_res[4] -= 2

    def pay_power(self, amount):
        if self.pli_built:
            # one pws counts for 2 power
            if amount % 2 == 1:
                amount += 1
            self.pwr[2] -= int(amount / 2)
            self.pwr[0] += int(amount / 2)
        else:
            self.pwr[2] -= amount
            self.pwr[0] += amount

    def free_action_possible(self, action_type):
        if action_type == c.SPECIAL_NEVLA:
            if self.pwr[2] < 1:
                return c.NOT_ENOUGH_RESOURCES
            return c.POSSIBLE
        if not self.pli_built:
            return super().free_action_possible(action_type)
        else:
            # overwrite to halve pws required
            if action_type == c.PWR_TO_GLD:
                if self.pwr[2] < 1:
                    return c.NOT_ENOUGH_RESOURCES
                if self.gld > 29:
                    return c.NOT_POSSIBLE
            elif action_type == c.PWR_TO_KNW:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
                if self.knw > 14:
                    return c.NOT_POSSIBLE
            elif action_type == c.PWR_TO_ORE:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
                if self.ore > 14:
                    return c.NOT_POSSIBLE
            elif action_type == c.PWR_TO_QIC:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            else:
                return super().free_action_possible(action_type)
            # no edge case has been hit so action is possible
            return c.POSSIBLE

    def execute_free_action(self, action_type):
        if action_type == c.SPECIAL_NEVLA:            
            self.pwr[2] -= 1
            self.pwr[3] += 1
            self.knw = min(self.knw + 1, 15)
        else:
            super().execute_free_action(action_type)

    def p_and_q_possible(self, action_type):
        if not self.pli_built:
            return super().p_and_q_possible(action_type)
        else:
            if action_type == c.PUB_2_KNW_3:
                if self.pwr[2] < 4:
                    return c.NOT_ENOUGH_RESOURCES            
            elif action_type == c.PUB_2_TRF_2:
                if self.pwr[2] < 3:
                    return c.NOT_ENOUGH_RESOURCES
            elif action_type == c.PUB_2_ORE:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            elif action_type == c.PUB_2_GLD:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            elif action_type == c.PUB_2_KNW_2:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            elif action_type == c.PUB_2_TRF_1:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            elif action_type == c.PUB_2_PWS:
                if self.pwr[2] < 2:
                    return c.NOT_ENOUGH_RESOURCES
            else:
                return super().p_and_q_possible(action_type)
            return c.POSSIBLE

class MadAndroids(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BLACK,
            c.MAD_ANDROIDS,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BLACK: 0,
                c.BROWN: 1,
                c.WHITE: 1,
                c.YELLOW: 2,
                c.BLUE: 2,
                c.RED: 3,
                c.ORANGE: 3,
            },
        )
        self.inc_gld = [0, 3, 7, 12]
        self.inc_knw = [0, 1, 2, 3, 4]
        self.knw = 1

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 2

    def income_phase(self, round_goal):
        '''Madandroids specific.'''
        self.ore += self.inc_ore[8 - self.mne]
        self.gld += self.inc_gld[3 - self.lab]  # diff
        self.knw += self.inc_knw[4 - self.trd]  # diff
        if self.left_ac_built:
            self.knw += 2
        # Resource income by tech, research, etc.
        self.ore += self.inc_res[0]
        self.gld += self.inc_res[1]
        self.knw += self.inc_res[2]
        self.qic += self.inc_res[3]
        # Resource income by booster.
        leftover_pwr_movement = 0        
        if self.current_booster == c.BOO_GAI:
            self.gld += 4
        elif self.current_booster == c.BOO_LAB:
            self.knw += 1
        elif self.current_booster == c.BOO_MIN:
            self.ore += 1
        elif self.current_booster == c.BOO_NAV:
            leftover_pwr_movement += self.handle_pwr_movement(2)
        elif self.current_booster == c.BOO_PIA:
            leftover_pwr_movement += self.handle_pwr_movement(4)
        elif self.current_booster == c.BOO_TER:
            self.gld += 2
        elif self.current_booster == c.BOO_TRS:
            self.ore += 1
        elif self.current_booster == c.BOO_KNW:
            self.ore += 1
            self.knw += 1
        elif self.current_booster == c.BOO_PWT:
            self.pwr[0] += 2
            self.ore += 1
        elif self.current_booster == c.BOO_QIC:
            self.gld += 2
            self.qic += 1
        # Gain Power.
        leftover_pwr_movement += self.handle_pwr_movement(self.inc_res[4])
        new_stones = self.inc_res[5]
        # algorithm to maximize pwr stones in level 3
        while leftover_pwr_movement > 0:
            if new_stones > 0:
                self.pwr[0] += 1
                new_stones -= 1
                leftover_pwr_movement = self.handle_pwr_movement(leftover_pwr_movement)
            else:
                break
        self.pwr[0] += new_stones

        self.ore = min(self.ore, 15)
        self.gld = min(self.gld, 30)
        self.knw = min(self.knw, 15)

        self.orange_used = [False] * 7
        self.round_goal = round_goal
        return

    def upgrade_building_possible(self, q, r, gaia_map, decision=None):
        '''Try to upgrade existing building to new_building_type.
        decision= PLI or LAB.
        decision= LEFT_ACADEMY or RIGHT_ACADEMY.'''
        planet = gaia_map[(q,r)]
        if planet[1] != self.pos:
            return c.NOT_OWNED_BY_YOU
        if planet[0] == c.BLACK_PLANET:
            return c.FULLY_UPGRADED
        old_type = planet[2]
        if old_type == c.GAIAFORMER:
            if planet[0] != c.GAIAFORMED:
                return c.NOT_POSSIBLE
            return self.build_mine_possible(q, r, gaia_map)
        if old_type == c.MINE:
            if self.trd == 0:
                return c.NO_MORE_FREE_BUILDINGS
            cost_gld = 3 if self.are_neighbors_nearby(q, r, gaia_map) else 6
            if self.gld >= cost_gld and self.ore >= 2:
                return c.POSSIBLE
            else:
                return c.NOT_ENOUGH_RESOURCES
        if old_type == c.TRADING_STATION:
            if self.left_ac_built and self.right_ac_built:
                decision = c.LAB
            elif self.lab == 0 and decision is None:
                decision = c.ACADEMY
            if decision == None:
                return c.NEED_FEEDBACK_TRD
            if decision in [c.ACADEMY, c.LEFT_ACADEMY, c.RIGHT_ACADEMY]:
                if self.left_ac_built and self.right_ac_built:
                    return c.NO_MORE_FREE_BUILDINGS
                if self.left_ac_built:
                    decision = c.RIGHT_ACADEMY
                elif self.right_ac_built:
                    decision = c.LEFT_ACADEMY
                if decision == c.ACADEMY:
                    return c.NEED_FEEDBACK_AC            
                if self.gld >= 6 and self.ore >= 6:
                    return c.POSSIBLE_CHOOSE_TECH
                return c.NOT_ENOUGH_RESOURCES            
            elif decision == c.LAB:  # LAB
                if self.lab == 0:
                    return c.NO_MORE_FREE_BUILDINGS
                if self.gld >= 5 and self.ore >= 3:
                    return c.POSSIBLE_CHOOSE_TECH
                return c.NOT_ENOUGH_RESOURCES 
            return c.NEED_FEEDBACK_TRD           
        if old_type == c.LAB:
            if self.pli_built:
                return c.FULLY_UPGRADED
            if self.gld >= 6 and self.ore >= 4:                    
                return c.POSSIBLE
            return c.NOT_ENOUGH_RESOURCES            
        else:
            return c.FULLY_UPGRADED


    def upgrade_building(self, q, r, gaia_map, decision):
        '''Try to upgrade existing building to new_building_type.
        decision= PLI or LAB.
        decision= LEFT_ACADEMY or RIGHT_ACADEMY.'''
        planet=gaia_map[(q,r)]
        old_type = planet[2]
        if old_type == c.GAIAFORMER:
            self.build_mine(q, r, gaia_map)
        elif old_type == c.MINE:
            cost_gld = 3 if self.are_neighbors_nearby(q, r, gaia_map) else 6
            self.gld -= cost_gld
            self.ore -= 2
            self.mne += 1
            self.trd -= 1
            planet[2] = c.TRADING_STATION
            if c.ADV_TRSB in self.tech_tiles:
                self.vcp += 3
            if self.round_goal == c.RND_TRS3:
                self.vcp += 3
            if self.round_goal == c.RND_TRS4:
                self.vcp += 4
        elif old_type == c.TRADING_STATION:
            # decision is None if there is no more option
            if self.left_ac_built and self.right_ac_built:
                decision = c.LAB
            if decision == c.LAB:
                self.gld -= 5
                self.ore -= 3
                self.trd += 1
                self.lab -= 1
                planet[2] = c.LAB
            else:                 
                self.gld -= 6
                self.ore -= 6
                self.trd += 1
                planet[2] = c.ACADEMY
                if self.round_goal == c.RND_PIA:
                    self.vcp += 5    
                if self.left_ac_built:
                    decision = c.RIGHT_ACADEMY
                elif self.right_ac_built:
                    decision = c.LEFT_ACADEMY       
                if decision == c.RIGHT_ACADEMY:                
                    self.right_ac_built = True                
                else:  # Left Academy
                    self.left_ac_built = True  
        elif old_type == c.LAB:
            self.gld -= 6
            self.ore -= 4
            self.lab += 1
            self.pli_built = True
            self.activate_pli()
            planet[2] = c.PLANETARY_INSTITUTE
            if self.round_goal == c.RND_PIA:
                self.vcp += 5

    def get_power_value(self, submap):
        ''' Mad Android specific. Returns power value of buildings in submap. '''
        value = 0
        for planet in submap.values():
            if planet[2] == c.MINE:
                value += 1
            elif planet[2] == c.TRADING_STATION or planet[2] == c.LAB:
                value += 2
            elif planet[2] == c.PLANETARY_INSTITUTE or planet[2] == c.ACADEMY:
                value += 4 if c.TEC_PIA in self.tech_tiles else 3
            if self.pli_built and planet[0] == c.BLACK:
                value += 1
        return value

    def pli_orange_possible(self):
        if self.orange_used[1]:
            return c.ALREADY_USED
        return c.POSSIBLE

    def execute_start_faction_action(self):
        self.orange_used[1] = True

    def execute_cancel_action(self, action_type):
        if action_type == c.MAD_ANDROIDS_SPECIAL:
            self.orange_used[1] = False
        else:
            super().execute_cancel_action(action_type)

    def free_level_up_possible(self, branch):  
        for rb in self.research_branches:
            if rb < self.research_branches[branch]:
                return c.NEED_CHOOSE_OTHER_TRACK    
        return c.POSSIBLE


class Firaks(Faction):
    def __init__(self, name, pos):
        super().__init__(
            name,
            pos,
            c.BLACK,
            c.FIRAKS,
            {
                c.GAIA: 0,
                c.GAIAFORMED: 0,
                c.BLACK: 0,
                c.BROWN: 1,
                c.WHITE: 1,
                c.YELLOW: 2,
                c.BLUE: 2,
                c.RED: 3,
                c.ORANGE: 3,
            },
        )
        self.inc_knw = [2, 3, 4, 5]
        self.knw = 2
        self.ore = 3

    def activate_pli(self):
        ''' Gets called once when you build your Planetary Institue. '''
        self.inc_res[4] += 4
        self.inc_res[5] += 1

    def pli_orange_possible(self):
        if self.pli_built:
            if self.orange_used[1]:
                return c.ALREADY_USED
            if self.lab < 3 and self.trd > 0:
                return c.POSSIBLE
            return c.NOT_POSSIBLE            
        return c.BUILD_PLI_FIRST
    
    def execute_start_faction_action(self):
        self.orange_used[1] = True

    def execute_cancel_action(self, action_type):
        if action_type == c.FIRAKS_PLI:
            self.orange_used[1] = False
        else:
            super().execute_cancel_action(action_type)

    def lab_downgrade_possible(self, gaia_map, q, r):
        if (q,r) in gaia_map:
            if gaia_map[(q,r)][1] == self.pos:
                if gaia_map[(q,r)][2] == c.LAB:
                    return c.POSSIBLE
                return c.NOT_POSSIBLE
            return c.NOT_OWNED_BY_YOU
        return c.NOT_POSSIBLE

    def execute_lab_downgrade(self, gaia_map, q,r):
        gaia_map[(q,r)][2] = c.TRADING_STATION
        self.trd -= 1
        self.lab += 1
        # this action acts as placing a trd so check for vcp gain
        if c.ADV_TRSB in self.tech_tiles:
            self.vcp += 3
        if self.round_goal == c.RND_TRS3:
            self.vcp += 3
        if self.round_goal == c.RND_TRS4:
            self.vcp += 4


FACTIONS = {
    c.AMBAS: Ambas,
    c.BAL_TAK: BalTak,
    c.MAD_ANDROIDS: MadAndroids,
    c.ITAR: Itar,
    c.NEVLA: Nevla,
    c.HADSCH_HALLA: HadschHalla,
    c.DER_SCHWARM: DerSchwarm,
    c.TERRANER: Terraner,
    c.LANTIDA: Lantida,
    c.GEODEN: Geoden,
    c.FIRAKS: Firaks,
    c.TAKLONS: Taklons,
    c.GLEEN: Gleen,
    c.XENOS: Xenos,
}
