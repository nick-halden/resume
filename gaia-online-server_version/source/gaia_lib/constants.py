#////////////////////////
#GAME
#////////////////////////
# Factions
AMBAS = 'Ambas'
BAL_TAK = 'BalTak'
MAD_ANDROIDS = 'MadAndroids'
ITAR = 'Itar'
NEVLA = 'Nevla'
HADSCH_HALLA = 'HadschHalla'
DER_SCHWARM = 'DerSchwarm'
TERRANER = 'Terraner'
LANTIDA = 'Lantida'
GEODEN = 'Geoden'
FIRAKS = 'Firaks'
TAKLONS = 'Taklons'
GLEEN = 'Gleen'
XENOS = 'Xenos'
# Planet Types / Colors
BLACK = 'black'
BLUE = 'blue'
BROWN = 'brown'
GAIA = 'gaia'
GAIAFORMED = 'gaiaformed'  # gaiaformed former transdim planet
ORANGE = 'orange'
RED = 'red'
TRANSDIM = 'transdim'
TRANSDIM_GFM = 'transdim_gfm'  # Transdim planet with gaiaformer on it.
WHITE = 'white'
YELLOW = 'yellow'
BLACK_PLANET = 'black_planet' # The black planet placed with lvl 5 navigation
EMPTY = ''
# buildings
MINE = 'mine.png'
TRADING_STATION = 'trading_station.png'
LAB = 'lab.png'
ACADEMY = 'academy.png'
LEFT_ACADEMY = 'left academy'
RIGHT_ACADEMY = 'right academy'
PLANETARY_INSTITUTE = 'planetary_institute.png'
GAIAFORMER = 'gaiaformer.png'
SATELLITE = 'satellite.png'
PLAYER_TOKEN = 'player_token.png'
IVIT_SATELLITE = 'ivit_satellite.png'
# resources
GLD = 'gld'
KNW = 'knw'
ORE = 'ore'
QIC = 'qic'

# free actions
PWR_TO_QIC = 'pwr2qic'
PWR_TO_ORE = 'pwr2ore'
PWR_TO_KNW = 'pwr2knw'
PWR_TO_GLD = 'pwr2gld'
ORE_TO_GLD = 'ore2gld'
KNW_TO_GLD = 'knw2gld'
ORE_TO_PST = 'ore2pst'
QIC_TO_ORE = 'qic2ore'
QIC_TO_RNG = 'qic2rng'
MOVE_PWR_3 = 'move3pwr'
ORANGE_QIC = 'orangeqic'
SPECIAL_NEVLA = 'specialnevla'
HH_GLD_TO_QIC = 'hh_gld_to_qic'
HH_GLD_TO_ORE = 'hh_gld_to_ore'
HH_GLD_TO_KNW = 'hh_gld_to_knw'
FIRAKS_PLI = 'firakspli'
DER_SCHWARM_PLI = 'derschwarmpli'
AMBAS_PLI = 'ambaspli'
ITAR_PLI = 'Du kannst dir Technologieren\nfür Machtsteine nehmen'
TERRANER_PLI = 'Mache Freie Aktionen\nin deiner Gaia Phase'
TAKLONS_PLI = 'taklonspli'
TER_TO_QIC = 'ter2qic'
TER_TO_ORE = 'ter2ore'
TER_TO_KNW = 'ter2knw'
TER_TO_GLD = 'ter2gld'
MAD_ANDROIDS_SPECIAL = 'madandroidsspecial'
BAL_TAK_SPECIAL = 'balttakspecial'
# actions on research board
TECH_1 = 'tech1'
TECH_2 = 'tech2'
TECH_3 = 'tech3'
TECH_4 = 'tech4'
TECH_5 = 'tech5'
TECH_6 = 'tech6'
TECH_7 = 'tech7'
TECH_8 = 'tech8'
TECH_9 = 'tech9'
ADV_TECH_1 = 'adv_tech1'
ADV_TECH_2 = 'adv_tech2'
ADV_TECH_3 = 'adv_tech3'
ADV_TECH_4 = 'adv_tech4'
ADV_TECH_5 = 'adv_tech5'
ADV_TECH_6 = 'adv_tech6'
TRACK_1 = 'track1'
TRACK_2 = 'track2'
TRACK_3 = 'track3'
TRACK_4 = 'track4'
TRACK_5 = 'track5'
TRACK_6 = 'track6'
KNW_2_LVLUP = 'knw2lvlup'
QIC_2_VPS = 'qic2vps'
QIC_2_FED = 'qic2fed'
QIC_2_TEC = 'qic2tec'
PUB_2_PWS = 'pub2pws'
PUB_2_TRF_1 = 'pub2trf1'
PUB_2_TRF_2 = 'pub2trf2'
PUB_2_KNW_2 = 'pub2knw2'
PUB_2_KNW_3 = 'pub2knw3'
PUB_2_ORE = 'pub2ore'
PUB_2_GLD = 'pub2gld'


# constants
OUT_OF_MAP = 'out_of_map'
BOTTOM_LEFT_SECTOR = 'bottomleftsector'
MID_LEFT_SECTOR = 'midleftsector'
TOP_LEFT_SECTOR = 'topleftsector'
MID_LEFT_MID_SECTOR = 'midleftmidsector'
BOTTOM_MID_SECTOR = 'bottommidsector'
MID_RIGHT_MID_SECTOR = 'midrightmidsector'
TOP_MID_SECTOR = 'topmidsector'
TOP_RIGHT_SECTOR = 'toprightsector'
MID_RIGHT_SECTOR = 'midrightsector'
BOTTOM_RIGHT_SECTOR = 'bottomrightsector'



SECTOR_1 = {
    (-1, 1): BROWN,
    (-2, 1): YELLOW,
    (1, 0): BLUE,
    (2, -1): TRANSDIM,
    (0, -2): RED,
    (1, -2): ORANGE
}
SECTOR_2 = {
    (1, 0): WHITE,
    (2, -1): YELLOW,
    (1, -2): TRANSDIM,
    (-1, -1): RED,
    (-1, 0): BROWN,
    (-1, 2): ORANGE,
    (0, 2): BLACK
}
SECTOR_3 = {
    (-1, 1): GAIA,
    (1, -1): WHITE,
    (2, -1): BLACK,
    (0, -2): YELLOW,
    (-1, -1): BLUE,
    (0, 2): TRANSDIM
}
SECTOR_4 = {
    (0, 1): RED,
    (0, 2): BLACK,
    (1, -1): BROWN,
    (2, -2): BLUE,
    (-1, 0): ORANGE,
    (-2, 1): WHITE
}
SECTOR_5 = {
    (0, 2): WHITE,
    (-1, 1): GAIA,
    (2, 0): TRANSDIM,
    (2, -1): RED,
    (0, -2): YELLOW,
    (-1, -1): ORANGE
}
SECTOR_6 = {
    (1, 0): BLUE,
    (1, 1): TRANSDIM,
    (0, -1): GAIA,
    (1, -2): TRANSDIM,
    (2, -2): YELLOW,
    (-1, 1): BROWN
}
SECTOR_7 = {
    (1, -1): GAIA,
    (-1, 0): GAIA,
    (0, 1): RED,
    (1, 1): BROWN,
    (0, -2): BLACK,
    (-2, 2): TRANSDIM
}
SECTOR_8 = {
    (0, 1): WHITE,
    (0, 2): BLUE,
    (1, -1): BLACK,
    (2, 0): TRANSDIM,
    (-1, 0): ORANGE,
    (-1, -1): TRANSDIM
}
SECTOR_9 = {
    (-1, 2): ORANGE,
    (-1, 0): BLACK,
    (-2, 0): BROWN,
    (1, -1): GAIA,
    (2, 0): WHITE,
    (1, 1): TRANSDIM
}
SECTOR_10 = {
    (1, 1): TRANSDIM,
    (2, 0): TRANSDIM,
    (1, -1): GAIA,
    (-1, 1): YELLOW,
    (-1, -1): RED,
    (-2, 0): BLUE
}
SECTOR_TILES = [SECTOR_1, SECTOR_2, SECTOR_3, SECTOR_4, SECTOR_5, SECTOR_6, SECTOR_7, SECTOR_8, SECTOR_9, SECTOR_10]
SECTOR_CENTERS = [
    (-3, -2, BOTTOM_LEFT_SECTOR), (-5, 3, MID_LEFT_SECTOR), (-2, 5, TOP_LEFT_SECTOR),
    (0, 0, MID_LEFT_MID_SECTOR), (2, -5, BOTTOM_MID_SECTOR), (5, -3, MID_RIGHT_MID_SECTOR),
    (3, 2, TOP_MID_SECTOR), (8, -1, TOP_RIGHT_SECTOR), (10, -6, MID_RIGHT_SECTOR),
    (7, -8, BOTTOM_RIGHT_SECTOR)
]
SECTOR_LIST_POS = {
    BOTTOM_LEFT_SECTOR: 0,
    BOTTOM_MID_SECTOR: 4,
    BOTTOM_RIGHT_SECTOR: 9,
    MID_LEFT_SECTOR: 1,
    MID_LEFT_MID_SECTOR: 3,
    MID_RIGHT_MID_SECTOR: 5,
    MID_RIGHT_SECTOR: 8,
    TOP_LEFT_SECTOR: 2,
    TOP_MID_SECTOR: 6,
    TOP_RIGHT_SECTOR: 7
}

# view
ERROR_POPUP = 'Das hat nicht geklappt!'
FED_MARKER_POPUP = 'Wähle deinen Allianzmarker:'
BOO_POPUP = 'Wähle deinen Rundenbooster:'
ASSETS_PATH = '../../assets'
ASSETS_PATH_SERVER = '../../assets'
CONFIG_PATH = 'config'

# return values
SUCCESS = 'success'
POSSIBLE_NO_LVL_UP = 'Das Aufsteigen hier war leider nicht möglich'
SUCCESS_TECH = 'succes_tech'
SUCCESS_GFM = 'successfully placed a gaiaformer on transdim planet'
POSSIBLE = 'possible'
NOT_POSSIBLE = 'Das kannst du nicht machen'
POSSIBLE_TURN_MARKER_GRAY = 'turn alliance marker from green to gray'
POSSIBLE_CHOOSE_TECH = 'possible tech'
OUT_OF_RANGE = 'Der Planet ist außerhalb deiner Reichweite'
NOT_ENOUGH_RESOURCES = 'Dir fehlen die nötigen Resourcen'
INIT_NOT_HOME_PLANET = 'Du darfst nur einen Planeten \n deiner Farbe besiedeln'
NO_MORE_FREE_BUILDINGS = 'Du hast kein freies Gebäude'
NOT_OWNED_BY_YOU = 'Dieser Planet gehört dir nicht'
CANT_PLACE_HERE = 'Du kannst das hier nicht platzieren'
NEED_FEEDBACK_TRD = 'need feedback on Trading station upgrade'
NEED_FEEDBACK_AC = 'need feedback on Academy choice'
NEED_FEEDBACK_FED = 'Willst du eine Allianz \n mit diesen Planeten gründen?'
TECH_NOT_AVAILABLE = 'Du kannst dir diese Technologie nicht holen'
NO_MORE_FREE_GAIAFORMERS = 'Du hast keinen freien Gaiaformer mehr'
ALREADY_USED = 'Das wurde schon gemacht'
ALREADY_OWNED = 'Diese Technologie hast du schon'
ALREADY_OWNED_FED = 'Dieser Allianzmarker\n gehört dir schon'
ALREADY_IN_FED = 'Der Planet ist schon Teil\neiner Allianz'
NOT_ENOUGH_POWERSTONES = 'Du hast nicht genug Machtsteine dafür'
BUILD_PLI_FIRST = 'Dafür musst du erst den Regierungssitz bauen'
NEED_CHOOSE_TECH = 'Wähle eine Technologie aus,\n die du dir nehmen willst'
NEED_CHOOSE_TRACK = 'Wähle aus, wo du aufsteigen möchtest'
NEED_CHOOSE_OTHER_TRACK = 'Du musst einen anderen Zweig wählen'
NEED_CHOOSE_COVER = 'Wähle aus, welche Technologie\n du abdecken möchtest'
NEED_BUILD_MINE = 'Du musst eine Mine bauen, \n um den Zug zu beenden'
NEED_CHOOSE_FED_MARKER = 'Wähle einen Allianzmarker aus'
NEED_CHOOSE_FED_BUILD = 'Du musst deine Allianz fertigstellen'
NEED_CHOOSE_SATS = 'Setze die Satelliten für\ndie neue Allianz'
NEED_CHOOSE_ACTION = 'Wähle eine Aktion aus'
NEED_CHOOSE_BOOSTER = 'Wähle deinen Rundenbooster aus'
NEED_CHOOSE_BLACK_PLANET = 'Setze den schwarzen Planeten\nauf ein freies Feld'
ACTION_NOT_POSSIBLE = 'Es wird angezeigt, dass du das nicht machen kannst'
NOT_YOUR_TURN = 'Du bist nicht dran'
FULLY_UPGRADED = 'Du kannst dieses Gebäude nicht mehr ausbauen'
CANCEL_ACTION = 'Die Aktion wurde von dir abgebrochen'
FED_IMPOSSIBLE = 'Du kannst aus diesen Gebäuden\n keine Allianz gründen'
FED_NOT_CONNECTED = 'Die Allianz ist nicht\nzusammenhängend'
NUM_SATS_TOO_HIGH = 'Du musst die Allianz mit\nweniger Satelliten gründen'

# boosters
BOO_GAI = 'BOOgai.png'
BOO_KNW = 'BOOknw.png'
BOO_LAB = 'BOOlab.png'
BOO_MIN = 'BOOmin.png'
BOO_NAV = 'BOOnav.png'
BOO_PIA = 'BOOpia.png'
BOO_PWT = 'BOOpwt.png'
BOO_QIC = 'BOOqic.png'
BOO_TER = 'BOOter.png'
BOO_TRS = 'BOOtrs.png'
# round goals
RND_FED = 'RNDfed.png'
RND_GAI3 = 'RNDgai3.png'
RND_GAI4 = 'RNDgai4.png'
RND_MIN = 'RNDmin.png'
RND_PIA = 'RNDpia.png'
RND_STP = 'RNDstp.png'
RND_TER = 'RNDter.png'
RND_TRS3 = 'RNDtrs3.png'
RND_TRS4 = 'RNDtrs4.png'
# end goals
FIN_BLD = 'FINbld.png'
FIN_FED = 'FINfed.png'
FIN_GAI = 'FINgai.png'
FIN_SAT = 'FINsat.png'
FIN_SEC = 'FINsec.png'
FIN_TYP = 'FINtyp.png'
# technologies
TEC_CRE = 'TECcre.png'
TEC_GAI = 'TECgai.png'
TEC_KNW = 'TECknw.png'
TEC_ORE = 'TECore.png'
TEC_PIA = 'TECpia.png'
TEC_POW = 'TECpow.png'
TEC_QIC = 'TECqic.png'
TEC_TYP = 'TECtyp.png'
TEC_VPS = 'TECvps.png'
# advanced tech
ADV_FEDP = 'ADVfedP.png'
ADV_FEDV = 'ADVfedV.png'
ADV_MINB = 'ADVminB.png'
ADV_MINV = 'ADVminV.png'
ADV_SECO = 'ADVsecO.png'
ADV_SECV = 'ADVsecV.png'
ADV_TRSB = 'ADVtrsB.png'
ADV_TRSV = 'ADVtrsV.png'
ADV_LAB = 'ADVlab.png'
ADV_KNW = 'ADVknw.png'
ADV_ORE = 'ADVore.png'
ADV_QIC = 'ADVqic.png'
ADV_STP = 'ADVstp.png'
ADV_TYP = 'ADVtyp.png'
ADV_GAI = 'ADVgai.png'
ADVANCED_TECH_TILES = [ADV_FEDP, ADV_FEDV, ADV_GAI, ADV_KNW, ADV_LAB, ADV_MINB, ADV_MINV, ADV_ORE, ADV_QIC, ADV_SECO, ADV_SECV, ADV_STP, ADV_TRSB, ADV_TRSV, ADV_TYP]
# federation markers
FED_CRE = 'FEDcre'
FED_GLE = 'FEDgle'
FED_KNW = 'FEDknw'
FED_ORE = 'FEDore'
FED_PWT = 'FEDpwt'
FED_VPS = 'FEDvps'
FED_QIC = 'FEDqic'
FED_MARKERS = [FED_CRE, FED_KNW, FED_ORE, FED_PWT, FED_VPS, FED_QIC]
#////////////////////////
#NETWORK
#////////////////////////

PORT = 6414
PUB_PORT = 6415

REQUEST_TIMEOUT = 2500
REQUEST_RETRIES = 3

# Types of Messages
PLAYER = 'PLYR'
NAME_IN_USE = 'NAME'
PLYR_LIST = 'LIST'
REJOIN = 'JOIN'
CHANGE_MAP = 'CMAP'
ROTATE_SEC = 'ROTS'
NEW_SETUP = 'NSET'
SWITCH_TO_FACTION_SETUP = 'STFS'
FACTION_PICKED = 'FCTN'
PLAYER_AT_TURN = 'PLAT'
BUILD_MINE = 'MINE'
BUILDING_UPGRADE = 'UPGR'
BUILD_EVENT = 'BLDE'
MAP_EVENT  = 'MAPE'
P_AND_Q_EVENT = 'PNQE'
PLAYER_EVENT = 'PLRE'
ADV_EVENT = 'ADVE'
PASSIVE_INCOME = 'PSIC'
BOOSTER_PICK = 'BSTR'
NEW_ROUND = 'NRND'
FREE_ACTION = 'FREE'
TECH_CHOSEN = 'TECH'
ACTION_STARTED = 'ASTR'
ACTION_CANCELED = 'ACNC'
LEVEL_UP = 'LVLU'
BUILD_FED = 'BFED'
FED_MARKER_CHOICE = 'FEDM'
FACTION_SPECIAL = 'FACS'
FINISH_ROUND = 'PASS'
REQ_SYNC = 'SYNC'
REQ_UNDO = 'UNDO'
ACKNOWLEDGE = 'ACK'
DENY = 'DENY'

#////////////////////////
# Server specific
#////////////////////////
BACKLOG_LEN = 12