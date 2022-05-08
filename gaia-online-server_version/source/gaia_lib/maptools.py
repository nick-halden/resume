''' A collection of map related functions for Gaia-Project. '''
import os, sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import math
from gaia_lib import constants


def get_sector(q, r):
    for sector in constants.SECTOR_CENTERS:
        if hex_distance(q, r, sector[0], sector[1]) < 3:
            return sector
    return constants.OUT_OF_MAP


def cube_to_axial(x, y, z):
    return x, y


def axial_to_cube(q, r):
    return q, r, -(r + q)


def cube_round(x, y, z):
    rx, ry, rz = round(x), round(y), round(z)

    if abs(rx - x) > abs(ry - y) and abs(rx - x) > abs(rz - z):
        rx = -ry - rz
    elif abs(ry - y) > abs(rz - z):
        ry = -rx - rz
    else:
        rz = -rx - ry

    return rx, ry, rz


def hex_round(q, r):
    x, y, z = axial_to_cube(q, r)
    x, y, z = cube_round(x, y, z)
    return cube_to_axial(x, y, z)


def pixel_to_hex(x, y, radius):
    ''' Calculates for given coordinates (in pixels) the hexagon they belong to. Output: Axial coordinates. '''
    q = 2 / 3 * x / radius
    r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / radius
    return hex_round(q, r)


def hex_to_pixel(q, r, radius):
    x = radius * 3 / 2 * q - radius + 11.5 * radius
    y = (
        radius * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
        - math.sqrt(3) / 2 * radius
        + 14 * math.sqrt(3) / 2 * radius
    )
    return x, y


def hex_distance(q1, r1, q2, r2):
    ''' Calculate distance of two hexagons. Input: Axial coordinates. '''
    return (abs(q1 - q2) + abs(-q1 - r1 + q2 + r2) + abs(r1 - r2)) / 2


def rotate_around_center(q, r, n=1):
    ''' Rotate point n times 60° clockwise around center (0, 0). '''
    x, y, z = axial_to_cube(q, r)
    new_q, new_r = cube_to_axial(-z, -x, -y)
    return (new_q, new_r) if n == 1 else rotate_around_center(new_q, new_r, n - 1)
