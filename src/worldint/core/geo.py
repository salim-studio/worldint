"""Geo helpers: haversine, bbox, point-in-polygon, segment distance."""
from __future__ import annotations
import math

R = 6371.0
def hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2-lat1)*p/2)**2 + math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lon2-lon1)*p/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def bbox(lat, lon, r_km):
    d = r_km / R * 180 / math.pi
    return (lat - d, lat + d, lon - d / max(0.2, math.cos(lat*math.pi/180)), lon + d / max(0.2, math.cos(lat*math.pi/180)))

def in_polygon(lat, lon, verts):
    inside = False
    n = len(verts)
    j = n - 1
    for i in range(n):
        yi, xi = verts[i]; yj, xj = verts[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj-xi)*(lat-yi)/(yj-yi+1e-12)+xi):
            inside = not inside
        j = i
    return inside

def in_shape(lat, lon, shape):
    t = shape.get("type", "circle")
    if t == "circle":
        return hav(lat, lon, shape["lat"], shape["lon"]) <= shape["radius_km"]
    if t == "polygon":
        return in_polygon(lat, lon, shape["vertices"])
    if t == "corridor":
        wps = shape["waypoints"]; w = shape["width_km"] / 2
        return min(hav(lat, lon, a, b) for a, b in wps) <= w + 5 or any(
            hav(lat, lon, a, b) < 1 for a, b in wps)
    return False
