from typing import Text
import kivy
from kivy.app import App
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
# This error is only a mistake form lint
from kivy.properties import Property, ObjectProperty, NumericProperty, ReferenceListProperty, ListProperty, BooleanProperty, StringProperty
from kivy.lang import Builder
import kivy.uix.screenmanager as screenmanager


import functools
import os.path
import math
import random
import sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from gaia_lib import maptools
from gaia_lib import constants as c

kivy.require('1.11.1')

class WindowManager(ScreenManager):
    pass

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
        Clock.schedule_once(functools.partial(
            self.clock_add_player, player_name))

    def clock_add_player(self, player_name, *largs):
        self.ids['list_players'].add_widget(Label(text=player_name, size=(
            200, 30), size_hint=(None, None), halign='center', font_size=18))
        if len(self.ids['list_players'].children) == (mainApp.gaia_inst.num_players):
            mainApp.switch_screen('setup', transition=screenmanager.SlideTransition(
                direction='up'), delay=1.5)
            Clock.unschedule(self.clock_change_text)


class LoginScreen(Screen):
    input_players = ObjectProperty(None)
    ip = ObjectProperty(None)

    def load_config(self, *args, **kwargs):
        Logger.info('loading config')
        if os.path.exists('../server_config'):
            with open('../server_config', 'r') as config:
                config_data = config.readlines()
            for line in config_data:
                widget, value = line.strip('\n').split(': ')
                widgets = {
                    'num_players': self.input_players,
                    'ip': self.ip
                }
                widgets[widget].text = value

    def enter_login(self, import_game = False):
        ip = str.strip(self.ip.text)
        player_count = str.strip(self.input_players.text)
        popup_grid = GridLayout(cols=1)
        correct_input = True        
        if not ip:
            popup_grid.add_widget(Label(text='Bitte gib die Server IP ein'))
            correct_input = False
        else:
            if not len(ip.split('.')) == 4:
                popup_grid.add_widget(Label(
                    text='Die IP hat nicht das korrekte Format, richtig ist [x].[x].[x].[x]'))
                correct_input = False
            if not all(map(str.isdigit, ip.split('.'))):
                popup_grid.add_widget(Label(text='Die IP darf nur aus Zahlen und Punkten bestehen'))
                correct_input = False
        if not player_count:
            popup_grid.add_widget(Label(text='Bitte gib die Spieler:innenanzahl ein'))
            correct_input = False
        else:
            if not player_count.isdigit():
                popup_grid.add_widget(Label(text='Die Spieler:innenanzahl muss eine Zahl sein'))
                correct_input = False
            # TODO: Disable 1 player server if testing is done
            if not 0 < int(player_count) < 5: # player count between 2 and 4
                popup_grid.add_widget(Label(text='Die Spieler:innenanzahl muss zwischen 2 und 4 liegen'))
                correct_input = False
        
        if correct_input:
            if import_game:
                self.server_state = (ip, player_count)
                content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
                self._popup = Popup(title='Load Game State from File', content=content,
                                    size_hint=(0.9, 0.9))
                self._popup.open()                
            else:
                mainApp.gaia_inst.enter_login(ip, player_count)
                mainApp.root.get_screen('waiting').change_waiting_text()
                mainApp.root.get_screen('waiting').ids['main_text'].text = 'Warte bis alle Spieler sich eingeloggt haben \n'
                mainApp.switch_screen('waiting', transition=screenmanager.SlideTransition(direction='up'))
        else:
            login_popup = Popup(title='Überprüfe deine Eingaben!',
                                content=popup_grid, size_hint=(None, None), size=(500, 200))
            login_popup.open()
            
    def dismiss_popup(self):
        self._popup.dismiss()

    def load(self, path, filename):
        self.dismiss_popup()
        mainApp.gaia_inst.import_game_state(path, filename, start_server = self.server_state)
        mainApp.switch_screen('game')

class SetupScreen(Screen):
    sector_pos = ObjectProperty(None)
    sector_rot = ObjectProperty(None)
    boo_input = TextInput()
    rnd_input = TextInput()
    end_input = TextInput()
    phase = 0
    def on_enter(self, *args):
        self.update_values()
        return super().on_enter(*args)
    def next_phase(self):
        self.phase += 1
        if(self.phase == 1):
            # Booster and Goals Setup
            self.ids['setup_phase'].text = 'Boosters and Goals'
            s_grid = self.ids['setup_grid']
            s_grid.clear_widgets()
            s_grid.add_widget(Label(text='Boosters'))
            self.boo_input = TextInput(multiline=False, write_tab=False, size_hint_max_x=400) 
            self.boo_input.bind(on_text_validate=self.boo_setup_change)
            s_grid.add_widget(self.boo_input)
            self.ids['boosters'] = self.boo_input._proxy_ref
            s_grid.add_widget(Label(text='Round Goals'))
            self.rnd_input = TextInput(multiline=False, write_tab=False, size_hint_max_x=400)
            self.rnd_input.bind(on_text_validate=self.boo_setup_change)
            s_grid.add_widget(self.rnd_input)
            self.ids['rnd_goals'] = self.rnd_input._proxy_ref
            s_grid.add_widget(Label(text='End Goals'))
            self.end_input = TextInput(multiline=False, write_tab=False, size_hint_max_x=280) 
            self.end_input.bind(on_text_validate=self.boo_setup_change)
            s_grid.add_widget(self.end_input)
            self.ids['end_goals'] = self.end_input._proxy_ref
            
        elif(self.phase == 2):
            # Faction Setup            
            self.ids['setup_phase'].text = 'Factions'
            s_grid = self.ids['setup_grid']
            s_grid.clear_widgets()
            self.ids['top_grid'].remove_widget(self.ids['next_phase_btn'])
            for i in range(mainApp.gaia_inst.num_players):
                s_grid.add_widget(Label(text=mainApp.gaia_inst.server.players[i]))
                fac_pi = Label(text='')
                s_grid.add_widget(fac_pi)
                self.ids[f'fac_p{i}'] = fac_pi._proxy_ref

    def finish_phase(self, **kwargs):
        if(self.phase == 0):
            mainApp.gaia_inst.send_final_map()
            self.next_phase()
        elif(self.phase == 1 and mainApp.gaia_inst.boosters):            
            mainApp.gaia_inst.switch_to_faction_setup()
            self.next_phase()

    def update_values(self, *args, **kwargs):
        if(self.phase == 0):
            # Map Setup
            self.sector_pos.text = ','.join(map(str,mainApp.gaia_inst.sector_pos))
            self.sector_rot.text = ','.join(map(str,mainApp.gaia_inst.sector_rot))
        elif(self.phase == 1):
            # boosters and other values are None if no setup has been picked yet
            if mainApp.gaia_inst.boosters:
                self.boo_input.text = ','.join(mainApp.gaia_inst.boosters)
                self.rnd_input.text = ','.join(mainApp.gaia_inst.round_goals)
                self.end_input.text = ','.join(mainApp.gaia_inst.end_goals)
        elif(self.phase == 2):
            # Faction Setup
            for player in mainApp.gaia_inst.players:
                if player:
                    self.ids[f'fac_p{player.pos}'].text = player.faction_type
                

    def map_setup_change(self, *args, **kwargs):
        new_sector_pos = list(map(int, map(str.strip, self.sector_pos.text.split(','))))
        new_sector_rot = list(map(int, map(str.strip, self.sector_rot.text.split(','))))
        mainApp.gaia_inst.server_change_map(new_sector_pos, new_sector_rot)
        
    def boo_setup_change(self, *args, **kwargs):
        new_boo = list(map(str.strip,self.boo_input.text.split(',')))
        new_rnd = list(map(str.strip,self.rnd_input.text.split(',')))
        new_end = list(map(str.strip,self.end_input.text.split(',')))
        mainApp.gaia_inst.server_change_setup(new_boo, new_rnd, new_end)

class GameScreen(Screen):
    def top_values_changed(self, *args, **kwargs):
        pass

    def dismiss_popup(self):
        self._popup.dismiss()

    def load(self, path, filename):
        self.dismiss_popup()
        mainApp.gaia_inst.import_game_state(path, filename)

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title='Load Game State from File', content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def export_game_state(self):
        mainApp.gaia_inst.export_game_state()

class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

class GaiaServer(App):
    galaxy_texture = ObjectProperty()

    def __init__(self, gaia_inst, **kwargs):
        super().__init__(**kwargs)
        self.Window = Window
        global mainApp
        mainApp = self
        self.gaia_inst = gaia_inst
        Window.top -= 100
        Window.left -= 100
        Window.size = (1024, 840)

    def build(self):
        self.galaxy_texture = Image(
            source=f'{c.ASSETS_PATH_SERVER}/galaxy_texture.png').texture
        self.galaxy_texture.wrap = 'repeat'
        self.galaxy_texture.uvsize = (2, 1)
        return Builder.load_file('gaia_server.kv')

    def on_start(self):
        self.root.get_screen('login').load_config()

    def switch_screen(self, screen, transition=None, direction=None, delay=0):
        Clock.schedule_once(functools.partial(
            self.clock_switch_screen, screen, transition, direction), delay)

    def clock_switch_screen(self, screen, transition, *largs):
        if transition:
            self.root.transition = transition
        self.root.current = screen
        self.root.transition = screenmanager.NoTransition()

    