import os, sys
import threading
import copy

from kivy.uix.textinput import TextInput

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import kivy
from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.graphics import Rotate, PushMatrix, PopMatrix, Ellipse, Color, Rectangle
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.behaviors.togglebutton import ToggleButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen

# This error is only a mistake form lint
from kivy.properties import (
    Property,
    ObjectProperty,
    NumericProperty,
    ReferenceListProperty,
    ListProperty,
    BooleanProperty,
    StringProperty,
)
from kivy.lang import Builder
import kivy.uix.screenmanager as screenmanager


import functools
import math
import random

from gaia_lib import maptools
from gaia_lib import constants as c

kivy.require('1.11.1')


# Classes needed to define specififc behavior / elements


class HoverBehavior(object):
    ''' From: https://stackoverflow.com/questions/28712359/how-to-fix-aspect-ratio-of-a-kivy-game '''

    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        super(HoverBehavior, self).__init__(**kwargs)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return  # do proceed if has no parent
        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside:
            return
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self):
        pass

    def on_leave(self):
        pass
    
    def do_bind(self):
        Window.fbind('mouse_pos',self.on_mouse_pos)
    
    def do_unbind(self):
        Window.funbind('mouse_pos', self.on_mouse_pos)



Factory.register('HoverBehavior', HoverBehavior)


class HoverButton(Button, HoverBehavior):
    action_type = StringProperty()
    hover_color = ListProperty([0, 1, 0, 0.2])

    def on_enter(self, *args):
        ''' Blit half-transparent green background when hovering over button. '''
        self.background_color = self.hover_color

    def on_leave(self, *args):
        self.background_color = 0, 0, 0, 0


class ToolTipImage(Image, HoverBehavior):
    '''Image which displays a tooltip when hovered over'''
    tooltip = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tooltip_size = (len(self.tooltip)*7.5,20)

    def on_enter(self, *args):

        x, y = mainApp.Window.mouse_pos
        if x + self.tooltip_size[0] > mainApp.Window.width:
            x -= self.tooltip_size[0]
        x, y = self.to_widget(x, y)
        root = mainApp.root.get_screen(mainApp.root.current)
        root.ids['tooltip'].pos = (x,y)
        root.ids['tooltip'].text = self.tooltip
        root.ids['tooltip'].size = self.tooltip_size
        root.ids['tooltip'].canvas.before.clear()      
        root.ids['tooltip'].canvas.before.add(Color((2/3), 0.96, 0.098, mode='hsv'))
        root.ids['tooltip'].canvas.before.add(Rectangle(pos=(x,y), size=self.tooltip_size)) 
        root.ids['tooltip'].canvas.ask_update()
        #self.add_widget(self.tooltip_label)

    def on_leave(self, *args):
        #self.clear_widgets()
        root = mainApp.root.get_screen(mainApp.root.current)
        if root.ids['tooltip'].text == self.tooltip:
            root.ids['tooltip'].text = ''
            root.ids['tooltip'].canvas.before.clear()
            root.ids['tooltip'].canvas.ask_update() 

class TranspImage(Image, HoverBehavior):
    def on_enter(self):
        self.color = [1,1,1,0.3]

    def on_leave(self):
        self.color = [1,1,1,1]


class TranspLayout(RelativeLayout, HoverBehavior):
    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return  # do proceed if has no parent
        pos = args[1]
        if self.parent:
            pos = self.parent.to_widget(*pos)
        inside = self.collide_point(*pos)
        if self.hovered == inside:
            return
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self):
        for widget in self.children:
            if isinstance(widget, Image):
                widget.color = [1,1,1,0.3]

    def on_leave(self):
        for widget in self.children:
            if isinstance(widget, Image):
                widget.color = [1,1,1,1]
    


class MyToggleButton(ToggleButtonBehavior, Image):   
    def __init__(self, **kwargs):
        super(MyToggleButton, self).__init__(**kwargs)
        self.source = f'{c.ASSETS_PATH}/ui/toggle_off.png'

    def on_state(self, widget, value):
        if value == 'down':
            self.source = f'{c.ASSETS_PATH}/ui/toggle_on.png'
        else:
            self.source = f'{c.ASSETS_PATH}/ui/toggle_off.png'


class SectorImage(Image):
    pass


class Background(Image):
    offset = ListProperty()
    magnification = NumericProperty(0)


class FactionBoard(Widget):
    player = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # the base board with actions for all factions

    def enable_free_actions(self):
        return (
            mainApp.gaia_inst.round > 0
            and self.player == mainApp.gaia_inst.my_pos
            and not mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].has_finished
        )

    def free_action(self, action_type, *args):
        if self.enable_free_actions():
            result = mainApp.gaia_inst.req_free_action(action_type)
            if not result == c.POSSIBLE:
                mainApp.error_popup(result)
    
    def ac_action(self, *args):
        result = mainApp.gaia_inst.ac_action()
        if result != c.POSSIBLE:
            mainApp.error_popup(result) 

    def action(self, action_type, *args):
        result = mainApp.gaia_inst.req_action(action_type)   
        if result != c.POSSIBLE:
            mainApp.error_popup(result) 

    def update_resources(self, p):
        # CURRENCIES
        # standard y position
        ore_y = 1998 / 2225
        knw_y = 1998 / 2225
        gld1_y = 1998 / 2225
        gld2_y = 1998 / 2225
        if p.ore == 0:
            ore_x = 125 / 3483
        else:
            if p.ore < 11:
                ore_x = (396 + 223 * (p.ore - 1)) / 3483
            else:
                ore_x = (2594 + 180 * (p.ore - 11)) / 3483
        if p.knw == 0:
            knw_x = 125 / 3483
        else:
            if p.knw < 11:
                knw_x = (396 + 223 * (p.knw - 1)) / 3483
            else:
                knw_x = (2594 + 180 * (p.knw - 11)) / 3483
        if p.gld == 0:
            gld1_x = 125 / 3483
        else:
            if p.gld < 11:
                gld1_x = (396 + 223 * (p.gld - 1)) / 3483
            else:
                gld1_x = (2594 + 180 * (min(p.gld - 11, 4))) / 3483
        if p.gld < 16:
            gld2_x = 125 / 3483
        else:
            gld2 = p.gld - 15
            if gld2 < 11:
                gld2_x = (396 + 223 * (gld2 - 1)) / 3483
            else:
                gld2_x = (2594 + 180 * (gld2 - 11)) / 3483
        # y adjustment
        if p.ore == p.knw:
            knw_y = 2020 / 2225
            if p.gld == p.ore:
                gld1_y = 2058 / 2225
                if p.gld == 0:
                    gld2_y = 2088 / 2225
            elif (p.gld - 15) == p.ore:
                gld2_y = 2058 / 2225
            elif p.ore == 0 and p.gld < 16:
                gld2_y = 2058 / 2225
        # ore and knw different but gold equal to one of them
        elif p.ore == p.gld or p.knw == p.gld:
            gld1_y = 2024 / 2225
            if p.gld == 0:
                gld2_y = 2050 / 2225
        elif p.gld < 15 and (p.ore == 0 or p.knw == 0):
            gld2_y = 2020 / 2225
        elif p.ore == (p.gld - 15) or p.knw == (p.gld - 15):
            gld2_y = 2024 / 2225
            if p.gld == 30:
                gld1_y = 2054 / 2225
        elif p.gld == 0:
            gld2_y = 2018 / 2225
        self.ids['ore'].pos_hint = {'x': ore_x, 'y': ore_y}
        self.ids['knw'].pos_hint = {'x': knw_x, 'y': knw_y}
        self.ids['gld1'].pos_hint = {'x': gld1_x, 'y': gld1_y}
        self.ids['gld2'].pos_hint = {'x': gld2_x, 'y': gld2_y}
        # POWER TOKENS
        self.ids['pt_1'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pt_2'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pt_3'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pt_gaia'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pt_1_label'].text = ''
        self.ids['pt_2_label'].text = ''
        self.ids['pt_3_label'].text = ''
        self.ids['pt_gaia_label'].text = ''
        if 0 < p.pwr[0] < 5:
            self.ids['pt_1'].source = f'{c.ASSETS_PATH}/currencies/{p.pwr[0]}pt.png'
        elif p.pwr[0]:
            self.ids['pt_1'].source = f'{c.ASSETS_PATH}/currencies/pt_more.png'
            self.ids['pt_1_label'].text = f'{p.pwr[0]}'
        if 0 < p.pwr[1] < 5:
            self.ids['pt_2'].source = f'{c.ASSETS_PATH}/currencies/{p.pwr[1]}pt.png'
        elif p.pwr[1]:
            self.ids['pt_2'].source = f'{c.ASSETS_PATH}/currencies/pt_more.png'
            self.ids['pt_2_label'].text = f'{p.pwr[1]}'
        if 0 < p.pwr[2] < 5:
            self.ids['pt_3'].source = f'{c.ASSETS_PATH}/currencies/{p.pwr[2]}pt.png'
        elif p.pwr[2]:
            self.ids['pt_3'].source = f'{c.ASSETS_PATH}/currencies/pt_more.png'
            self.ids['pt_3_label'].text = f'{p.pwr[2]}'
        if 0 < p.pwr[3] < 5:
            self.ids['pt_gaia'].source = f'{c.ASSETS_PATH}/currencies/{p.pwr[3]}pt.png'
        elif p.pwr[3]:
            self.ids['pt_gaia'].source = f'{c.ASSETS_PATH}/currencies/pt_more.png'
            self.ids['pt_gaia_label'].text = f'{p.pwr[3]}'
        self.ids['pt_1_label'].size = self.ids['pt_1_label'].texture_size
        self.ids['pt_2_label'].size = self.ids['pt_2_label'].texture_size
        self.ids['pt_3_label'].size = self.ids['pt_3_label'].texture_size
        self.ids['pt_gaia_label'].size = self.ids['pt_gaia_label'].texture_size
        self.ids['pt_1'].reload()
        self.ids['pt_2'].reload()
        self.ids['pt_3'].reload()
        self.ids['pt_gaia'].reload()
        # UPDATE BUILDINGS
        self.ids['mine_layout'].clear_widgets()
        mine_x = 1240
        for _i in range(p.mne):
            mine_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/mine_board.png')
            mine_img.size_hint = (122 / 1361, 1)
            mine_img.pos_hint = {'x': mine_x / 1361, 'y': 0}
            mine_img.allow_stretch = True
            mine_x -= 177
            self.ids['mine_layout'].add_widget(mine_img)
        self.ids['trs_layout'].clear_widgets()
        trs_x = 531
        for _i in range(p.trd):
            trs_img = Image(
                source=f'{c.ASSETS_PATH}/colors/{p.color}/trading_station_board.png'
            )
            trs_img.size_hint = (122 / 653, 1)
            trs_img.pos_hint = {'x': trs_x / 653, 'y': 0}
            trs_img.allow_stretch = True
            trs_x -= 177
            self.ids['trs_layout'].add_widget(trs_img)
        self.ids['lab_layout'].clear_widgets()
        lab_x = 500
        for _i in range(p.lab):
            lab_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/lab_board.png')
            lab_img.size_hint = (220 / 740, 1)
            lab_img.pos_hint = {'x': lab_x / 740, 'y': 0}
            lab_img.allow_stretch = True
            lab_x -= 250
            self.ids['lab_layout'].add_widget(lab_img)
        self.ids['gfm_layout'].clear_widgets()
        gfm_x = 0
        for _i in range(p.gfm):
            gfm_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/gaiaformer_board.png')
            gfm_img.size_hint = (244 / 781, 1)
            gfm_img.pos_hint = {'x': gfm_x / 781, 'y': 0}
            gfm_img.allow_stretch = True
            gfm_x += 270
            self.ids['gfm_layout'].add_widget(gfm_img)
        self.ids['left_ac'].source = f'{c.ASSETS_PATH}/colors/{p.color}/academy_board.png'
        self.ids['right_ac'].source = f'{c.ASSETS_PATH}/colors/{p.color}/academy_board.png'
        self.ids[
            'pli'
        ].source = f'{c.ASSETS_PATH}/colors/{p.color}/planetary_institute_board.png'
        if p.right_ac_built:
            self.ids['right_ac'].source = f'{c.ASSETS_PATH}/empty.png'
            self.ids['orangeqic'].bind(on_release=self.ac_action)
            self.ids['orangeqic'].hover_color = [0, 1, 0, 0.2]
        if p.left_ac_built:
            self.ids['left_ac'].source = f'{c.ASSETS_PATH}/empty.png'
        if p.pli_built:
            self.ids['pli'].source = f'{c.ASSETS_PATH}/empty.png'
        if p.orange_used[0]:
            self.ids['ac_octagon'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['ac_octagon'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['ac_octagon'].reload()
        self.ids['left_ac'].reload()
        self.ids['right_ac'].reload()
        self.ids['pli'].reload()


class AmbasBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/ambas.jpg'
        self.pli_button = HoverButton()
        self.pli_button.action_type = c.AMBAS_PLI
        self.pli_button.size_hint = (460 / 3483, 325 / 2225)
        self.pli_button.pos_hint = {'x': 785 / 3483, 'y': 875 / 2225}
        self.pli_button.background_normal = ''
        self.pli_button.background_color = (0, 0, 0, 0)
        self.pli_button.bind(
            on_release=functools.partial(self.action, self.pli_button.action_type)
        )
        self.ids['board_layout'].add_widget(self.pli_button)
        self.ids['faction_octagon'].size_hint = (460 / 3483, 325 / 2225)
        self.ids['faction_octagon'].pos_hint = {'x': 785 / 3483, 'y': 875 / 2225}


    def update_resources(self, p):
        super().update_resources(p)
        if p.orange_used[1]:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['faction_octagon'].reload()

             


class BalTakBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/baltak.jpg'
        spec_button = HoverButton()
        spec_button.action_type = c.BAL_TAK_SPECIAL
        spec_button.size_hint = (190 / 3483, 82 / 2225)
        spec_button.pos_hint = {'x': 3111 / 3483, 'y': 1642 / 2225}
        spec_button.background_normal = ''
        spec_button.background_color = (0, 0, 0, 0)
        spec_button.bind(
            on_release=functools.partial(self.free_action, spec_button.action_type)
        )
        self.ids['board_layout'].add_widget(spec_button)
        self.gaia_gfm = GridLayout(cols=3, rows=1)
        self.gaia_gfm.size_hint = (354/3483, 125/2225)
        self.gaia_gfm.pos_hint = {'x': 30/3483, 'y': 1758/2225}
        self.ids['board_layout'].add_widget(self.gaia_gfm)

    def update_resources(self, p):
        super().update_resources(p)
        gfm_count = p.gfm_in_gaia
        self.gaia_gfm.clear_widgets()
        while gfm_count > 0:
            gfm = Image(source=f'{c.ASSETS_PATH}/colors/orange/gaiaformer_board.png')
            self.gaia_gfm.add_widget(gfm)
            gfm_count -= 1




class DerSchwarmBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/derschwarm.jpg'
        pli_button = HoverButton()
        pli_button.action_type = c.DER_SCHWARM_PLI
        pli_button.size_hint = (464 / 3483, 339 / 2225)
        pli_button.pos_hint = {'x': 781 / 3483, 'y': 865 / 2225}
        pli_button.background_normal = ''
        pli_button.background_color = (0, 0, 0, 0)
        pli_button.bind(
            on_release=functools.partial(self.action, pli_button.action_type)
        )
        self.ids['board_layout'].add_widget(pli_button)        
        self.ids['faction_octagon'].size_hint = (464 / 3483, 339 / 2225)
        self.ids['faction_octagon'].pos_hint = {'x': 781 / 3483, 'y': 865 / 2225}

    def update_resources(self, p):
        super().update_resources(p)
        if p.orange_used[1]:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['faction_octagon'].reload()


class FiraksBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/firaks.jpg'
        self.pli_button = HoverButton()
        self.pli_button.action_type = c.FIRAKS_PLI
        self.pli_button.size_hint = (460 / 3483, 325 / 2225)
        self.pli_button.pos_hint = {'x': 785 / 3483, 'y': 875 / 2225}
        self.pli_button.background_normal = ''
        self.pli_button.background_color = (0, 0, 0, 0)
        self.pli_button.bind(
            on_release=functools.partial(self.action, self.pli_button.action_type)
        )
        self.ids['board_layout'].add_widget(self.pli_button)
        self.ids['faction_octagon'].size_hint = (460 / 3483, 325 / 2225)
        self.ids['faction_octagon'].pos_hint = {'x': 785 / 3483, 'y': 875 / 2225}


    def update_resources(self, p):
        super().update_resources(p)
        if p.orange_used[1]:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['faction_octagon'].reload()


class GeodenBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/geoden.jpg'


class GleenBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/gleen.jpg'


class HadschHallaBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/hadschhalla.jpg'
        knw1_button = HoverButton()
        knw1_button.action_type = c.HH_GLD_TO_KNW
        knw1_button.size_hint = (210 / 3483, 82 / 2225)
        knw1_button.pos_hint = {'x': 948 / 3483, 'y': 900 / 2225}
        knw1_button.background_normal = ''
        knw1_button.background_color = (0, 0, 0, 0)
        knw1_button.bind(
            on_release=functools.partial(self.free_action, knw1_button.action_type)
        )
        self.ids['board_layout'].add_widget(knw1_button)
        knw2_button = HoverButton()
        knw2_button.action_type = c.HH_GLD_TO_ORE
        knw2_button.size_hint = (210 / 3483, 82 / 2225)
        knw2_button.pos_hint = {'x': 948 / 3483, 'y': 986 / 2225}
        knw2_button.background_normal = ''
        knw2_button.background_color = (0, 0, 0, 0)
        knw2_button.bind(
            on_release=functools.partial(self.free_action, knw2_button.action_type)
        )
        self.ids['board_layout'].add_widget(knw2_button)
        knw3_button = HoverButton()
        knw3_button.action_type = c.HH_GLD_TO_QIC
        knw3_button.size_hint = (210 / 3483, 82 / 2225)
        knw3_button.pos_hint = {'x': 948 / 3483, 'y': 1075 / 2225}
        knw3_button.background_normal = ''
        knw3_button.background_color = (0, 0, 0, 0)
        knw3_button.bind(
            on_release=functools.partial(self.free_action, knw3_button.action_type)
        )
        self.ids['board_layout'].add_widget(knw3_button)


class ItarBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/itar.jpg'
        self.gaia_phase_btn = Button(text='Beende Gaia Phase', on_release=self.end_gaia_phase)
        self.gaia_phase_btn.size_hint = (483/3483, 102/2225)
        self.gaia_phase_btn.pos_hint = {'x': 750/3483, 'y': 735/2225}
        gaia_tech = HoverButton()
        gaia_tech.action_type = c.ITAR_PLI
        gaia_tech.size_hint = (470/3483, 280/2225)
        gaia_tech.pos_hint = {'x': 783/3483, 'y': 902/2225}
        gaia_tech.background_normal = ''
        gaia_tech.background_color = (0, 0, 0, 0)
        gaia_tech.bind(
            on_release=functools.partial(self.action, gaia_tech.action_type)
        )
        self.ids['board_layout'].add_widget(gaia_tech)

    def show_itar_gaia_phase_btn(self):
        Clock.schedule_once(self.clock_show_itar_gaia_phase_btn)

    def clock_show_itar_gaia_phase_btn(self, *largs):        
        self.ids['board_layout'].add_widget(self.gaia_phase_btn)

    def end_gaia_phase(self, *args):
        self.ids['board_layout'].remove_widget(self.gaia_phase_btn)
        mainApp.gaia_inst.req_finish_round()

    def update_resources(self, p):
        if not mainApp.gaia_inst.booster_phase and self.gaia_phase_btn.parent is not None:
            self.ids['board_layout'].remove_widget(self.gaia_phase_btn)
        super().update_resources(p)


class LantidaBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/lantida.jpg'


class MadAndroidsBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/madandroids.jpg'
        spec_button = HoverButton()
        spec_button.action_type = c.MAD_ANDROIDS_SPECIAL
        spec_button.size_hint = (367 / 3483, 268 / 2225)
        spec_button.pos_hint = {'x': 2828 / 3483, 'y': 1605 / 2225}
        spec_button.background_normal = ''
        spec_button.background_color = (0, 0, 0, 0)
        spec_button.bind(on_release=functools.partial(self.action, spec_button.action_type))
        self.ids['board_layout'].add_widget(spec_button)
        self.ids['faction_octagon'].size_hint = (367 / 3483, 268 / 2225)
        self.ids['faction_octagon'].pos_hint = {'x': 2828 / 3483, 'y': 1605 / 2225}  
        self.init = True

    def update_resources(self, p):
        super().update_resources(p)
        if self.init:
            self.ids['pli'].pos_hint = {'x': 1633 / 3483, 'y': 860 / 2225}
            self.ids['left_ac'].pos_hint = {'x': 390 / 3483, 'y': 860 / 2225}
            self.ids['right_ac'].pos_hint = {'x': 783 / 3483, 'y': 860 / 2225}
            self.ids['ac_octagon'].pos_hint = {'x': 810 / 3483, 'y': 891 / 2225}
            self.init = False
        if p.orange_used[1]:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['faction_octagon'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['faction_octagon'].reload()


class NevlaBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/nevla.jpg'
        spec_button = HoverButton()
        spec_button.action_type = c.SPECIAL_NEVLA
        spec_button.size_hint = (222 / 3483, 124 / 2225)
        spec_button.pos_hint = {'x': 3068 / 3483, 'y': 1760 / 2225}
        spec_button.background_normal = ''
        spec_button.background_color = (0, 0, 0, 0)
        spec_button.bind(
            on_release=functools.partial(self.free_action, spec_button.action_type)
        )
        self.ids['board_layout'].add_widget(spec_button)


class TaklonsBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/taklons.jpg'
        self.brainstone_img = Image(source=f'{c.ASSETS_PATH}/currencies/brainstone.png')
        self.brainstone_img.size_hint = (120/3483, 123/2225)
        self.brainstone_img.pos_hint = {'x': 711/3483, 'y': 1433/2225}
        self.ids['board_layout'].add_widget(self.brainstone_img)
        self.strat_btn = Button(text='')
        self.strat_btn.size_hint = (305/3483, 105/2225)
        self.strat_btn.pos_hint = {'x': 915/3483, 'y': 1132/2225}
        self.strat_btn.bind(
            on_release=functools.partial(self.free_action, c.TAKLONS_PLI)
        )

    def update_resources(self, p):
        super().update_resources(p)
        if p.brainstone == 0:
            self.brainstone_img.pos_hint = {'x': 668/3483, 'y': 1433/2225}
        elif p.brainstone == 1:
            self.brainstone_img.pos_hint = {'x': 700/3483, 'y': 1823/2225}
        elif p.brainstone == 2:
            self.brainstone_img.pos_hint = {'x': 1424/3483, 'y': 1631/2225}
        elif p.brainstone == 3:
            self.brainstone_img.pos_hint = {'x': 210/3483, 'y': 1417/2225}
        if p.brainstone == -1:
            self.brainstone_img.source = f'{c.ASSETS_PATH}/empty.png'
        else:
            self.brainstone_img.source = f'{c.ASSETS_PATH}/currencies/brainstone.png'
        self.brainstone_img.reload()
        if p.pli_built and self.strat_btn.parent is None:
            self.ids['board_layout'].add_widget(self.strat_btn)
        elif (not p.pli_built) and self.strat_btn.parent is not None:
            self.ids['board_layout'].remove_widget(self.strat_btn)        
        if p.maximize_pwr_gain:
            self.strat_btn.text = 'Max PWR gain'
        else:
            self.strat_btn.text = 'Min VPS loss'


class TerranerBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/terraner.jpg'
        pwr1_button = HoverButton()
        pwr1_button.action_type = c.TER_TO_QIC
        pwr1_button.size_hint = (235 / 3483, 75 / 2225)
        pwr1_button.pos_hint = {'x': 983 / 3483, 'y': 1113 / 2225}
        pwr1_button.background_normal = ''
        pwr1_button.background_color = (0, 0, 0, 0)
        pwr1_button.bind(
            on_release=functools.partial(self.free_action, pwr1_button.action_type)
        )
        self.ids['board_layout'].add_widget(pwr1_button)
        pwr2_button = HoverButton()
        pwr2_button.action_type = c.TER_TO_ORE
        pwr2_button.size_hint = (235 / 3483, 66 / 2225)
        pwr2_button.pos_hint = {'x': 983 / 3483, 'y': 1035 / 2225}
        pwr2_button.background_normal = ''
        pwr2_button.background_color = (0, 0, 0, 0)
        pwr2_button.bind(
            on_release=functools.partial(self.free_action, pwr2_button.action_type)
        )
        self.ids['board_layout'].add_widget(pwr2_button)
        pwr3_button = HoverButton()
        pwr3_button.action_type = c.TER_TO_KNW
        pwr3_button.size_hint = (235 / 3483, 66 / 2225)
        pwr3_button.pos_hint = {'x': 983 / 3483, 'y': 954 / 2225}
        pwr3_button.background_normal = ''
        pwr3_button.background_color = (0, 0, 0, 0)
        pwr3_button.bind(
            on_release=functools.partial(self.free_action, pwr3_button.action_type)
        )
        self.ids['board_layout'].add_widget(pwr3_button)
        pwr4_button = HoverButton()
        pwr4_button.action_type = c.TER_TO_GLD
        pwr4_button.size_hint = (235 / 3483, 66 / 2225)
        pwr4_button.pos_hint = {'x': 983 / 3483, 'y': 880 / 2225}
        pwr4_button.background_normal = ''
        pwr4_button.background_color = (0, 0, 0, 0)
        pwr4_button.bind(
            on_release=functools.partial(self.free_action, pwr4_button.action_type)
        )
        self.ids['board_layout'].add_widget(pwr4_button)


class XenosBoard(FactionBoard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids['Background'].source = f'{c.ASSETS_PATH}/factions/xenos.jpg'


FACTION_BOARDS = {
    c.AMBAS: AmbasBoard,
    c.BAL_TAK: BalTakBoard,
    c.DER_SCHWARM: DerSchwarmBoard,
    c.FIRAKS: FiraksBoard,
    c.GEODEN: GeodenBoard,
    c.GLEEN: GleenBoard,
    c.HADSCH_HALLA: HadschHallaBoard,
    c.ITAR: ItarBoard,
    c.LANTIDA: LantidaBoard,
    c.MAD_ANDROIDS: MadAndroidsBoard,
    c.NEVLA: NevlaBoard,
    c.TAKLONS: TaklonsBoard,
    c.TERRANER: TerranerBoard,
    c.XENOS: XenosBoard,
}


class FactionButton(Button, HoverBehavior):

    faction = StringProperty()
    chooseable = BooleanProperty(True)

    def get_id(self):
        for id_, widget in mainApp.root.get_screen('faction_setup').ids.items():
            if widget.__self__ == self:
                return id_

    def on_enter(self, *args):
        x, y = mainApp.Window.mouse_pos

        x, y = self.to_widget(x, y)
        x, y = self.to_parent(x, y, relative=True)
        width, height = self.parent.size
        while x > (width * 0.3):
            x -= int(width * 0.1)
        y = min(y, height * 0.3)
        mainApp.root.get_screen(
            'faction_setup'
        ).ids.img.source = f'{c.ASSETS_PATH}/factions/{self.faction.lower()}_preview.jpg'
        mainApp.root.get_screen('faction_setup').ids.img.pos = (x, y)
        mainApp.root.get_screen('faction_setup').ids.img.reload()

    def on_leave(self, *args):
        mainApp.root.get_screen('faction_setup').ids.img.source = f'{c.ASSETS_PATH}/empty.png'
        mainApp.root.get_screen('faction_setup').ids.img.reload()

    def choose_faction(self):
        if mainApp.gaia_inst.my_turn():
            if self.chooseable:
                mainApp.gaia_inst.req_choose_faction(self.faction)                              
            else:
                mainApp.your_turn_popup('Diese Farbe ist schon vergeben')



# The different Screens for the App


class BoardWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.is_bound = False

    def bind_hover(self):
        if not self.is_bound:
            board = self.ids['board']
            board.ids['booster_action'].do_bind()
            board.ids['finish_button'].do_bind()
            for tech in board.ids['tech_layout'].children:
                if isinstance(tech, Factory.TechButton):
                    tech.children[0].do_bind()
                elif isinstance(tech, Image) and len(tech.children) > 0:
                    t_w_a_layout = tech.children[0]
                    for widget in t_w_a_layout.children:
                        if isinstance(widget, Factory.TechButton):
                            widget.children[0].do_bind()
            p_board = board.ids['board_grid'].children[0]
            for widget in p_board.ids['board_layout'].children:
                if isinstance(widget, HoverBehavior):
                    widget.do_bind()
            self.is_bound = True

    def unbind_hover(self):
        if self.is_bound:
            board = self.ids['board']
            board.ids['booster_action'].do_unbind()
            board.ids['finish_button'].do_unbind()
            for tech in board.ids['tech_layout'].children:
                if isinstance(tech, Factory.TechButton):
                    tech.children[0].do_unbind()
                elif isinstance(tech, Image) and len(tech.children) > 0:
                    t_w_a_layout = tech.children[0]
                    for widget in t_w_a_layout.children:
                        if isinstance(widget, Factory.TechButton):
                            widget.children[0].do_unbind()
            p_board = board.ids['board_grid'].children[0]
            for widget in p_board.ids['board_layout'].children:
                if isinstance(widget, HoverBehavior):
                    widget.do_unbind()
            self.is_bound = False

    def save_faction(self, pos, fac_type):        
        Clock.schedule_once(functools.partial(self.clock_save_faction, pos, fac_type))
        
    def clock_save_faction(self, pos, fac_type, *args):
        # add the right faction board to the board view
        self.ids['board'].player = pos
        f_board = FACTION_BOARDS[fac_type]()
        f_board.player = pos
        self.ids['board'].ids['board_grid'].add_widget(f_board)
        self.ids['f_board'] = f_board._proxy_ref

    def clock_update_pat(self, label_text, *largs):
        self.ids['pat_label'].text = label_text 


class Board(RelativeLayout):
    player = NumericProperty(0)

    def enable_actions(self):
        return (
            mainApp.gaia_inst.round > 0
            and self.player == mainApp.gaia_inst.my_pos
            and mainApp.gaia_inst.my_turn()
        )

    def flip_booster(self):
        if mainApp.gaia_inst.players[self.player].current_booster:
            if mainApp.gaia_inst.players[self.player].has_finished:
                self.ids[
                    'booster_img'
                ].source = f'{c.ASSETS_PATH}/boosters/{mainApp.gaia_inst.players[self.player].current_booster}'
            else:
                self.ids['booster_img'].source = f'{c.ASSETS_PATH}/boosters/BOO_flipped.png'
                self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/empty.png'
                self.ids['boo_oct'].reload()
            self.ids['booster_img'].reload()

    def flip_back_booster(self):
        if mainApp.gaia_inst.players[self.player].current_booster:
            if not mainApp.gaia_inst.players[self.player].has_finished:
                self.ids[
                    'booster_img'
                ].source = f'{c.ASSETS_PATH}/boosters/{mainApp.gaia_inst.players[self.player].current_booster}'
                if mainApp.gaia_inst.players[self.player].orange_used[2]:
                    self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
                else:
                    self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/empty.png'
            else:
                self.ids['booster_img'].source = f'{c.ASSETS_PATH}/boosters/BOO_flipped.png'
                self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/empty.png'
            self.ids['boo_oct'].reload()
            self.ids['booster_img'].reload()


    def booster_action(self):
        if self.enable_actions():
            if self.ids['booster_action'].action_type in [c.BOO_NAV, c.BOO_TER]:
                result = mainApp.gaia_inst.req_booster_action(self.ids['booster_action'].action_type)
                if result == c.ALREADY_USED:
                    mainApp.error_popup(result)

    def tech_action(self, action_type, *args):
        result = mainApp.gaia_inst.tech_action(action_type)
        if result != c.POSSIBLE:
            mainApp.error_popup(result)  

    def finish_round(self):
        if self.enable_actions():
            mainApp.gaia_inst.req_finish_round()

    def update_resources(self):
        Clock.schedule_once(self.clock_update_resources)

    def clock_update_resources(self, *args):
        p = mainApp.gaia_inst.players[self.player]
        if p.has_finished:
            self.ids['booster_img'].source = f'{c.ASSETS_PATH}/boosters/BOO_flipped.png'
        else:
            self.ids['booster_img'].source = (
                f'{c.ASSETS_PATH}/boosters/{p.current_booster}'
                if p.current_booster
                else f'{c.ASSETS_PATH}/empty.png'
            )   
        self.ids['booster_img'].reload()
        self.ids['booster_action'].action_type = (
            p.current_booster if p.current_booster else ''
        )
        if p.current_booster in [c.BOO_NAV, c.BOO_TER] and not p.orange_used[2]:
            self.ids['booster_action'].hover_color = [0, 1, 0, 0.2]
        else:
            self.ids['booster_action'].hover_color = [0, 0, 0, 0] 
        # update qic
        self.ids['qic_layout'].clear_widgets()
        for _i in range(p.qic):
            self.ids['qic_layout'].add_widget(
                Image(source=f'{c.ASSETS_PATH}/currencies/qic.png')
            )
        # update fed markers
        flip = len(p.fed_markers) - p.green_fed_markers
        self.ids['fed_layout'].clear_widgets()
       # FED VPS is always flipped, check if it is in fed markers first
        fed_vps_special = p.fed_markers.copy()
        for _i in range(3):
            if c.FED_VPS in fed_vps_special:
                flip -= 1
                self.ids['fed_layout'].add_widget(
                    Image(source=f'{c.ASSETS_PATH}/federations/{c.FED_VPS}.png')
                )
                fed_vps_special = fed_vps_special[(fed_vps_special.index(c.FED_VPS) + 1):]
            else:
                break
        for fed in p.fed_markers:
            if fed == c.FED_VPS:
                break
            if flip > 0:
                flip -= 1
                self.ids['fed_layout'].add_widget(
                    Image(source=f'{c.ASSETS_PATH}/federations/{fed}_flipped.png')
                )
            else:
                self.ids['fed_layout'].add_widget(
                    Image(source=f'{c.ASSETS_PATH}/federations/{fed}.png')
                )
        self.ids['tech_layout'].clear_widgets()
        for idx in range(len(p.tech_tiles)):
            tech = p.tech_tiles[idx]
            if p.adv_tiles[idx] is None:
                if tech == c.TEC_POW:
                    if not p.orange_used[3]:
                        tech_img = Factory.TechButton(source=f'{c.ASSETS_PATH}/tech/{tech}')
                        tech_img.size_hint = (0.5, None)
                        if mainApp.gaia_inst.choose_cover:
                            if p.adv_tiles[idx] is None:
                                tech_img.children[0].bind(on_release=functools.partial(self.pick_cover, tech))
                        else:
                            tech_img.children[0].bind(
                                on_release=functools.partial(self.tech_action, tech)
                            )
                        self.ids['tech_layout'].add_widget(tech_img)
                    else:
                        if mainApp.gaia_inst.choose_cover and p.adv_tiles[idx] is None:                            
                            tech_with_oct = Factory.TechButton()
                            tech_with_oct.children[0].bind(on_release=functools.partial(self.pick_cover, tech))
                        else:
                            tech_with_oct = Image()
                        tech_with_oct.size_hint = (0.5, None)
                        tech_with_oct.source = f'{c.ASSETS_PATH}/tech/{tech}'
                        self.ids['tech_layout'].add_widget(tech_with_oct)
                        Clock.schedule_once(functools.partial(self.clock_tech_oct, tech), timeout=0.05)
                elif tech in mainApp.gaia_inst.tech:
                    if mainApp.gaia_inst.choose_cover and p.adv_tiles[idx] is None:
                        tech_img = Factory.TechButton()
                        tech_img.children[0].bind(on_release=functools.partial(self.pick_cover, tech))
                    else:
                        tech_img = Image() 
                    tech_img.source = f'{c.ASSETS_PATH}/tech/{tech}'                   
                    tech_img.size_hint = (0.5, None)
                    tech_img.allow_stretch = True
                        
                    self.ids['tech_layout'].add_widget(tech_img)
            else:
                tech_with_adv = Image()
                tech_with_adv.size_hint = (0.5, None)
                tech_with_adv.source = f'{c.ASSETS_PATH}/tech/{tech}'
                self.ids['tech_layout'].add_widget(tech_with_adv)
                Clock.schedule_once(functools.partial(self.clock_tech_adv, tech, idx, p), timeout=0.05)
        if p.orange_used[2]:
            self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
        else:
            self.ids['boo_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['boo_oct'].reload()
                

        # update resources on the faction board
        self.ids['board_grid'].children[0].update_resources(p)

    def clock_tech_oct(self, tech, *largs):
        for child in self.ids['tech_layout'].children:
            if child.source == f'{c.ASSETS_PATH}/tech/{tech}':
                child.offset = [
                    child.center_x - child.norm_image_size[0] / 2,
                    child.center_y - child.norm_image_size[1] / 2,
                ]
                tech_with_oct = child
                break
        t_w_o_layout = RelativeLayout()
        t_w_o_layout.pos = tech_with_oct.offset
        t_w_o_layout.size = tech_with_oct.norm_image_size
        octagon = Image(source=f'{c.ASSETS_PATH}/octagon.png')
        octagon.size_hint = (81 / 178, 76 / 134)
        octagon.pos_hint = {'x': 48 / 178, 'y': 30 / 134}
        octagon.allow_stretch = True
        t_w_o_layout.add_widget(octagon)
        tech_with_oct.add_widget(t_w_o_layout)

    def clock_tech_adv(self, tech, idx, p, *largs):
        for child in self.ids['tech_layout'].children:
            if child.source == f'{c.ASSETS_PATH}/tech/{tech}':
                child.offset = [
                    child.center_x - child.norm_image_size[0] / 2,
                    child.center_y - child.norm_image_size[1] / 2,
                ]
                tech_with_adv = child
                break
        t_w_a_layout = RelativeLayout()
        t_w_a_layout.pos = tech_with_adv.offset
        t_w_a_layout.size = tech_with_adv.norm_image_size
        if p.adv_tiles[idx] in [c.ADV_ORE, c.ADV_KNW, c.ADV_QIC]:
            adv_tech = Factory.TechButton(source=f'{c.ASSETS_PATH}/tech/{p.adv_tiles[idx]}')
            t_w_a_layout.add_widget(adv_tech)
            if ((p.orange_used[4] and p.adv_tiles[idx]==c.ADV_QIC) or 
                (p.orange_used[5] and p.adv_tiles[idx]==c.ADV_ORE) or
                (p.orange_used[6] and p.adv_tiles[idx]==c.ADV_KNW)):
                octagon = Image(source=f'{c.ASSETS_PATH}/octagon.png')
                octagon.size_hint = (92 / 178, 86 / 134)
                octagon.pos_hint = {'x': 29 / 178, 'y': 32 / 134}
                octagon.allow_stretch = True
                t_w_a_layout.add_widget(octagon)
            else:
                adv_tech.children[0].bind(on_release=functools.partial(self.tech_action, p.adv_tiles[idx]))
            adv_tech.size_hint = (167/178, 132/134)
            adv_tech.pos_hint = {'x': 5 / 178, 'y': 1 / 134}
        else:
            adv_tech = Image(source=f'{c.ASSETS_PATH}/tech/{p.adv_tiles[idx]}')
            adv_tech.size_hint = (167/178, 132/134)
            adv_tech.pos_hint = {'x': 5 / 178, 'y': 1 / 134}
            t_w_a_layout.add_widget(adv_tech)
        tech_with_adv.add_widget(t_w_a_layout)

    def pick_cover(self, tech, *largs):
        result = mainApp.gaia_inst.pick_cover(tech)
        if result not in [c.POSSIBLE_NO_LVL_UP, c.POSSIBLE]:
            if result == c.NEED_CHOOSE_TRACK:
                mainApp.switch_screen('research_board')
            mainApp.your_turn_popup(result)


class MapWindow(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)  
        self.build_fed = False
        self.sats = set()
        self.current_pos = None
        self.current_popup = None
        self.fed_layout = RelativeLayout()
        # list of all images of already built buildings
        self.buildings = {}

    # FUNCTIONS FOR BUILDING IMAGES ON MAP

    def place_building(self, q, r, color, bld_type):
        mainApp.switch_screen('map')
        Clock.schedule_once(
            functools.partial(self.clock_place_building, q, r, color, bld_type),
            0 if color == mainApp.colors[mainApp.gaia_inst.my_pos] else 0.3,
        )

    def clock_place_building(self, q, r, color, bld_type, *largs):
        radius = self.ids['MapLayout'].size[0] / 30.5
        x, y = maptools.hex_to_pixel(q, r, radius)
        image = Image(
            source=f'{c.ASSETS_PATH}/colors/{color}/{bld_type}'
        )
        image.pos_hint = {
            'x': x / self.ids['MapLayout'].size[0],
            'y': y / self.ids['MapLayout'].size[1],
        }
        image.size_hint = (
            2 * radius / self.ids['MapLayout'].size[0],
            2 * radius / self.ids['MapLayout'].size[1],
        )
        self.ids['MapLayout'].add_widget(image)         
        self.buildings[(q, r)] = image

    def upgrade_building(self, pos, color, bld_type):
        mainApp.switch_screen('map')
        Clock.schedule_once(
            functools.partial(self.clock_upgrade_building, pos, color, bld_type),
            0 if color == mainApp.colors[mainApp.gaia_inst.my_pos] else 0.3,
        )

    def clock_upgrade_building(self, pos, color, bld_type, *largs):
        self.buildings[pos].source = f'{c.ASSETS_PATH}/colors/{color}/{bld_type}'
        self.buildings[pos].reload()

    def place_black_planet(self, q, r, gaia_map):
        planet = gaia_map[(q,r)]
        color = mainApp.colors[planet[1]] 
        Clock.schedule_once(functools.partial(self.clock_place_black_planet,q, r, color))
        
    
    def clock_place_black_planet(self, q, r, color, *largs):
        radius = self.ids['MapLayout'].size[0] / 30.5
        x, y = maptools.hex_to_pixel(q, r, radius)
        image = Image(
            source=f'{c.ASSETS_PATH}/blackplanet.png'
        )
        image.pos_hint = {
            'x': x / self.ids['MapLayout'].size[0],
            'y': y / self.ids['MapLayout'].size[1],
        }
        image.size_hint = (
            2 * radius / self.ids['MapLayout'].size[0],
            2 * radius / self.ids['MapLayout'].size[1],
        )
        self.ids['MapLayout'].add_widget(image)
        sat = Image(
            source=f'{c.ASSETS_PATH}/colors/{color}/satellite.png'
        )
        sat.pos_hint = {
            'x': (x + 1.1*radius)/ self.ids['MapLayout'].size[0],
            'y': (y + radius)/ self.ids['MapLayout'].size[1],
        }
        sat.size_hint = (
            0.7 * radius / self.ids['MapLayout'].size[0],
            0.7 * radius / self.ids['MapLayout'].size[1],
        )
        self.ids['MapLayout'].add_widget(sat)
        self.buildings[(q,r)] = (image, sat)

    def clock_add_lantida_mine(self, pos, in_fed):
        radius = self.ids['MapLayout'].size[0] / 30.5
        x, y = maptools.hex_to_pixel(pos[0], pos[1], radius)
        l_mne = Image(source=f'{c.ASSETS_PATH}/colors/blue/lantida_mine.png')
        y += 0.4*radius
        x += 0.9*radius
        l_mne.pos_hint = {
            'x': x / self.ids['MapLayout'].size[0],
            'y': y / self.ids['MapLayout'].size[1],
        }
        l_mne.size_hint = (
            radius / self.ids['MapLayout'].size[0],
            radius / self.ids['MapLayout'].size[1],
        )
        self.fed_layout.add_widget(l_mne)
        if in_fed:
            x += 0.2*radius
            image = Image(
                source=f'{c.ASSETS_PATH}/fed_mark.png'
            )
            image.pos_hint = {
                'x': x / self.ids['MapLayout'].size[0],
                'y': y / self.ids['MapLayout'].size[1],
            }
            image.size_hint = (
                (0.6*radius) / self.ids['MapLayout'].size[0],
                (0.4*radius) / self.ids['MapLayout'].size[1],
            )
            self.fed_layout.add_widget(image)

    def update_map(self, gaia_map, fed_possible):
        Clock.schedule_once(functools.partial(self.clock_update_map, gaia_map, fed_possible))

    def clock_update_map(self, gaia_map, fed_possible, *largs):
        if self.fed_layout.parent is not None:
            self.ids['MapLayout'].remove_widget(self.fed_layout)
        self.fed_layout = RelativeLayout(size_hint=(1,1))
        for pos in self.buildings:
            if pos not in gaia_map:
                if isinstance(self.buildings[pos], tuple):
                    # black planet has been removed
                    self.ids['MapLayout'].remove_widget(self.buildings[pos][0])
                    self.ids['MapLayout'].remove_widget(self.buildings[pos][1])                
                    self.buildings.pop(pos)
                for p in mainApp.gaia_inst.players:
                    if p.faction_type == c.DER_SCHWARM:
                        if pos in p.ivit_sats:
                            break
                        else:
                            self.ids['MapLayout'].remove_widget(self.buildings[pos])
                            self.buildings.pop(pos)
        for pos, planet in gaia_map.items():
            if planet[1] == None:
                if pos in self.buildings:
                    # remove building from map
                    self.ids['MapLayout'].remove_widget(self.buildings[pos])
                    self.buildings.pop(pos)
            else:
                color = mainApp.colors[planet[1]] 
                bld_type = planet[2]
                if planet[3]:
                    q, r = pos
                    radius = self.ids['MapLayout'].size[0] / 30.5
                    x, y = maptools.hex_to_pixel(q, r, radius)
                    image = Image(
                        source=f'{c.ASSETS_PATH}/fed_mark.png'
                    )
                    image.pos_hint = {
                        'x': (x + 0.6*radius) / self.ids['MapLayout'].size[0],
                        'y': y / self.ids['MapLayout'].size[1],
                    }
                    image.size_hint = (
                        (0.8*radius) / self.ids['MapLayout'].size[0],
                        (0.5*radius) / self.ids['MapLayout'].size[1],
                    )
                    self.fed_layout.add_widget(image) 
                if planet[0] == c.BLACK_PLANET:
                    if pos not in self.buildings:
                        self.clock_place_black_planet(pos[0],pos[1],color, None)
                    if planet[4] > 0:
                        self.clock_add_lantida_mine(pos, (planet[4] == 2))
                    continue
                if pos in self.buildings:
                    if (not self.buildings[pos].source == f'{c.ASSETS_PATH}/colors/{color}/{bld_type}'):
                        self.upgrade_building(pos, color, bld_type)
                    elif (not self.build_fed) and self.buildings[pos].canvas.has_after:
                        self.buildings[pos].canvas.after.clear()
                else:
                    if planet[0] == c.GAIAFORMED:
                        # add gaia planet if update gaia was skipped (e.g. on rejoin)
                        q, r = pos
                        radius = self.ids['MapLayout'].size[0] / 30.5
                        x, y = maptools.hex_to_pixel(q, r, radius)
                        bg = Image(source=f'{c.ASSETS_PATH}/gaiaplanet.png')
                        bg.pos_hint = {
                            'x': x / self.ids['MapLayout'].size[0],
                            'y': y / self.ids['MapLayout'].size[1],
                        }
                        bg.size_hint = (
                            2 * radius / self.ids['MapLayout'].size[0],
                            2 * radius / self.ids['MapLayout'].size[1],
                        )
                        self.ids['MapLayout'].add_widget(bg)
                    self.place_building(pos[0], pos[1], color, bld_type)
                if planet[4] > 0:
                    self.clock_add_lantida_mine(pos, (planet[4] == 2))        
        self.ids['MapLayout'].add_widget(self.fed_layout)
        for p in mainApp.gaia_inst.players:
            if p.faction_type == c.DER_SCHWARM:
                for pos in p.ivit_sats:
                    if pos not in self.buildings:
                        q, r = pos
                        radius = self.ids['MapLayout'].size[0] / 30.5
                        x, y = maptools.hex_to_pixel(q, r, radius)
                        image = Image(
                            source=f'{c.ASSETS_PATH}/colors/red/ivit_satellite.png'
                        )
                        # offset ivit satellites
                        y += 0.5*radius
                        x += 0.5*radius  
                        image.pos_hint = {
                            'x': x / self.ids['MapLayout'].size[0],
                            'y': y / self.ids['MapLayout'].size[1],
                        }
                        image.size_hint = (
                            radius / self.ids['MapLayout'].size[0],
                            radius / self.ids['MapLayout'].size[1],
                        )
                        self.ids['MapLayout'].add_widget(image)
                        self.buildings[pos] = image
            for pos in p.satellites:
                q, r = pos
                radius = self.ids['MapLayout'].size[0] / 30.5
                x, y = maptools.hex_to_pixel(q, r, radius)
                image = Image(
                    source=f'{c.ASSETS_PATH}/colors/{p.color}/satellite.png'
                )
                # offset satellites
                y += 0.9*radius if p.pos > 1 else 0.1*radius
                x += 0.9*radius if p.pos in [1, 3] else 0.1*radius  
                image.pos_hint = {
                    'x': x / self.ids['MapLayout'].size[0],
                    'y': y / self.ids['MapLayout'].size[1],
                }
                image.size_hint = (
                    radius / self.ids['MapLayout'].size[0],
                    radius / self.ids['MapLayout'].size[1],
                )
                self.fed_layout.add_widget(image)
        self.clock_fed_possible(fed_possible)  


    def clock_update_pat(self, label_text, *largs):
        self.ids['pat_label'].text = label_text


    # FUNCTIONS FOR INTERACTIONS ON THE MAP

    # starting or aborting the process of founding a federation
    def fed_button_pressed(self):
        if not self.build_fed:
            if mainApp.gaia_inst.start_build_fed():
                mainApp.your_turn_popup(text='Wähle Gebäude für die Allianz aus')
                self.build_fed = True
                self.ids['fed_button'].text = 'Abbrechen'
        else:
            self.build_fed = False
            mainApp.gaia_inst.cancel_build_fed()
            Clock.schedule_once(self.clock_cancel_fed)
            if (mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].faction_type == c.DER_SCHWARM and
                mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].gained_fed_markers > 0):
                self.ids['fed_button'].text = 'Erweitern'
            else:
                self.ids['fed_button'].text = 'Gründen' 

    def after_fed_finished(self, fed_possible):
        self.build_fed = False
        Clock.schedule_once(functools.partial(self.clock_fed_finished, fed_possible))

    def clock_fed_finished(self, fed_possible, *largs):
        # remove temporary widgets and place fixed sats
        self.ids['TempSatsLayout'].clear_widgets()
        p = mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos]
        for q,r in self.sats:
            radius = self.ids['MapLayout'].size[0] / 30.5
            x, y = maptools.hex_to_pixel(q, r, radius)
            image = Image(
                source=f'{c.ASSETS_PATH}/colors/{p.color}/satellite.png'
            )
            # offset satellites
            y += 0.9*radius if p.pos > 1 else 0.1*radius
            x += 0.9*radius if p.pos in [1, 3] else 0.1*radius  
            image.pos_hint = {
                'x': x / self.ids['MapLayout'].size[0],
                'y': y / self.ids['MapLayout'].size[1],
            }
            image.size_hint = (
                radius / self.ids['MapLayout'].size[0],
                radius / self.ids['MapLayout'].size[1],
            )
            self.fed_layout.add_widget(image)

        
        self.sats = set()
        if (mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].faction_type == c.DER_SCHWARM and
            mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].gained_fed_markers > 0):
            self.ids['fed_button'].text = 'Erweitern'
        else:
            self.ids['fed_button'].text = 'Gründen'
        self.clock_fed_possible(fed_possible=fed_possible)
        for pos in self.buildings.keys():
            if isinstance(self.buildings[pos], tuple):
                if self.buildings[pos][0].canvas.has_after:
                    self.buildings[pos][0].canvas.after.clear()
                    self.buildings[pos][0].canvas.ask_update() 
            else:
                if self.buildings[pos].canvas.has_after:
                    self.buildings[pos].canvas.after.clear()
                    self.buildings[pos].canvas.ask_update() 
        
    
    def clock_fed_possible(self, fed_possible, *largs):
        self.ids['fed_button'].disabled = not fed_possible

    def clock_update_fed_choice(self, fed, *largs):
        for pos in self.buildings:
            if pos in fed:
                # highlight planet
                if isinstance(self.buildings[pos], tuple):
                    self.buildings[pos][0].canvas.after.clear()
                    self.buildings[pos][0].canvas.after.add(Color(0,1,0,0.2))
                    self.buildings[pos][0].canvas.after.add(    
                        Ellipse(size=self.buildings[pos][0].size, pos=self.buildings[pos][0].pos)
                    )
                    self.buildings[pos][0].canvas.ask_update()
                else:
                    self.buildings[pos].canvas.after.clear()
                    self.buildings[pos].canvas.after.add(Color(0,1,0,0.2))
                    self.buildings[pos].canvas.after.add(    
                        Ellipse(size=self.buildings[pos].size, pos=self.buildings[pos].pos)
                    )
                    self.buildings[pos].canvas.ask_update()                
            else:
                # remove highlighting
                if isinstance(self.buildings[pos], tuple):
                    self.buildings[pos][0].canvas.after.clear()
                    self.buildings[pos][0].canvas.ask_update()
                else:
                    self.buildings[pos].canvas.after.clear()
                    self.buildings[pos].canvas.ask_update()

    def clock_update_sats(self, *largs):
        self.ids['TempSatsLayout'].clear_widgets()
        for q,r in self.sats:
            radius = self.ids['MapLayout'].size[0] / 30.5
            x, y = maptools.hex_to_pixel(q, r, radius)
            image = Image(
                source=f'{c.ASSETS_PATH}/colors/{mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].color}/satellite.png'
            )
            image.pos_hint = {
                'x': (x + 0.5*radius)/ self.ids['MapLayout'].size[0],
                'y': (y + 0.5*radius)/ self.ids['MapLayout'].size[1],
            }
            image.size_hint = (
                radius / self.ids['MapLayout'].size[0],
                radius / self.ids['MapLayout'].size[1],
            )
            self.ids['TempSatsLayout'].add_widget(image) 

    def cancel_fed(self, fed_possible):
        Clock.schedule_once(functools.partial(self.clock_cancel_fed, fed_possible))
    
    def clock_cancel_fed(self, fed_possible, *largs):        
        self.ids['TempSatsLayout'].clear_widgets()
        self.sats = set()
        self.build_fed = False
        self.ids['fed_button'].disabled = not fed_possible
        if (mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].faction_type == c.DER_SCHWARM and
            mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].gained_fed_markers > 0):
            self.ids['fed_button'].text = 'Erweitern'
        else:
            self.ids['fed_button'].text = 'Gründen'
        for pos in self.buildings:
            if isinstance(self.buildings[pos], tuple):
                if self.buildings[pos][0].canvas.has_after:
                    self.buildings[pos][0].canvas.after.clear()
                    self.buildings[pos][0].canvas.ask_update()
            elif self.buildings[pos].canvas.has_after:
                self.buildings[pos].canvas.after.clear()

    def update_gaia(self, gaia_map):
        Clock.schedule_once(functools.partial(self.clock_update_gaia, gaia_map))

    def clock_update_gaia(self, gaia_map, *largs):
        radius = self.ids['MapLayout'].size[0] / 30.5
        for pos, planet in gaia_map.items():
            if planet[0] == c.GAIAFORMED:
                q, r = pos
                x, y = maptools.hex_to_pixel(q, r, radius)
                bg = Image(source=f'{c.ASSETS_PATH}/gaiaplanet.png')
                bg.pos_hint = {
                    'x': x / self.ids['MapLayout'].size[0],
                    'y': y / self.ids['MapLayout'].size[1],
                }
                bg.size_hint = (
                    2 * radius / self.ids['MapLayout'].size[0],
                    2 * radius / self.ids['MapLayout'].size[1],
                )
                image = Image(
                    source=f'{c.ASSETS_PATH}/colors/{mainApp.colors[planet[1]]}/{planet[2]}'
                )
                image.pos_hint = {
                    'x': x / self.ids['MapLayout'].size[0],
                    'y': y / self.ids['MapLayout'].size[1],
                }
                image.size_hint = (
                    2 * radius / self.ids['MapLayout'].size[0],
                    2 * radius / self.ids['MapLayout'].size[1],
                )
                self.ids['MapLayout'].add_widget(bg)
                self.ids['MapLayout'].add_widget(image)
                self.buildings[(q, r)] = image

    def get_feedback(self, feedback):
        content_grid = GridLayout(rows=1)
        content_grid.spacing = 10
        content_grid.padding = 10
        if feedback == c.NEED_FEEDBACK_AC:
            l_button = Button(
                text='Linke \n Akademie', size_hint=(None, None), size=(100, 60)
            )
            l_button.bind(
                on_release=functools.partial(self.set_feedback, c.LEFT_ACADEMY)
            )
            content_grid.add_widget(l_button)
            r_button = Button(
                text='Rechte \n Akademie', size_hint=(None, None), size=(100, 60)
            )
            r_button.bind(
                on_release=functools.partial(self.set_feedback, c.RIGHT_ACADEMY)
            )
            content_grid.add_widget(r_button)
            self.current_popup = YourTurnPopup(
                title='Was willst du hier bauen?', title_size=18, content=content_grid, size=(250, 145)
            )
        elif feedback == c.NEED_FEEDBACK_TRD:
            if mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].faction_type == c.MAD_ANDROIDS:
                pi_text = 'Akademie'
                pi_arg = c.ACADEMY
            else:
                pi_text = 'Regierungs- \n sitz'
                pi_arg = c.PLANETARY_INSTITUTE
            pi_button = Button(
                text=pi_text, size_hint=(None, None), size=(100, 60)
            )
            pi_button.bind(
                on_release=functools.partial(self.set_feedback, pi_arg)
            )
            content_grid.add_widget(pi_button)
            l_button = Button(
                text='Forschungs- \n labor', size_hint=(None, None), size=(100, 60)
            )
            l_button.bind(on_release=functools.partial(self.set_feedback, c.LAB))
            content_grid.add_widget(l_button)
            self.current_popup = YourTurnPopup(
                title='Was willst du hier bauen?', title_size=18, content=content_grid, size=(250, 145)
            )
        elif feedback == c.NEED_FEEDBACK_FED:          
            yes_button = Button(
                text='Ja', size_hint=(None, None), size=(100, 40)
            )
            yes_button.bind(
                on_release=functools.partial(self.set_feedback, c.BUILD_FED)
            )
            content_grid.add_widget(yes_button)
            no_button = Button(
                text='Nein', size_hint=(None, None), size=(100, 40)
            )
            no_button.bind(on_release=functools.partial(self.set_feedback, c.CANCEL_ACTION))
            content_grid.add_widget(no_button)
            self.current_popup = YourTurnPopup(
                title=c.NEED_FEEDBACK_FED, title_size=18, content=content_grid, size=(300, 145)
            )
        else:
            return # do not open popup if feedback has no correct value        
        self.current_popup.size_hint = (None, None)
        self.current_popup.open()

    def set_feedback(self, feedback, *args):
        if not (self.current_popup is None):
            self.current_popup.dismiss()
        if feedback in [c.LAB, c.ACADEMY, c.PLANETARY_INSTITUTE, c.LEFT_ACADEMY, c.RIGHT_ACADEMY]:
            self.try_building(self.current_pos[0], self.current_pos[1], decision=feedback)
        # feedback for fed finished
        elif feedback == c.BUILD_FED:
            mainApp.gaia_inst.req_fed(self.sats)
        elif feedback == c.CANCEL_ACTION:
            mainApp.your_turn_popup(text='Ändere die Allianz,\num sie fertigzustellen')

    def try_building(self, q, r, decision=None):
        result = c.NOT_POSSIBLE
        # initial mine building
        if (
            mainApp.gaia_inst.round == 0
            and mainApp.gaia_inst.my_turn()
            and (q, r) in mainApp.gaia_inst.gaia_map
            and not (q, r) in self.buildings
        ):
            result = mainApp.gaia_inst.req_build_mine(q, r)
            if not result == c.POSSIBLE:
                mainApp.error_popup(result)
        # building during game rounds
        elif (
            mainApp.gaia_inst.round > 0
            and mainApp.gaia_inst.my_turn()
        ):
            if (q, r) in mainApp.gaia_inst.gaia_map:
                if (q, r) in list(self.buildings):
                    # fed building choice
                    if self.build_fed:
                        result = mainApp.gaia_inst.build_fed_add_planet(q, r)
                        # make planet selection visible on map
                        if result[0] == c.SUCCESS:
                            Clock.schedule_once(
                                functools.partial(self.clock_update_fed_choice, result[1])
                            )
                            result = mainApp.gaia_inst.check_fed_ready(self.sats)
                            if result == c.POSSIBLE:
                                self.get_feedback(c.NEED_FEEDBACK_FED)
                            elif result == c.FED_NOT_CONNECTED and not self.sats:
                                mainApp.your_turn_popup(c.NEED_CHOOSE_SATS)
                            return
                        else:
                            # call failed, set result to only error code to show in popup
                            result = result[0]
                        
                    # upgrade building
                    else:
                        result = mainApp.gaia_inst.req_upgrade_building(q, r, decision)
                        if result == c.NEED_FEEDBACK_TRD or result == c.NEED_FEEDBACK_AC:
                            self.current_pos = (q, r)
                            self.get_feedback(result)
                            return       
                # build mine                 
                else:
                    result = mainApp.gaia_inst.req_build_mine(q, r)
                if not (result == c.POSSIBLE or result == c.POSSIBLE_CHOOSE_TECH):
                    mainApp.error_popup(result)
            else:
                if self.build_fed:
                    if (mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].faction_type == c.DER_SCHWARM
                        and (q, r) in self.buildings):
                    # fed building add ivit sat
                        result = mainApp.gaia_inst.build_fed_add_planet(q, r)
                        # make planet selection visible on map
                        if result[0] == c.SUCCESS:
                            Clock.schedule_once(
                                functools.partial(self.clock_update_fed_choice, result[1])
                            )
                            result = mainApp.gaia_inst.check_fed_ready(self.sats)
                            if result == c.POSSIBLE:
                                self.get_feedback(c.NEED_FEEDBACK_FED)
                            elif result == c.FED_NOT_CONNECTED and not self.sats:
                                mainApp.your_turn_popup(c.NEED_CHOOSE_SATS)
                            return
                        else:
                            # call failed, set result to only error code to show in popup
                            result = result[0] 
                    elif mainApp.gaia_inst.choose_sats:
                        if (q,r) in self.sats:
                            self.sats.remove((q,r))
                        else:
                            self.sats.add((q,r))
                        Clock.schedule_once(self.clock_update_sats)
                        result = mainApp.gaia_inst.check_fed_ready(self.sats)
                        if result == c.POSSIBLE:
                            self.get_feedback(c.NEED_FEEDBACK_FED)                   
                elif mainApp.gaia_inst.choose_black_planet:
                    result = mainApp.gaia_inst.req_black_planet(q, r)
                    if not result == c.POSSIBLE:
                        mainApp.error_popup(result)
                elif mainApp.gaia_inst.action_started == c.DER_SCHWARM_PLI:
                    result = mainApp.gaia_inst.req_ivit_sat(q,r)
                    if not result == c.POSSIBLE:
                        mainApp.error_popup(result)

    def my_touch_up(self, touch):
        x, y = touch
        if self.ids['MapLayout'].collide_point(x, y):
            radius = self.ids['MapLayout'].size[0] / 30.5
            x, y = self.ids['MapLayout'].to_local(x, y, relative=True)
            # calculate the offset s.t. mid hex from mid-(left-mid) tile is (0,0)
            x -= 11.5 * radius
            y -= 14 * math.sqrt(3) / 2 * radius
            q, r = maptools.pixel_to_hex(x, y, radius)
            if not maptools.get_sector(q,r) == c.OUT_OF_MAP:
                    self.try_building(q, r)

    def draw_map(self):
        Clock.schedule_once(
            functools.partial(
                self.clock_draw_map,
                mainApp.gaia_inst.sector_pos,
                mainApp.gaia_inst.sector_rot,
            )
        )

    def clock_draw_map(self, sector_pos, sector_rot, *largs):
        for i in range(0, 10):
            sector_img = self.ids['MapLayout'].children[(i + 1)] # children 0 is TempSatsLayout
            sector_img.source = f'{c.ASSETS_PATH}/sectors/{sector_pos[i]}.png'
            sector_img.canvas.before.clear()
            sector_img.canvas.after.clear()
            if sector_rot[i] > 0:
                sector_img.canvas.before.add(PushMatrix())
                sector_img.canvas.before.add(
                    Rotate(angle=(sector_rot[i] * (-60)), origin=sector_img.center)
                )
                sector_img.canvas.after.add(PopMatrix())
            sector_img.canvas.ask_update()
            sector_img.reload()


class ResearchBoardWindow(Screen):
    def __init__(self, **kw):        
        super().__init__(**kw)
        self.is_bound = False
        self.init = True

    def bind_hover(self):
        if not self.is_bound:
            for widget in self.ids['research_board'].children:
                if isinstance(widget, HoverButton):
                    widget.do_bind()
            self.is_bound = True

    def unbind_hover(self):
        if self.is_bound:
            for widget in self.ids['research_board'].children:
                if isinstance(widget, HoverButton):
                    widget.do_unbind()
            self.is_bound = False

    def my_touch_up(self, touch):
        _x, _y = touch

    def action(self, action_type, *args):
        result = mainApp.gaia_inst.req_action(action_type)
        self.update_resources()
        if result == c.POSSIBLE:
            return
        else:
            mainApp.error_popup(result)

    def choose_lvlup(self, track, *args):
        result = mainApp.gaia_inst.req_level_up(track)
        if not (result == c.POSSIBLE or result ==c.POSSIBLE_TURN_MARKER_GRAY):
            if result is not None:
                mainApp.your_turn_popup(result)
            

    def choose_tech(self, tile, *args):
        result = mainApp.gaia_inst.req_tech(tile)
        if not result == c.POSSIBLE:
            if result == c.NEED_CHOOSE_COVER:
                mainApp.switch_screen('board')
            mainApp.your_turn_popup(result)


    def update_resources(self):
        Clock.schedule_once(self.clock_update_resources)

    def clock_update_resources(self, *largs):
        if self.init:
            self.ids[
                'fin_1'
            ].source = f'{c.ASSETS_PATH}/goals/{mainApp.gaia_inst.end_goals[1]}'
            self.ids['fin_1'].reload()
            self.ids[
                'fin_2'
            ].source = f'{c.ASSETS_PATH}/goals/{mainApp.gaia_inst.end_goals[0]}'
            self.ids['fin_2'].reload()
            self.ids['tf_fedm'].source = f'{c.ASSETS_PATH}/federations/{mainApp.gaia_inst.tf_fedm}.png'
            self.ids['tf_fedm'].reload()
            # technologies
            for i in range(9):
                tech_img = Image(source=f'{c.ASSETS_PATH}/tech/{mainApp.gaia_inst.tech[i]}')
                tech_img.size_hint = (259 / 1579, 194 / 1687)
                y = 252
                if i < 6:
                    x = 8 + i * 258
                    y = 478
                elif i == 6:
                    x = 111
                elif i == 7:
                    x = 623
                elif i == 8:
                    x = 1117
                tech_img.pos_hint = {'x': x / 1579, 'y': y / 1687}
                self.ids['research_board'].add_widget(tech_img)
            self.init = False
        # cover used p and q actions
        self.ids['pub2knw3_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2trf2_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2ore_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2gld_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2knw2_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2trf1_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['pub2pws_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['qic2tec_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['qic2fed_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        self.ids['qic2vps_oct'].source = f'{c.ASSETS_PATH}/empty.png'
        if len(mainApp.gaia_inst.used_p_and_q):
            if c.PUB_2_KNW_3 in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2knw3_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_TRF_2 in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2trf2_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_ORE in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2ore_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_GLD in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2gld_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_KNW_2 in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2knw2_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_TRF_1 in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2trf1_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.PUB_2_PWS in mainApp.gaia_inst.used_p_and_q:
                self.ids['pub2pws_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.QIC_2_TEC in mainApp.gaia_inst.used_p_and_q:
                self.ids['qic2tec_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.QIC_2_FED in mainApp.gaia_inst.used_p_and_q:
                self.ids['qic2fed_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
            if c.QIC_2_VPS in mainApp.gaia_inst.used_p_and_q:
                self.ids['qic2vps_oct'].source = f'{c.ASSETS_PATH}/octagon.png'
        self.ids['pub2knw3_oct'].reload()
        self.ids['pub2trf2_oct'].reload()
        self.ids['pub2ore_oct'].reload()
        self.ids['pub2gld_oct'].reload()
        self.ids['pub2knw2_oct'].reload()
        self.ids['pub2trf1_oct'].reload()
        self.ids['pub2pws_oct'].reload()
        self.ids['qic2tec_oct'].reload()
        self.ids['qic2fed_oct'].reload()
        self.ids['qic2vps_oct'].reload()

        self.ids['research_markers'].clear_widgets()
        offset_x = 0
        offset_y = 41
        vcp = []
        for p in mainApp.gaia_inst.players:
            for i in range(6):
                m_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/player_token.png')
                m_img.size_hint = (69 / 1516, 83 / 955)
                y = offset_y
                lvl = p.research_branches[i]
                if lvl < 3:
                    y += lvl * 133
                elif lvl < 5:
                    y += 443 + (lvl - 3) * 133
                else:
                    y += 839
                m_img.pos_hint = {'x': (offset_x + i * 256) / 1516, 'y': y / 955}
                self.ids['research_markers'].add_widget(m_img)
            if offset_y and offset_x:
                offset_y = 0
            offset_x += 40
            # add to vcp list
            vcp.append((p.vcp, p.name))
        vcp.sort(reverse=True)
        self.ids['adv_layout'].clear_widgets()
        for i in range(6):
            y = 1393
            x = 60 + i * 257
            adv = mainApp.gaia_inst.adv_tech[i]
            if adv in mainApp.gaia_inst.avail_adv:
                adv_img = Image(source=f'{c.ASSETS_PATH}/tech/{adv}')
                adv_img.size_hint = (203 / 1579, 162 / 1687)
                adv_img.allow_stretch = True
                adv_img.pos_hint = {'x': x / 1579, 'y': y / 1687}
                self.ids['adv_layout'].add_widget(adv_img)
        self.ids['vcp_score'].clear_widgets()
        for p_score, p_name in vcp:
            txt = f'  [b]{p_score}[/b]  {p_name}'
            if len(txt) > 32:
                txt = txt[0:29]
                txt += '...'
            if p_score < 100:
                txt = ' ' + txt
            vcp_label = Label(text=txt, halign='left', valign = 'middle')
            vcp_label.size_hint = (None, None)
            vcp_label.size = (320, 40)
            vcp_label.text_size = (320, 40)
            vcp_label.font_size = 20
            vcp_label.markup = True
            self.ids['vcp_score'].add_widget(vcp_label)

        for i in range(1, mainApp.gaia_inst.round):            
            self.ids[f'round_{i}'].source = f'{c.ASSETS_PATH}/goals/RNDdone.png'
            self.ids[f'round_{i}'].reload()
        if mainApp.gaia_inst.round < 7:
            for i in range(mainApp.gaia_inst.round, 7):
                if i < 1:
                    continue
                self.ids[
                    f'round_{i}'
                ].source = f'{c.ASSETS_PATH}/goals/{mainApp.gaia_inst.round_goals[i - 1]}'
                self.ids[f'round_{i}'].reload()
        # update progress for fin goals
        self.ids['fin_score_layout'].clear_widgets()
        for i in range(2):
            f_goal = mainApp.gaia_inst.end_goals[i]
            for p in mainApp.gaia_inst.players:
                n = 0
                n = p.get_goal_score(mainApp.gaia_inst.gaia_map, f_goal)
                if n < 11:
                    offset_x = 368
                    if n > 0:
                        offset_x = 462 + (n - 1) * 76
                    offset_y = 404 if i else 773
                    offset_y += p.pos * 74
                    sat_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/{c.SATELLITE}')
                    sat_img.pos_hint = {'x': offset_x / 2140, 'y': offset_y / 2130}
                    sat_img.size_hint = (84 / 2140, 84 / 2130)
                    sat_img.allow_stretch = True
                    self.ids['fin_score_layout'].add_widget(sat_img)
                else:
                    offset_x = 368
                    if (n - 10) > 0:
                        offset_x = 462 + (n - 11) * 76
                    offset_y = 404 if i else 773
                    offset_y += p.pos * 74
                    sat_img = Image(source=f'{c.ASSETS_PATH}/colors/{p.color}/{c.SATELLITE}')
                    sat_img.pos_hint = {'x': offset_x / 2140, 'y': offset_y / 2130}
                    sat_img.size_hint = (84 / 2140, 84 / 2130)
                    sat_img.allow_stretch = True
                    self.ids['fin_score_layout'].add_widget(sat_img)
                    sat_img_2 = Image(
                        source=f'{c.ASSETS_PATH}/colors/{p.color}/{c.SATELLITE}'
                    )
                    sat_img_2.pos_hint = {'x': 1146 / 2140, 'y': offset_y / 2130}
                    sat_img_2.size_hint = (84 / 2140, 84 / 2130)
                    sat_img_2.allow_stretch = True
                    self.ids['fin_score_layout'].add_widget(sat_img_2)
        if not mainApp.gaia_inst.lvl_5_free[0]:
            self.ids['tf_fedm'].source = f'{c.ASSETS_PATH}/empty.png'
            self.ids['tf_fedm'].reload()

    def clock_update_pat(self, label_text, *largs):
        self.ids['pat_label'].text = label_text

    def show_final_score(self):
        Clock.schedule_once(self.clock_show_final_score)
        mainApp.switch_screen('research_board')

    def clock_show_final_score(self, *largs):
        vcp = []
        for p in mainApp.gaia_inst.players:            
            vcp.append((p.vcp, p.name))
        vcp.sort(reverse=True)
        self.ids['vcp_score'].clear_widgets()
        for p in vcp:
            txt = f'  [b]{p[0]}[/b]  {p[1]}'
            if len(txt) > 32:
                txt = txt[0:29]
                txt += '...'
            if p[0] < 100:
                txt = ' ' + txt
            if vcp.index(p) == 0:
                txt += '[b] HAT GEWONNEN![/b]'
            vcp_label = Label(text=txt, halign='left')
            vcp_label.halign = 'left'
            vcp_label.valign = 'middle'
            vcp_label.size_hint = (None, None)
            vcp_label.size = (320, 40)
            vcp_label.text_size = (320, 40)
            vcp_label.font_size = 20
            vcp_label.markup = True
            self.ids['vcp_score'].add_widget(vcp_label)
        # SHOW END DETAILS
        self.ids['end_layout'].size_hint=(1, (1040/2130))
        score_details = GridLayout(
            cols=6, 
            pos_hint={'center_x':0.5, 'y':0},
            size_hint = (None, None),
            size = (450, ((mainApp.gaia_inst.num_players + 1)*50)),
            col_default_width=40,
            cols_minimum={0:150},
            row_default_height=40,
            spacing=5,
            row_force_default=True
            )
        # row 0 contains col names
        score_details.add_widget(Label(text='Endwertung:', bold=True))
        score_details.add_widget(ToolTipImage(tooltip='In den Runden erzielte Punkte', source=f'{c.ASSETS_PATH}/fin_details/ingame.png'))
        score_details.add_widget(ToolTipImage(tooltip='Punkte duch Ressourcen', source=f'{c.ASSETS_PATH}/fin_details/acc_res.png'))
        score_details.add_widget(ToolTipImage(tooltip='Punkte durch Forschung', source=f'{c.ASSETS_PATH}/fin_details/acc_lvl.png'))
        score_details.add_widget(ToolTipImage(tooltip='Punkte für obere Endwertung', source=f'{c.ASSETS_PATH}/fin_details/{mainApp.gaia_inst.end_goals[0]}'))
        score_details.add_widget(ToolTipImage(tooltip='Punkte für untere Endwertung', source=f'{c.ASSETS_PATH}/fin_details/{mainApp.gaia_inst.end_goals[1]}'))
        for p in mainApp.gaia_inst.players:
            name = p.name
            if len(name) > 32:
                name = name[0:29]
                name += '...'
            score_details.add_widget(Label(text=name))
            score_details.add_widget(Label(text=str(p.end_details['ingame'])))
            score_details.add_widget(Label(text=str(p.end_details['acc_res'])))
            score_details.add_widget(Label(text=str(p.end_details['acc_lvl'])))
            score_details.add_widget(Label(text=str(p.end_details[mainApp.gaia_inst.end_goals[0]])))
            score_details.add_widget(Label(text=str(p.end_details[mainApp.gaia_inst.end_goals[1]])))
        self.ids['end_layout'].add_widget(score_details)
        tooltip = Label()
        tooltip.size_hint = (None, None)
        self.ids['end_layout'].add_widget(tooltip)
        self.ids['tooltip'] = tooltip._proxy_ref


class OthersWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.zoom_player = None
        self.zoom_background = RelativeLayout()
        self.zoom_background.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.zoom_background.size_hint = (0.8,0.8)
        self.is_bound = False

    def bind_hover(self):
        if not self.is_bound:
            for board in self.ids['other_boards'].children:
                board.ids['finish_button'].do_bind()
                p_board = board.ids['board_grid'].children[0]
                for widget in p_board.ids['board_layout'].children:
                    if isinstance(widget, TranspImage) or isinstance(TranspLayout):
                        widget.do_bind()
            self.is_bound = True  


    def unbind_hover(self):
        if self.is_bound:
            for board in self.ids['other_boards'].children:
                board.ids['finish_button'].do_unbind()
                p_board = board.ids['board_grid'].children[0]
                for widget in p_board.ids['board_layout'].children:
                    if isinstance(widget, TranspImage) or isinstance(TranspLayout):
                        widget.do_unbind()
            self.is_bound = False

    def add_player(self, pos, name, faction_value):
        Clock.schedule_once(
            functools.partial(self.clock_add_player, pos, name, faction_value)
        )

    def clock_add_player(self, pos, name, faction_value, *largs):
        player_board = Board()
        player_board.player = pos
        f_board = FACTION_BOARDS[faction_value]()
        f_board.player = pos
        name_lbl = Label(text=name, bold=True, outline_color=(0,0,0,1),outline_width=2,font_size=18)
        name_lbl.size_hint = ((630/3484), (86/2225))
        name_lbl.pos_hint = {'x': (1950 / 3483), 'y': (1454 / 2225)}
        f_board.ids['board_layout'].add_widget(name_lbl)
        player_board.ids['board_grid'].add_widget(f_board)
        self.ids['other_boards'].add_widget(player_board)

    def update_resources(self):
        Clock.schedule_once(self.clock_update_resources)

    def clock_update_resources(self, *largs):
        for player_board in self.ids['other_boards'].children:
            player_board.update_resources()
        if isinstance(self.zoom_player, Board):
            self.zoom_player.update_resources()

    def my_touch_up(self, touch):
        x, y = touch
        if isinstance(self.zoom_player, Board) and self.zoom_player.parent is not None:
            self.ids['others_layout'].remove_widget(self.zoom_background)
            self.zoom_background.remove_widget(self.zoom_player)
            self.zoom_player.pos_hint = {}
            self.ids['other_boards'].add_widget(self.zoom_player)
            self.zoom_player = None
            if self.ids['other_boards'].canvas.has_after:
                self.ids['other_boards'].canvas.after.clear()
            return
        for player_board in self.ids['other_boards'].children:
            if player_board.collide_point(x,y):
                self.zoom_player = player_board                
                self.zoom_player.pos_hint = {'x': 0, 'y': 0}
                self.ids['other_boards'].remove_widget(self.zoom_player)
                self.ids['other_boards'].canvas.after.add(Rectangle(size=self.ids['other_boards'].size, texture=mainApp.galaxy_texture))
                self.ids['others_layout'].add_widget(self.zoom_background)
                self.zoom_background.add_widget(self.zoom_player)
                return


class NetworkWindow(Screen):

    def toggle_popups(self, new_state):
        if new_state == 'down':
            mainApp.less_popups = True
        else:
            mainApp.less_popups = False

    def show_current_popup(self):
        if mainApp.current_popup is not None and not mainApp.current_popup_open:
            # dont show choice popup again
            if not mainApp.current_popup.title in [c.FED_MARKER_POPUP, c.BOO_POPUP]:
                mainApp.current_popup.open()

    def sync_with_server(self):
        self.ids['sync_btn'].text = 'Bitte warten ...'
        self.ids['sync_btn'].disabled = True
        mainApp.gaia_inst.req_sync()
        mainApp.update_resources()
        fed_possible = (mainApp.gaia_inst.players[mainApp.gaia_inst.my_pos].get_fed_possible(mainApp.gaia_inst.gaia_map) == c.POSSIBLE)
        mainApp.update_map(mainApp.gaia_inst.gaia_map,fed_possible)
        self.ids['sync_btn'].text = 'Synchronisieren'
        self.ids['sync_btn'].disabled = False
        
    def request_undo(self):
        self.ids['undo_btn'].text = 'Bitte warten ...'
        self.ids['undo_btn'].disabled = True
        mainApp.gaia_inst.req_undo()
        self.ids['undo_btn'].text = 'Rückgängig'
        self.ids['undo_btn'].disabled = False

    def export_game_state(self):
        mainApp.gaia_inst.export_game_state()

    


class FactionSetupWindow(Screen):
    ''' behavior for this screen is defined mainly in the FactionButton class'''
    def __init__(self, **kw):
        self.is_bound = False
        super().__init__(**kw)

    def bind_hover(self): 
        if not self.is_bound:       
            for btn in self.ids['fac_layout'].children:
                if isinstance(btn, FactionButton):
                    btn.do_bind()
            self.is_bound = True  

    def unbind_hover(self):
        if self.is_bound:
            for btn in self.ids['fac_layout'].children:
                if isinstance(btn, FactionButton):
                    btn.do_unbind()
            self.is_bound = False  


class SetupWindow(Screen):
    def pick_random(self):
        mainApp.gaia_inst.request_new_setup()
        self.enable_button()

    # This method updates the setup window to show the newly drawn choices

    def new_setup(self, round_boosters, round_goals, end_goals):
        self.ids.random_button.disabled = True
        self.ids.continue_button.disabled = False
        grid_rb = self.ids.grid_round_boosters
        grid_rg = self.ids.grid_round_goals
        grid_eg = self.ids.grid_end_goals

        grid_rb.clear_widgets()
        grid_rg.clear_widgets()
        grid_eg.clear_widgets()
        for img_src in round_boosters:
            Clock.schedule_once(
                functools.partial(self.clock_add_img, grid_rb, 'boosters/' + img_src)
            )
        for img_src in round_goals:
            Clock.schedule_once(
                functools.partial(self.clock_add_img, grid_rg, 'goals/' + img_src)
            )
        for img_src in end_goals:
            Clock.schedule_once(
                functools.partial(self.clock_add_img, grid_eg, 'goals/' + img_src)
            )
        self.enable_button()

    def enable_button(self):
        Clock.schedule_once(self.clock_enable_button, 0.2)

    def clock_add_img(self, grid, img_src, *largs):
        grid.add_widget(
            Image(source=f'{c.ASSETS_PATH}/{img_src}', allow_stretch=True, keep_ratio=True)
        )

    def clock_enable_button(self, *largs):
        self.ids.random_button.disabled = False

    def switch_to_faction_setup(self):
        mainApp.switch_screen(
            'faction_setup', transition=screenmanager.SlideTransition(direction='up')
        )
        mainApp.gaia_inst.switch_to_faction_setup()


class MapSetupWindow(Screen):
    touch_start_sector = None

    def get_sector_from_touch(self, x, y):
        radius = self.ids['MapLayout'].size[0] / 30.5
        x, y = self.ids['MapLayout'].to_widget(x, y, relative=True)
        # calculate the offset s.t. mid hex from mid-(left-mid) tile is (0,0)
        x -= 11.5 * radius
        y -= 14 * math.sqrt(3) / 2 * radius
        q, r = maptools.pixel_to_hex(x, y, radius)
        return maptools.get_sector(q, r)

    def my_touch_down(self, touch):
        x, y = touch
        if self.ids['MapLayout'].collide_point(x, y):
            sector = self.get_sector_from_touch(x, y)
            if sector == c.OUT_OF_MAP:
                self.touch_start_sector = sector
            else:
                self.touch_start_sector = sector[2]

    def my_touch_up(self, touch):
        x, y = touch
        if self.ids['MapLayout'].collide_point(x, y):
            sector = self.get_sector_from_touch(x, y)
            if sector == c.OUT_OF_MAP or self.touch_start_sector is None or self.touch_start_sector == c.OUT_OF_MAP:
                return
            if sector[2] == self.touch_start_sector:
                mainApp.gaia_inst.req_rotate(sector[2])
            else:
                # switch sectors
                mainApp.gaia_inst.req_switch_sectors(
                    c.SECTOR_LIST_POS[self.touch_start_sector],
                    c.SECTOR_LIST_POS[sector[2]],
                )
        else:
            x, y = self.ids['top_layout'].to_local(touch[0], touch[1], relative=True)
            if self.ids['new_map'].collide_point(x, y):
                sector_pos = mainApp.gaia_inst.sector_pos
                random.shuffle(sector_pos)
                mainApp.gaia_inst.req_new_map(sector_pos)
            elif self.ids['continue'].collide_point(x, y):
                mainApp.gaia_inst.req_final_map()

    def rotate_sector(self, sector_name):
        Clock.schedule_once(functools.partial(self.clock_rotate_sector, sector_name))

    def clock_rotate_sector(self, sector_name, *largs):
        sector_img = self.ids[sector_name]
        if sector_img.canvas.before.length():
            # the canvas is not empty so it has been rotated before
            angle = sector_img.canvas.before.children[1].angle
        else:
            angle = 0
        sector_img.canvas.before.clear()
        sector_img.canvas.after.clear()
        if angle != -300:
            angle -= 60
            sector_img.canvas.before.add(PushMatrix())
            sector_img.canvas.before.add(Rotate(angle=angle, origin=sector_img.center))
            sector_img.canvas.after.add(PopMatrix())
        sector_img.canvas.ask_update()

    def draw_map(self):
        Clock.schedule_once(
            functools.partial(
                self.clock_draw_map,
                mainApp.gaia_inst.sector_pos,
                mainApp.gaia_inst.sector_rot,
            )
        )

    def clock_draw_map(self, sector_pos, sector_rot, *largs):
        for i in range(0, 10): 
            sector_img = self.ids['MapLayout'].children[i] 
            sector_img.source = f'{c.ASSETS_PATH}/sectors/{sector_pos[i]}.png'
            sector_img.canvas.before.clear()
            sector_img.canvas.after.clear()
            if sector_rot[i] > 0:
                sector_img.canvas.before.add(PushMatrix())
                sector_img.canvas.before.add(
                    Rotate(angle=(sector_rot[i] * (-60)), origin=sector_img.center)
                )
                sector_img.canvas.after.add(PopMatrix())
            sector_img.canvas.ask_update()
            sector_img.reload()

    def switch_to_setup(self):
        mainApp.gaia_inst.req_final_map()
        mainApp.switch_screen(
            'setup', transition=screenmanager.SlideTransition(direction='up')
        )


class WaitingScreen(Screen):
    i = 0
    add = True

    def change_waiting_text(self):
        Clock.schedule_interval(self.clock_change_text, 0.5)

    def clock_change_text(self, *largs):
        self.ids['main_text'].text += '.'
        if self.i == 3:
            self.i = 0
            self.ids['main_text'].text = self.ids['main_text'].text.rstrip('.')
        else:
            self.i += 1

    def add_player(self, player_name):
        Clock.schedule_once(functools.partial(self.clock_add_player, player_name))

    def clock_add_player(self, player_name, *largs):
        self.ids['list_players'].add_widget(
            Label(
                text=player_name,
                size=(200, 30),
                size_hint=(None, None),
                halign='center',
                font_size=18,
            )
        )
        if len(self.ids['list_players'].children) == (mainApp.gaia_inst.num_players):
            mainApp.switch_screen(
                'map_setup',
                transition=screenmanager.SlideTransition(direction='up'),
                delay=2,
            )
            Clock.unschedule(self.clock_change_text)


class LoginScreen(Screen):
    host_check = ObjectProperty(None)
    username = ObjectProperty(None)
    ip = ObjectProperty(None)
    labelX = ObjectProperty(None)
    inputX = ObjectProperty(None)
    i = 0

    def load_config(self):
        Logger.info('loading config')
        if os.path.exists(f'{mainApp.user_data_dir}/{c.CONFIG_PATH}'):
            with open(f'{mainApp.user_data_dir}/{c.CONFIG_PATH}', 'r') as config:
                config_data = config.readlines()            
            widgets = {
                'name': self.username,
                'server_ip': self.server_ip,
            }
            for line in config_data:
                widget, value = line.strip('\n').split(': ')
                widgets[widget].text = value

    def enter_login(self):
        name = str.strip(self.username.text)
        server_ip = str.strip(self.server_ip.text)
        popup_grid = GridLayout(cols=1)
        correct_input = True
        if not name:
            popup_grid.add_widget(Label(text='Dein Name darf nicht leer sein'))
            correct_input = False
        else:
            if '\'' in name or '"' in name or '\n' in name:
                popup_grid.add_widget(
                    Label(
                        text='Dein Name darf keins der folgenden Zeichen enthalten: \' \"'
                    )
                )
                correct_input = False
        if not server_ip:
            popup_grid.add_widget(Label(text='Die Server-IP darf nicht leer sein'))
            correct_input = False
        else:
            if not len(server_ip.split('.')) == 4:
                popup_grid.add_widget(
                    Label(
                        text='Die Server-IP hat nicht das korrekte Format, richtig ist [x].[x].[x].[x]'
                    )
                )
                correct_input = False
            if not all(map(str.isnumeric, server_ip.split('.'))):
                popup_grid.add_widget(
                    Label(text='Die Server-IP darf nur aus Zahlen und Punkten bestehen')
                )
                correct_input = False        

        if correct_input:
            Clock.schedule_once(self.clock_change_text)
            Clock.schedule_interval(self.clock_change_text, 0.5)
            thread = threading.Thread(target=mainApp.gaia_inst.enter_login, args=[name, server_ip])
            thread.start()
        else:
            login_popup = Popup(
                title='Überprüfe deine Eingaben!',
                content=popup_grid,
                size_hint=(None, None),
                size=(500, 200),
            )
            login_popup.open()

    def clock_change_text(self, *largs):
        if not self.ids['btn'].disabled:            
            self.ids['btn'].disabled = True
            self.ids['btn'].text = 'Verbinde mit Server '
        self.ids['btn'].text += '.'
        if self.i == 3:
            self.i = 0
            self.ids['btn'].text = self.ids['btn'].text.rstrip('.')
        else:
            self.i += 1

    def clock_enable_btn(self, *largs):        
        self.ids['btn'].disabled = False
        self.ids['btn'].text = 'Weiter'

    def handle_login(self, result):
        if result == c.ACKNOWLEDGE:
            Clock.unschedule(self.clock_change_text)
            mainApp.root.get_screen('waiting').change_waiting_text()
            Clock.schedule_once(self.clock_handle_login)
        elif isinstance(result, tuple) and len(result) == 2 and result[0] == c.REJOIN:
            Clock.unschedule(self.clock_change_text)
            Clock.schedule_once(self.clock_handle_rejoin)
        else:
            Clock.unschedule(self.clock_change_text)
            Clock.schedule_once(self.clock_enable_btn)

    def clock_handle_login(self, *largs):        
        mainApp.Window.maximize()  
        mainApp.switch_screen(
            'waiting', transition=screenmanager.SlideTransition(direction='up')
        )

    def clock_handle_rejoin(self, *largs):        
        mainApp.Window.maximize()  
        mainApp.switch_screen(
            'map', transition=screenmanager.SlideTransition(direction='up')
        )



class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prev = None
    def screen_changed(self):
        if self.current == 'map':
            Clock.schedule_once(mainApp.redraw_map)
        # unbind and bind hover buttons
        if self.prev in ['board', 'research_board', 'others', 'faction_setup']:
            self.get_screen(self.prev).unbind_hover()
        if self.current in ['board', 'research_board', 'others', 'faction_setup']:
            self.current_screen.bind_hover()
        self.prev = self.current



class YourTurnPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_open(self):
        mainApp.current_popup_open = True

    def on_dismiss(self):
        mainApp.current_popup_open = False


class PipPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_dismiss(self):
        mainApp.pip_popup = None


class GaiaGame(App):
    galaxy_texture = ObjectProperty()

    def __init__(self, gaia_inst, **kwargs):
        super().__init__(**kwargs)
        self.Window = Window
        global mainApp
        mainApp = self
        self.gaia_inst = gaia_inst
        self.colors = [None]
        self.current_popup = None
        self.current_popup_open = False
        self.pip_popup = None
        self.current_boosters = None
        self.fed_marker_choice = None
        self.less_popups = False
        self.icon = f'{c.ASSETS_PATH}/gaia.ico'
        Window.top -= 100
        Window.left -= 100
        Window.size = (1024, 840)
        Window.bind(on_resize=self.on_resize)

    def build(self):
        self.icon = f'{c.ASSETS_PATH}/gaia.ico'
        self.galaxy_texture = Image(
            source=f'{c.ASSETS_PATH}/galaxy_texture.png'
        ).texture
        self.galaxy_texture.wrap = 'repeat'
        self.galaxy_texture.uvsize = (2, 1)
        return Builder.load_file('gaia.kv')

    def on_start(self):
        self.root.get_screen('login').load_config()

    def on_resize(self, *args):
        if self.root.current == 'map_setup' or self.root.current == 'map':
            Clock.schedule_once(self.redraw_map)
        if self.gaia_inst.round > 0:
            self.root.get_screen('board').ids['board'].update_resources()
            self.root.get_screen('others').update_resources()

    def redraw_map(self, *largs):
        if self.root.current == 'map_setup' or self.root.current == 'map':
            for sector_img in (
                self.root.get_screen(self.root.current).ids['MapLayout'].children # children[0] is TempSatsLayout
            ):             
                if isinstance(sector_img, RelativeLayout):
                    continue
                if len(sector_img.canvas.before.children) == 2:
                    angle = sector_img.canvas.before.children[1].angle
                    sector_img.canvas.before.clear()
                    sector_img.canvas.after.clear()
                    sector_img.canvas.before.add(PushMatrix())
                    sector_img.canvas.before.add(
                        Rotate(angle=angle, origin=sector_img.center)
                    )
                    sector_img.canvas.after.add(PopMatrix())
                    sector_img.canvas.ask_update()

    def switch_screen(self, screen, transition=None, direction=None, delay=0):        
        if not self.root.current == screen:
            Clock.schedule_once(
                functools.partial(self.clock_switch_screen, screen, transition, direction),
                delay,
            )

    def clock_switch_screen(self, screen, transition, *largs):
        if transition:
            self.root.transition = transition
        self.root.current = screen
        self.root.transition = screenmanager.NoTransition()

    def add_faction_picked(self, name, faction, myself=False):
        Clock.schedule_once(
            functools.partial(self.clock_add_faction_picked, name, faction, myself)
        )

    def clock_add_faction_picked(self, name, faction_pick, myself, *largs):
        rs = self.root.get_screen('faction_setup')
        rs.ids[faction_pick].text = name
        if myself:
            rs.ids[faction_pick].color = 0, 0.8, 0, 1
        # red
        if faction_pick == c.HADSCH_HALLA or faction_pick == c.DER_SCHWARM:
            rs.ids[c.HADSCH_HALLA].chooseable = False
            rs.ids[c.DER_SCHWARM].chooseable = False
        # blue
        elif faction_pick == c.LANTIDA or faction_pick == c.TERRANER:
            rs.ids[c.TERRANER].chooseable = False
            rs.ids[c.LANTIDA].chooseable = False
        # white
        elif faction_pick == c.NEVLA or faction_pick == c.ITAR:
            rs.ids[c.ITAR].chooseable = False
            rs.ids[c.NEVLA].chooseable = False
        # black
        elif faction_pick == c.MAD_ANDROIDS or faction_pick == c.FIRAKS:
            rs.ids[c.MAD_ANDROIDS].chooseable = False
            rs.ids[c.FIRAKS].chooseable = False
        # yellow
        elif faction_pick == c.GLEEN or faction_pick == c.XENOS:
            rs.ids[c.GLEEN].chooseable = False
            rs.ids[c.XENOS].chooseable = False
        # orange
        elif faction_pick == c.BAL_TAK or faction_pick == c.GEODEN:
            rs.ids[c.BAL_TAK].chooseable = False
            rs.ids[c.GEODEN].chooseable = False
        # brown
        elif faction_pick == c.AMBAS or faction_pick == c.TAKLONS:
            rs.ids[c.AMBAS].chooseable = False
            rs.ids[c.TAKLONS].chooseable = False    

    def save_colors(self, colors):
        self.colors = colors

    def update_resources(self):
        self.root.get_screen('research_board').update_resources()
        self.root.get_screen('board').ids['board'].update_resources()
        self.root.get_screen('others').update_resources()
        self.update_pat_name()

    def update_pat_name(self):
        if -1 < self.gaia_inst.round < 7:
            pat_name = self.gaia_inst.player_names[self.gaia_inst.player_at_turn]
            if len(pat_name) > 32:
                pat_name = pat_name[:29] + '...'
            text = pat_name + ' ist dran'
        else:
            text = ''
        Clock.schedule_once(functools.partial(self.root.get_screen('board').clock_update_pat, text))
        Clock.schedule_once(functools.partial(self.root.get_screen('map').clock_update_pat, text))
        Clock.schedule_once(functools.partial(self.root.get_screen('research_board').clock_update_pat, text))

    def update_map(self, gaia_map, fed_possible):
        self.root.get_screen('map').update_map(gaia_map, fed_possible)

    def set_current_popup(self, new_popup):
        if self.current_popup_open:
            self.current_popup.dismiss()
        self.current_popup = new_popup
        if ((not self.less_popups) or 
            (new_popup.title in[c.ERROR_POPUP,c.FED_MARKER_POPUP, c.BOO_POPUP]) 
        ):
            self.current_popup.open()

    def set_pip_popup(self, new_popup):
        if self.pip_popup:
            self.pip_popup.dismiss()
        if self.current_popup_open:
            self.current_popup.dismiss()
        self.pip_popup = new_popup
        self.pip_popup.open()

    def fed_marker_popup(self, fed_marker_choice):
        self.fed_marker_choice = fed_marker_choice
        Clock.schedule_once(
            functools.partial(self.clock_show_fed_marker_popup, fed_marker_choice)
        )
    
    def hide_fed_marker_choice(self, *args):
        self.fed_m_popup.dismiss()
        Clock.schedule_once(
            functools.partial(self.clock_show_fed_marker_popup, self.fed_marker_choice), 10
        )
    
    def choose_fed_marker(self, fed_marker, *largs):
        result = self.gaia_inst.req_fed_marker_choice(fed_marker)
        if not result == c.POSSIBLE:
            self.error_popup(result)

    def clock_show_fed_marker_popup(self, fed_marker_choice, *largs):
        if self.gaia_inst.choose_fed_marker:
            self.switch_screen('board')
            content_grid = GridLayout(cols=1)
            content_grid.size_hint = (1, 1)
            fed_marker_grid = GridLayout(rows=1)
            fed_marker_grid.size_hint = (1, None)
            fed_marker_grid.height = 125
            fed_marker_grid.row_default_height = 105
            fed_marker_grid.row_force_default = True
            fed_marker_grid.col_default_width = 75
            fed_marker_grid.col_force_default = True
            fed_marker_grid.spacing = 5
            fed_marker_grid.padding = 10
            width = 40
            for fed_m in fed_marker_choice:
                button = Factory.ImageButton()
                button.source = f'{c.ASSETS_PATH}/federations/{fed_m}.png'
                button.action_type = fed_m
                button.size_hint = (1, 1)
                button.bind(
                    on_release=functools.partial(self.choose_fed_marker, button.action_type)
                )
                fed_marker_grid.add_widget(button)
                width += 80
            content_grid.add_widget(fed_marker_grid)
            later_button = Button(text='Ich muss noch überlegen')
            later_button.size_hint = (None, None)
            later_button.size = (210, 40)
            later_button.pos_hint = {'center_x': 0.5}
            later_button.bind(on_release=self.hide_fed_marker_choice)
            content_grid.add_widget(later_button)
            fed_m_popup = Popup(
                title=c.FED_MARKER_POPUP,
                title_size=18,
                content=content_grid,
                auto_dismiss=False,
            )
            fed_m_popup.size_hint = (None, None)
            width = max(width, 200)
            fed_m_popup.size = (width, 230)
            fed_m_popup.overlay_color = [0, 0, 0, 0.2]
            fed_m_popup.pos_hint = {'center_x': 0.5, 'y': 0.05}
            self.fed_m_popup = fed_m_popup
            if self.current_popup_open:
                self.current_popup.dismiss()
            self.fed_m_popup.open()

    def your_turn_popup(self, text='', title='Du bist dran!', delay=0):
        '''this function creates a popup to tell the player that it is his turn.
        text allows for adding of additional information'''
        if text == c.NEED_CHOOSE_TECH:
            self.switch_screen('research_board')
        Clock.schedule_once(
            functools.partial(self.clock_popup, text, title), delay
        )

    def clock_popup(self, content_text, title_text, *largs):
        title_text = title_text if title_text is not None else ''
        content_text = content_text if content_text is not None else ''
        _popup = YourTurnPopup(
            title=title_text,
            title_size=18,
            title_align='center',
            content=Label(text=content_text, markup=True, halign='center'),
            size_hint=(None, None),
            size=(400, 160),
        )
        self.set_current_popup(_popup)

    def passive_income(self, income_value, vcp_after):
        Clock.schedule_once(
            functools.partial(self.clock_passive_income, income_value, vcp_after), 1
        )

    def clock_passive_income(self, income_value, vcp_after,  *largs):
        self.switch_screen('board')
        pip_popup = None
        pi_string = f'Willst du {income_value} Macht gewinnen? \n Danach hättest du noch {vcp_after} Siegpunkte'
        c_grid = GridLayout(rows=1, spacing=20, padding=10)
        yes_button = Button(
            size_hint=(None, None), size=(170, 40), text='Ich brauche die Macht!'
        )
        yes_button.bind(on_release=self.do_passive_income)
        c_grid.add_widget(yes_button)
        no_button = Button(size_hint=(None, None), size=(170, 40), text='Nein Danke!')
        no_button.bind(on_release=self.dont_passive_income)
        c_grid.add_widget(no_button)
        pip_popup = PipPopup(
            title_size=18,
            title_align='center',
            title=pi_string,
            content=c_grid,
            auto_dismiss=False,
            overlay_color=[0, 0, 0, 0],
            size_hint=(None, None),
            size=(400, 140),
            pos_hint={'center_x': 0.5, 'center_y': 0.2},
        )
        self.set_pip_popup(pip_popup)

    def do_passive_income(self, *args):
        self.pip_popup.dismiss()
        self.gaia_inst.do_passive_income()

    def dont_passive_income(self, *args):
        self.pip_popup.dismiss()

    def error_popup(self, error_text=''):
        # if it is another popup will be shown instead
        if not isinstance(error_text, str):
            error_text = 'Fehlercode ist kein String'
        if error_text not in [c.POSSIBLE, c.ACTION_NOT_POSSIBLE, c.SUCCESS]:
            Clock.schedule_once(
                functools.partial(self.clock_popup, error_text, c.ERROR_POPUP), 0
            )
            

    def choose_booster(self, boo, *args):
        self.gaia_inst.choose_booster(boo)        

    def show_booster_choice(self, avail_boosters):
        self.current_boosters = avail_boosters
        Clock.schedule_once(
            functools.partial(self.clock_show_booster_choice, avail_boosters), 0.8
        )

    def hide_booster_choice(self, *args):
        self.current_popup.dismiss()
        Clock.schedule_once(
            functools.partial(self.clock_show_booster_choice, self.current_boosters), 10
        )

    def clock_show_booster_choice(self, avail_boosters, *largs):
        if self.gaia_inst.booster_phase:
            self.switch_screen('board')
            content_grid = GridLayout(cols=1)
            content_grid.size_hint = (1, 1)
            booster_grid = GridLayout(rows=1)
            booster_grid.size_hint = (1, None)
            booster_grid.height = 245
            booster_grid.row_default_height = 225
            booster_grid.row_force_default = True
            booster_grid.col_default_width = 75
            booster_grid.col_force_default = True
            booster_grid.spacing = 5
            booster_grid.padding = 10
            width = 40
            for boo in avail_boosters:
                button = Factory.ImageButton()
                button.source = f'{c.ASSETS_PATH}/boosters/{boo}'
                button.action_type = boo
                button.size_hint = (1, 1)
                button.bind(
                    on_release=functools.partial(self.choose_booster, button.action_type)
                )
                booster_grid.add_widget(button)
                width += 80
            content_grid.add_widget(booster_grid)
            later_button = Button(text='Ich muss noch überlegen')
            later_button.size_hint = (None, None)
            later_button.size = (200, 40)
            later_button.pos_hint = {'center_x': 0.5}
            later_button.bind(on_release=self.hide_booster_choice)
            content_grid.add_widget(later_button)
            boo_popup = Popup(
                title=c.BOO_POPUP,
                title_size=18,
                content=content_grid,
                auto_dismiss=False,
            )
            boo_popup.size_hint = (None, None)
            boo_popup.size = (width, 360)
            boo_popup.overlay_color = [0, 0, 0, 0.2]
            boo_popup.pos_hint = {'right': 1, 'y': 0.05}
            self.set_current_popup(boo_popup)

    def show_itar_gaia_phase_btn(self):
        self.root.get_screen('board').ids['f_board'].show_itar_gaia_phase_btn()

