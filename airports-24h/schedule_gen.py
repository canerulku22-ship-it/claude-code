"""Representative 24-hour schedules for LAX and LGW.

Routes, daily frequencies and block times are modelled on each airport's real
network; individual times, flight numbers and loads are synthetic.
Usage: python3 schedule_gen.py LAX|LGW  -> schedule_<code>.json
"""
import json, math, random, sys
from collections import Counter

H = lambda h, m=0: h * 60 + m
SEATS = {"E175": 76, "E145": 49, "E190": 100, "CRJ": 90, "AT7": 70, "A319": 140, "A320": 178, "A321": 196, "737": 172, "A220": 135, "757": 176,
         "767": 211, "A330": 280, "787": 260, "777": 320, "A350": 310, "A380": 490, "747": 364}
LF = 0.84
ICAO = {"AA": "AAL", "UA": "UAL", "DL": "DAL", "WN": "SWA", "AS": "ASA", "B6": "JBU", "NK": "NKS", "F9": "FFT", "HA": "HAL",
        "AC": "ACA", "WS": "WJA", "AM": "AMX", "Y4": "VOI", "CM": "CMP", "AV": "AVA", "LA": "LAN", "BA": "BAW", "VS": "VIR",
        "AF": "AFR", "KL": "KLM", "LH": "DLH", "LX": "SWR", "TK": "THY", "EK": "UAE", "QR": "QTR", "EY": "ETD", "LY": "ELY",
        "JL": "JAL", "NH": "ANA", "KE": "KAL", "OZ": "AAR", "CI": "CAL", "BR": "EVA", "CX": "CPA", "MU": "CES", "CA": "CCA",
        "CZ": "CSN", "PR": "PAL", "SQ": "SIA", "QF": "QFA", "NZ": "ANZ", "FJ": "FJI", "TN": "THT", "EI": "EIN", "SK": "SAS",
        "IB": "IBE", "U2": "EZY", "W6": "WZZ", "VY": "VLG", "BY": "TOM", "DY": "NOZ", "N0": "NBT", "FI": "ICE", "AT": "RAM",
        "TP": "TAP", "GR": "AUR", "FR": "RYR", "ZG": "TZP", "AI": "AIC", "TS": "TSC", "D8": "NSZ", "LO": "LOT", "A3": "AEE",
        "OS": "AUA", "TU": "TAR", "J2": "AHY", "MS": "MSR", "RO": "ROT", "AY": "FIN", "ZB": "MON",
        "PC": "PGT", "VF": "TKJ", "XQ": "SXS", "LM": "LOG", "SI": "BCI", "LS": "EXS", "FZ": "FDB", "EW": "EWG"}

def R(code, city, lat, lon, dur, freq, prof, al, ac):
    return dict(code=code, city=city, lat=lat, lon=lon, dur=dur, freq=freq, prof=prof, al=al.split(), ac=ac.split())

# --------------------------------------------------------------------------- LAX (local = PST, UTC-8)
LAX = dict(code="LAX", lat=33.9425, lon=-118.4081, target_moves=1440, target_pax=208_000,
  routes=[
    R("SFO", "SAN FRANCISCO", 37.6213, -122.379, H(1, 25), 26, "DOM", "UA UA AS DL AA", "A320 737 A320 737 A321"),
    R("LAS", "LAS VEGAS", 36.084, -115.1537, H(1, 10), 18, "DOM", "WN WN AA DL UA NK", "737 737 A321 A320 737 A320"),
    R("PHX", "PHOENIX", 33.4342, -112.0116, H(1, 25), 14, "DOM", "WN AA AA", "737 A321 A320"),
    R("SJC", "SAN JOSE", 37.3639, -121.9289, H(1, 15), 9, "DOM", "WN AS", "737 E175"),
    R("OAK", "OAKLAND", 37.7126, -122.2197, H(1, 20), 9, "DOM", "WN WN AS", "737 737 E175"),
    R("SMF", "SACRAMENTO", 38.6954, -121.5908, H(1, 25), 9, "DOM", "WN AS UA", "737 E175 737"),
    R("SLC", "SALT LAKE CITY", 40.7899, -111.9791, H(1, 50), 10, "DOM", "DL DL", "A321 737"),
    R("FAT", "FRESNO", 36.7762, -119.7181, H(1, 5), 4, "DOM", "UA AA", "E175"),
    R("SBA", "SANTA BARBARA", 34.4262, -119.8403, H(0, 55), 4, "DOM", "UA AA", "E175"),
    R("RNO", "RENO", 39.4991, -119.7681, H(1, 30), 4, "DOM", "WN AS", "737 E175"),
    R("TUS", "TUCSON", 32.1161, -110.941, H(1, 35), 4, "DOM", "WN AA", "737"),
    R("ABQ", "ALBUQUERQUE", 35.0402, -106.609, H(1, 55), 4, "DOM", "WN AA", "737"),
    R("SEA", "SEATTLE", 47.4502, -122.3088, H(2, 45), 16, "DOM", "AS AS DL UA", "737"),
    R("PDX", "PORTLAND", 45.5898, -122.5951, H(2, 25), 9, "DOM", "AS AS WN", "737"),
    R("DEN", "DENVER", 39.8561, -104.6737, H(2, 30), 16, "DOM", "UA UA WN F9", "737 A320 737 A320"),
    R("DFW", "DALLAS", 32.8998, -97.0403, H(3, 15), 16, "DOM", "AA AA AA", "A321 737 A321"),
    R("IAH", "HOUSTON", 29.9902, -95.3368, H(3, 20), 9, "DOM", "UA UA", "737"),
    R("AUS", "AUSTIN", 30.1975, -97.6664, H(3, 10), 8, "DOM", "AA WN DL", "A321 737 737"),
    R("MSP", "MINNEAPOLIS", 44.8848, -93.2223, H(3, 40), 7, "DOME", "DL DL", "A321"),
    R("MCI", "KANSAS CITY", 39.2976, -94.7139, H(3, 15), 4, "DOM", "WN AA", "737"),
    R("STL", "ST. LOUIS", 38.7487, -90.37, H(3, 35), 4, "DOM", "WN AA", "737"),
    R("MSY", "NEW ORLEANS", 29.9934, -90.258, H(3, 50), 4, "DOM", "WN DL", "737"),
    R("BNA", "NASHVILLE", 36.1263, -86.6774, H(3, 55), 6, "DOME", "AA WN DL", "A321 737 737"),
    R("YVR", "VANCOUVER", 49.1967, -123.1815, H(2, 55), 6, "DOM", "AC WS AS", "A320 737 737"),
    R("YYC", "CALGARY", 51.1215, -114.0076, H(2, 50), 3, "DOM", "WS AC", "737 A320"),
    R("SJD", "LOS CABOS", 23.1518, -109.721, H(2, 25), 6, "LAT", "AS AA DL", "737"),
    R("PVR", "PUERTO VALLARTA", 20.68, -105.254, H(2, 55), 4, "LAT", "AS DL", "737"),
    R("GDL", "GUADALAJARA", 20.5218, -103.3112, H(3, 25), 7, "LAT", "Y4 AM", "A320 737"),
    R("MEX", "MEXICO CITY", 19.4361, -99.0719, H(3, 50), 9, "LAT", "AM AM Y4 DL", "737"),
    R("JFK", "NEW YORK JFK", 40.6413, -73.7781, H(5, 25), 22, "DOME", "AA AA DL DL B6 B6 UA", "A321 A321 A321 767 A321 A321 757"),
    R("EWR", "NEWARK", 40.6895, -74.1745, H(5, 20), 9, "DOME", "UA UA AS", "737 757 737"),
    R("BOS", "BOSTON", 42.3656, -71.0096, H(5, 35), 10, "DOME", "AA DL B6 AS UA", "A321 A321 A321 737 737"),
    R("ORD", "CHICAGO", 41.9742, -87.9073, H(4, 15), 18, "DOME", "AA UA UA AA", "A321 737 787 A321"),
    R("ATL", "ATLANTA", 33.6407, -84.4277, H(4, 25), 14, "DOME", "DL DL DL", "A321 757 767"),
    R("MIA", "MIAMI", 25.7959, -80.287, H(5, 5), 9, "DOME", "AA AA", "A321"),
    R("MCO", "ORLANDO", 28.4312, -81.3081, H(4, 50), 8, "DOME", "DL WN UA NK", "A321 737 737 A320"),
    R("IAD", "WASHINGTON", 38.9531, -77.4565, H(4, 55), 7, "DOME", "UA UA AA", "737"),
    R("DTW", "DETROIT", 42.2162, -83.3554, H(4, 25), 6, "DOME", "DL DL NK", "A321 737 A320"),
    R("PHL", "PHILADELPHIA", 39.8744, -75.2424, H(5, 5), 6, "DOME", "AA AA", "A321"),
    R("CLT", "CHARLOTTE", 35.214, -80.9431, H(4, 40), 8, "DOME", "AA AA", "A321"),
    R("YYZ", "TORONTO", 43.6777, -79.6248, H(4, 50), 6, "DOME", "AC AC WS", "A321 787 737"),
    R("HNL", "HONOLULU", 21.3187, -157.9225, H(5, 50), 10, "HI", "HA HA AA UA DL", "A330 A321 A321 757 A321"),
    R("OGG", "MAUI", 20.8986, -156.4305, H(5, 45), 6, "HI", "HA AA UA AS", "A321 A321 757 737"),
    R("KOA", "KONA", 19.7388, -156.0456, H(5, 40), 3, "HI", "HA UA", "A321 757"),
    R("CUN", "CANCUN", 21.0365, -86.8771, H(4, 40), 6, "LAT", "AA DL AS UA", "737"),
    R("GUA", "GUATEMALA CITY", 14.5833, -90.5275, H(5, 5), 3, "LAT", "AV DL", "A320 737"),
    R("SAL", "SAN SALVADOR", 13.4409, -89.0557, H(5, 15), 4, "LAT", "AV", "A320"),
    R("SJO", "SAN JOSE CR", 9.9939, -84.2088, H(5, 45), 2, "LAT", "AV DL", "A320 737"),
    R("PTY", "PANAMA CITY", 9.0714, -79.3835, H(6, 20), 2, "LAT", "CM", "737"),
    R("BOG", "BOGOTA", 4.7016, -74.1469, H(7, 15), 1, "LAT", "AV", "787"),
    R("LIM", "LIMA", -12.0219, -77.1143, H(8, 20), 2, "LAT", "LA AA", "787"),
    R("PPT", "TAHITI", -17.5537, -149.6066, H(8, 30), 1, "OCE", "TN", "787"),
    R("LHR", "LONDON", 51.47, -0.4543, H(10, 35), 8, "EUR", "BA BA VS AA UA", "A380 777 A350 777 787"),
    R("CDG", "PARIS", 49.0097, 2.5479, H(11, 0), 3, "EUR", "AF AF DL", "777 A350 A330"),
    R("FRA", "FRANKFURT", 50.0333, 8.5706, H(11, 10), 2, "EUR", "LH", "747"),
    R("MUC", "MUNICH", 48.3538, 11.7861, H(11, 30), 1, "EUR", "LH", "A350"),
    R("AMS", "AMSTERDAM", 52.3086, 4.7639, H(10, 40), 2, "EUR", "KL DL", "787 A330"),
    R("ZRH", "ZURICH", 47.4647, 8.5492, H(11, 25), 1, "EUR", "LX", "777"),
    R("IST", "ISTANBUL", 41.2753, 28.7519, H(13, 20), 1, "EUR", "TK", "777"),
    R("DUB", "DUBLIN", 53.4213, -6.2701, H(10, 25), 1, "EUR", "EI", "A330"),
    R("MAD", "MADRID", 40.4719, -3.5626, H(11, 20), 1, "EUR", "IB", "A350"),
    R("CPH", "COPENHAGEN", 55.618, 12.6561, H(11, 0), 1, "EUR", "SK", "A350"),
    R("DXB", "DUBAI", 25.2532, 55.3657, H(16, 10), 2, "ME", "EK", "A380"),
    R("DOH", "DOHA", 25.2731, 51.6081, H(16, 0), 1, "ME", "QR", "A350"),
    R("AUH", "ABU DHABI", 24.433, 54.6511, H(16, 0), 1, "ME", "EY", "787"),
    R("TLV", "TEL AVIV", 32.0055, 34.8854, H(15, 0), 1, "ME", "LY", "787"),
    R("HND", "TOKYO", 35.5494, 139.7798, H(11, 50), 5, "ASIA", "NH JL AA DL UA", "777 777 777 A350 787"),
    R("NRT", "TOKYO NARITA", 35.772, 140.3929, H(11, 40), 2, "ASIA", "ZG JL", "787"),
    R("ICN", "SEOUL", 37.4602, 126.4407, H(13, 10), 4, "ASIA", "KE KE OZ DL", "A380 777 A350 A350"),
    R("TPE", "TAIPEI", 25.0797, 121.2342, H(14, 0), 4, "ASIA", "BR BR CI CI", "777 787 A350 777"),
    R("HKG", "HONG KONG", 22.308, 113.9185, H(15, 20), 3, "ASIA", "CX CX", "777 A350"),
    R("PVG", "SHANGHAI", 31.1443, 121.8083, H(13, 40), 2, "ASIA", "MU DL", "777 A350"),
    R("PEK", "BEIJING", 40.0799, 116.6031, H(12, 50), 1, "ASIA", "CA", "777"),
    R("CAN", "GUANGZHOU", 23.3924, 113.2988, H(14, 30), 1, "ASIA", "CZ", "787"),
    R("MNL", "MANILA", 14.5086, 121.0198, H(14, 50), 2, "ASIA", "PR", "777"),
    R("SIN", "SINGAPORE", 1.3644, 103.9915, H(17, 30), 1, "ASIA", "SQ", "A350"),
    R("SYD", "SYDNEY", -33.9399, 151.1753, H(15, 0), 4, "OCE", "QF QF UA DL", "A380 787 787 A350"),
    R("MEL", "MELBOURNE", -37.669, 144.841, H(15, 45), 2, "OCE", "QF UA", "787"),
    R("BNE", "BRISBANE", -27.3842, 153.1175, H(13, 50), 2, "OCE", "QF DL", "787 A350"),
    R("AKL", "AUCKLAND", -37.0082, 174.785, H(12, 50), 2, "OCE", "NZ AA", "787"),
    R("NAN", "NADI", -17.7554, 177.4434, H(11, 0), 1, "OCE", "FJ", "A350"),
  ],
  prof={  # (departure weights by local hour, arrival weights)
    "DOM": ({6: 1.6, 7: 1.6, 8: 1.3, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 0.9, 20: 0.7, 21: 0.6, 22: 0.4, 23: 0.2},
            {7: 0.6, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 0.9, 23: 0.7, 0: 0.3}),
    "DOME": ({6: 1.5, 7: 1.5, 8: 1.3, 9: 1.0, 10: 0.8, 11: 0.8, 12: 0.8, 13: 0.8, 14: 0.7, 15: 0.6, 16: 0.5, 17: 0.4, 21: 0.9, 22: 1.3, 23: 1.0},
             {9: 0.5, 10: 0.9, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 0.9, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 0.9, 0: 0.5}),
    "HI": ({7: 0.6, 8: 1.0, 9: 1.0, 10: 0.8, 11: 0.6, 12: 0.5, 13: 0.5, 14: 0.5, 15: 0.6, 16: 0.7, 17: 0.7, 18: 0.5},
           {5: 0.6, 6: 0.6, 13: 0.4, 14: 0.6, 15: 0.6, 16: 0.6, 17: 0.7, 18: 0.7, 19: 0.6, 20: 0.6, 21: 0.5, 22: 0.5}),
    "LAT": ({0: 0.5, 1: 0.3, 7: 0.8, 8: 0.8, 9: 0.6, 10: 0.7, 11: 0.6, 12: 0.6, 13: 0.6, 14: 0.5, 22: 0.4, 23: 0.6},
            {11: 0.5, 12: 0.7, 13: 0.8, 14: 0.8, 15: 0.8, 16: 0.8, 17: 0.7, 18: 0.6, 19: 0.6, 20: 0.5, 21: 0.4, 22: 0.4}),
    "EUR": ({14: 0.6, 15: 0.9, 16: 1.0, 17: 1.0, 18: 0.9, 19: 0.8, 20: 0.5, 21: 0.3}, {11: 0.4, 12: 0.8, 13: 1.0, 14: 1.0, 15: 1.0, 16: 0.7, 17: 0.4}),
    "ME": ({15: 0.6, 16: 1.0, 17: 0.8, 20: 0.4, 21: 0.4}, {8: 0.5, 9: 0.8, 10: 0.8, 11: 0.6, 12: 0.4}),
    "ASIA": ({10: 0.6, 11: 0.9, 12: 0.9, 13: 0.8, 14: 0.5, 22: 0.8, 23: 1.0, 0: 0.8, 1: 0.4},
             {6: 0.5, 7: 0.7, 8: 0.8, 9: 0.9, 10: 0.8, 11: 0.6, 16: 0.5, 17: 0.7, 18: 0.7, 19: 0.7, 20: 0.5}),
    "OCE": ({21: 0.6, 22: 1.0, 23: 1.0, 0: 0.4}, {5: 0.4, 6: 0.8, 7: 1.0, 8: 0.8, 9: 0.4}),
  },
  cap=lambda typ, h: (6 if 1 <= h <= 4 else 22 if h in (0, 5) else 68),
  rwy=lambda typ, t, i: ("24R" if i % 2 == 0 else "25L") if typ == "A" else ("24L" if i % 2 == 0 else "25R"),
)

# --------------------------------------------------------------------------- LGW (local = GMT)
LGW = dict(code="LGW", lat=51.1537, lon=-0.1821, target_moves=770, target_pax=112_000,
  routes=[
    R("EDI", "EDINBURGH", 55.95, -3.3725, H(1, 20), 8, "EUL", "U2 U2 BA", "A320 A319 A320"),
    R("GLA", "GLASGOW", 55.8719, -4.4331, H(1, 20), 5, "EUL", "U2", "A320"),
    R("BFS", "BELFAST", 54.6575, -6.2158, H(1, 15), 5, "EUL", "U2", "A320"),
    R("JER", "JERSEY", 49.2079, -2.1955, H(0, 55), 5, "EUL", "U2 BA", "A319 A320"),
    R("GCI", "GUERNSEY", 49.4350, -2.6020, H(0, 50), 5, "EUL", "GR", "AT7"),
    R("INV", "INVERNESS", 57.5425, -4.0475, H(1, 35), 2, "EUL", "U2", "A320"),
    R("IOM", "ISLE OF MAN", 54.0833, -4.6239, H(1, 10), 2, "EUL", "U2", "A319"),
    R("DUB", "DUBLIN", 53.4213, -6.2701, H(1, 15), 8, "EUL", "FR EI FR", "737 A320 737"),
    R("AMS", "AMSTERDAM", 52.3086, 4.7639, H(1, 15), 7, "EUL", "U2 U2 BA", "A320 A319 A320"),
    R("GVA", "GENEVA", 46.2381, 6.109, H(1, 40), 8, "EUL", "U2 U2 BA", "A320 A319 A320"),
    R("BSL", "BASEL", 47.5896, 7.5299, H(1, 35), 3, "EUL", "U2", "A320"),
    R("ZRH", "ZURICH", 47.4647, 8.5492, H(1, 40), 3, "EUL", "U2 BA", "A320"),
    R("LYS", "LYON", 45.7256, 5.0811, H(1, 35), 3, "EUL", "U2", "A319"),
    R("NCE", "NICE", 43.6584, 7.2159, H(1, 55), 6, "EUL", "U2 U2 BA", "A320 A321 A320"),
    R("TLS", "TOULOUSE", 43.6291, 1.3638, H(1, 45), 3, "EUL", "U2", "A320"),
    R("BOD", "BORDEAUX", 44.8283, -0.7156, H(1, 35), 2, "EUL", "U2", "A320"),
    R("CPH", "COPENHAGEN", 55.618, 12.6561, H(1, 50), 4, "EUL", "U2 DY", "A320 737"),
    R("BER", "BERLIN", 52.3667, 13.5033, H(1, 50), 4, "EUL", "U2", "A320"),
    R("HAM", "HAMBURG", 53.6304, 9.9882, H(1, 35), 2, "EUL", "U2", "A320"),
    R("MXP", "MILAN", 45.6306, 8.7231, H(1, 55), 4, "EUL", "U2 U2", "A320 A321"),
    R("PRG", "PRAGUE", 50.1008, 14.26, H(1, 55), 3, "EUL", "U2", "A320"),
    R("BCN", "BARCELONA", 41.2971, 2.0785, H(2, 10), 9, "EUL", "U2 VY BA", "A320 A320 A321"),
    R("MAD", "MADRID", 40.4719, -3.5626, H(2, 20), 4, "EUL", "U2 BA", "A320"),
    R("AGP", "MALAGA", 36.6749, -4.4991, H(2, 50), 7, "EUL", "U2 BA BY", "A320 A320 737"),
    R("ALC", "ALICANTE", 38.2822, -0.5582, H(2, 30), 5, "EUL", "U2 BA", "A320"),
    R("PMI", "PALMA", 39.5517, 2.7388, H(2, 20), 4, "EUL", "U2 BA", "A320"),
    R("FAO", "FARO", 37.0144, -7.9659, H(2, 45), 5, "EUL", "U2 BA", "A320"),
    R("LIS", "LISBON", 38.7813, -9.1359, H(2, 40), 5, "EUL", "U2 TP", "A320 A321"),
    R("OPO", "PORTO", 41.2481, -8.6814, H(2, 15), 3, "EUL", "U2", "A320"),
    R("SVQ", "SEVILLE", 37.418, -5.8931, H(2, 40), 2, "EUL", "U2", "A320"),
    R("VLC", "VALENCIA", 39.4893, -0.4816, H(2, 20), 2, "EUL", "U2", "A320"),
    R("BIO", "BILBAO", 43.3011, -2.9106, H(1, 55), 2, "EUL", "U2", "A320"),
    R("GIB", "GIBRALTAR", 36.1512, -5.3497, H(2, 50), 2, "EUL", "U2 BA", "A320"),
    R("FCO", "ROME", 41.8003, 12.2389, H(2, 35), 5, "EUL", "U2 BA", "A320"),
    R("NAP", "NAPLES", 40.886, 14.2908, H(2, 40), 3, "EUL", "U2", "A320"),
    R("PSA", "PISA", 43.6839, 10.3927, H(2, 10), 3, "EUL", "U2 BA", "A320"),
    R("VCE", "VENICE", 45.5053, 12.3519, H(2, 10), 4, "EUL", "U2 BA", "A320"),
    R("BLQ", "BOLOGNA", 44.5354, 11.2887, H(2, 10), 2, "EUL", "U2", "A320"),
    R("CTA", "CATANIA", 37.4668, 15.0664, H(3, 0), 2, "EUL", "U2", "A320"),
    R("VIE", "VIENNA", 48.1103, 16.5697, H(2, 15), 3, "EUL", "U2", "A320"),
    R("BUD", "BUDAPEST", 47.4369, 19.2556, H(2, 30), 3, "EUL", "U2 W6", "A320 A321"),
    R("KRK", "KRAKOW", 50.0777, 19.7848, H(2, 15), 3, "EUL", "U2 W6", "A320 A321"),
    R("WAW", "WARSAW", 52.1657, 20.9671, H(2, 30), 2, "EUL", "W6", "A321"),
    R("OTP", "BUCHAREST", 44.5711, 26.085, H(3, 15), 3, "EUL", "W6 W6", "A321"),
    R("SOF", "SOFIA", 42.6967, 23.4114, H(3, 0), 2, "EUL", "W6", "A321"),
    R("ATH", "ATHENS", 37.9364, 23.9445, H(3, 40), 3, "EUL", "U2 BA", "A320 A321"),
    R("OSL", "OSLO", 60.1939, 11.1004, H(2, 0), 4, "EUL", "DY U2", "737 A320"),
    R("ARN", "STOCKHOLM", 59.6519, 17.9186, H(2, 25), 3, "EUL", "DY U2", "737 A320"),
    R("KEF", "REYKJAVIK", 63.985, -22.6056, H(3, 0), 2, "EUL", "U2 FI", "A320 737"),
    R("TFS", "TENERIFE", 28.0445, -16.5725, H(4, 20), 6, "EUL", "U2 BA BY", "A321 A320 737"),
    R("ACE", "LANZAROTE", 28.9455, -13.6052, H(4, 0), 5, "EUL", "U2 BY", "A320 737"),
    R("LPA", "GRAN CANARIA", 27.9319, -15.3866, H(4, 15), 4, "EUL", "U2 BA", "A321 A320"),
    R("FUE", "FUERTEVENTURA", 28.4527, -13.8638, H(4, 5), 3, "EUL", "U2 BY", "A320 737"),
    R("FNC", "MADEIRA", 32.6979, -16.7745, H(3, 45), 2, "EUL", "U2", "A320"),
    R("RAK", "MARRAKECH", 31.6069, -8.0363, H(3, 35), 3, "EUL", "U2 U2", "A320"),
    R("AGA", "AGADIR", 30.325, -9.4131, H(3, 50), 2, "EUL", "U2", "A320"),
    R("LCA", "LARNACA", 34.8751, 33.6249, H(4, 30), 2, "EUL", "U2", "A320"),
    R("PFO", "PAPHOS", 34.718, 32.4857, H(4, 30), 2, "EUL", "U2 BY", "A320 737"),
    R("TLV", "TEL AVIV", 32.0055, 34.8854, H(4, 55), 2, "EUL", "U2", "A321"),
    R("HRG", "HURGHADA", 27.1783, 33.7994, H(5, 15), 2, "EUL", "U2 BY", "A320 737"),
    R("IST", "ISTANBUL", 41.2753, 28.7519, H(3, 50), 3, "EUL", "TK TK", "A321 A330"),
    R("DXB", "DUBAI", 25.2532, 55.3657, H(6, 55), 3, "ME", "EK", "A380"),
    R("DOH", "DOHA", 25.2731, 51.6081, H(6, 35), 2, "ME", "QR", "787"),
    R("HKG", "HONG KONG", 22.308, 113.9185, H(12, 15), 1, "ASIA", "CX", "A350"),
    R("PEK", "BEIJING", 40.0799, 116.6031, H(10, 30), 1, "ASIA", "CA", "A330"),
    R("AMD", "AHMEDABAD", 23.0772, 72.6347, H(9, 20), 1, "ASIA", "AI", "787"),
    R("GOI", "GOA", 15.3809, 73.8314, H(10, 0), 1, "ASIA", "AI", "787"),
    R("JFK", "NEW YORK JFK", 40.6413, -73.7781, H(7, 45), 3, "NAM", "B6 N0 DL", "A321 787 767"),
    R("BOS", "BOSTON", 42.3656, -71.0096, H(7, 10), 2, "NAM", "B6 N0", "A321 787"),
    R("MCO", "ORLANDO", 28.4312, -81.3081, H(9, 40), 2, "NAM", "BA N0", "777 787"),
    R("TPA", "TAMPA", 27.9755, -82.5332, H(9, 50), 1, "NAM", "BA", "777"),
    R("LAS", "LAS VEGAS", 36.084, -115.1537, H(10, 50), 1, "NAM", "BA", "777"),
    R("YYZ", "TORONTO", 43.6777, -79.6248, H(7, 45), 2, "NAM", "WS TS", "737 A321"),
    R("CUN", "CANCUN", 21.0365, -86.8771, H(10, 15), 1, "NAM", "BA", "777"),
    R("ANU", "ANTIGUA", 17.1367, -61.7926, H(8, 45), 1, "NAM", "BA", "777"),
    R("BGI", "BARBADOS", 13.0746, -59.4925, H(8, 50), 1, "NAM", "BA", "777"),
    R("UVF", "ST LUCIA", 13.7332, -60.9526, H(9, 0), 1, "NAM", "BA", "777"),
  ],
  prof={
    "EUL": ({6: 2.6, 7: 1.8, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 0.9, 20: 0.7, 21: 0.4, 22: 0.12},
            {7: 0.3, 8: 0.6, 9: 1.0, 10: 1.1, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 0.85, 0: 0.35}),
    "NAM": ({9: 0.6, 10: 0.9, 11: 1.0, 12: 0.9, 13: 0.7, 14: 0.5, 15: 0.4, 16: 0.3, 18: 0.3}, {5: 0.4, 6: 1.0, 7: 1.0, 8: 0.9, 9: 0.6, 10: 0.4, 14: 0.2, 15: 0.3}),
    "ME": ({9: 0.5, 13: 0.6, 14: 0.6, 20: 0.7, 21: 0.8}, {6: 0.6, 7: 0.8, 12: 0.5, 13: 0.6, 19: 0.6, 20: 0.4}),
    "ASIA": ({11: 0.4, 12: 0.4, 18: 0.6, 19: 0.8, 20: 0.8}, {5: 0.8, 6: 0.9, 7: 0.6, 15: 0.3, 16: 0.4}),
  },
  cap=lambda typ, h: (0 if typ == "D" and h < 6 else (3 if typ == "A" and 1 <= h <= 4 else (24 if typ == "A" else 30) if 6 <= h <= 22 else 10)),
  rwy=lambda typ, t, i: "26L",
)

# --------------------------------------------------------------------------- BHX (local = GMT)
BHX = dict(code="BHX", lat=52.4539, lon=-1.748, target_moves=224, target_pax=27_500,
  routes=[
    R("DUB", "DUBLIN", 53.4213, -6.2701, H(1, 5), 6, "EUL", "FR EI FR", "737 AT7 737"),
    R("BHD", "BELFAST", 54.6181, -5.8725, H(1, 5), 4, "EUL", "EI", "AT7"),
    R("EDI", "EDINBURGH", 55.95, -3.3725, H(1, 10), 4, "EUL", "LM", "E145"),
    R("GLA", "GLASGOW", 55.8719, -4.4331, H(1, 10), 3, "EUL", "LM", "E145"),
    R("ABZ", "ABERDEEN", 57.2019, -2.1978, H(1, 20), 2, "EUL", "LM", "E145"),
    R("JER", "JERSEY", 49.2079, -2.1955, H(1, 5), 2, "EUL", "SI", "AT7"),
    R("AMS", "AMSTERDAM", 52.3086, 4.7639, H(1, 10), 5, "EUL", "KL", "E190"),
    R("CDG", "PARIS", 49.0097, 2.5479, H(1, 10), 3, "EUL", "AF", "E190"),
    R("FRA", "FRANKFURT", 50.0333, 8.5706, H(1, 30), 3, "EUL", "LH", "CRJ A320"),
    R("MUC", "MUNICH", 48.3538, 11.7861, H(1, 45), 2, "EUL", "LH", "A320"),
    R("ZRH", "ZURICH", 47.4647, 8.5492, H(1, 40), 2, "EUL", "LX", "A220"),
    R("GVA", "GENEVA", 46.2381, 6.109, H(1, 40), 1, "EUL", "LS", "737"),
    R("BCN", "BARCELONA", 41.2971, 2.0785, H(2, 5), 2, "EUL", "VY FR", "A320 737"),
    R("MAD", "MADRID", 40.4719, -3.5626, H(2, 15), 1, "EUL", "FR", "737"),
    R("AGP", "MALAGA", 36.6749, -4.4991, H(2, 40), 4, "EUL", "LS FR BY", "737 737 737"),
    R("ALC", "ALICANTE", 38.2822, -0.5582, H(2, 25), 4, "EUL", "LS FR BY", "737 737 737"),
    R("FAO", "FARO", 37.0144, -7.9659, H(2, 35), 3, "EUL", "LS FR", "737"),
    R("PMI", "PALMA", 39.5517, 2.7388, H(2, 15), 1, "EUL", "LS", "737"),
    R("TFS", "TENERIFE", 28.0445, -16.5725, H(4, 20), 4, "EUL", "LS BY FR", "737 737 737"),
    R("LPA", "GRAN CANARIA", 27.9319, -15.3866, H(4, 15), 3, "EUL", "LS BY", "737"),
    R("ACE", "LANZAROTE", 28.9455, -13.6052, H(4, 0), 3, "EUL", "LS FR BY", "737"),
    R("FUE", "FUERTEVENTURA", 28.4527, -13.8638, H(4, 5), 2, "EUL", "LS BY", "737"),
    R("FNC", "MADEIRA", 32.6979, -16.7745, H(3, 45), 1, "EUL", "LS", "737"),
    R("RAK", "MARRAKECH", 31.6069, -8.0363, H(3, 25), 1, "EUL", "FR", "737"),
    R("HRG", "HURGHADA", 27.1783, 33.7994, H(5, 15), 1, "EUL", "BY", "737"),
    R("KRK", "KRAKOW", 50.0777, 19.7848, H(2, 20), 2, "EUL", "FR W6", "737 A321"),
    R("KTW", "KATOWICE", 50.4743, 19.08, H(2, 15), 1, "EUL", "W6", "A321"),
    R("WAW", "WARSAW", 52.1657, 20.9671, H(2, 25), 1, "EUL", "W6", "A321"),
    R("OTP", "BUCHAREST", 44.5711, 26.085, H(3, 10), 2, "EUL", "W6", "A321"),
    R("SOF", "SOFIA", 42.6967, 23.4114, H(3, 0), 1, "EUL", "W6", "A321"),
    R("BUD", "BUDAPEST", 47.4369, 19.2556, H(2, 25), 1, "EUL", "FR", "737"),
    R("PRG", "PRAGUE", 50.1008, 14.26, H(1, 55), 1, "EUL", "LS", "737"),
    R("FCO", "ROME", 41.8003, 12.2389, H(2, 40), 1, "EUL", "FR", "737"),
    R("BGY", "MILAN", 45.6739, 9.7042, H(2, 5), 1, "EUL", "FR", "737"),
    R("IST", "ISTANBUL", 41.2753, 28.7519, H(3, 55), 2, "EUL", "TK", "A321"),
    R("SAW", "ISTANBUL SAW", 40.8986, 29.3092, H(3, 55), 1, "EUL", "PC", "A320"),
    R("AYT", "ANTALYA", 36.8987, 30.8005, H(4, 15), 1, "EUL", "LS", "737"),
    R("LCA", "LARNACA", 34.8751, 33.6249, H(4, 35), 1, "EUL", "LS", "737"),
    R("PFO", "PAPHOS", 34.718, 32.4857, H(4, 35), 1, "EUL", "LS", "737"),
    R("DXB", "DUBAI", 25.2532, 55.3657, H(6, 45), 2, "ME", "EK", "777 A380"),
    R("DOH", "DOHA", 25.2731, 51.6081, H(6, 30), 1, "ME", "QR", "787"),
    R("CUN", "CANCUN", 21.0365, -86.8771, H(10, 30), 1, "LH", "BY", "787"),
  ],
  prof={
    "EUL": ({6: 3.0, 7: 1.6, 8: 1.0, 9: 0.9, 10: 0.9, 11: 0.9, 12: 0.9, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 0.8, 20: 0.6, 21: 0.3},
            {8: 0.5, 9: 0.9, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 0.8, 0: 0.3}),
    "ME": ({13: 0.8, 14: 0.6, 21: 0.8}, {6: 0.8, 7: 0.6, 12: 0.8, 13: 0.4}),
    "LH": ({11: 1.0}, {9: 1.0}),
  },
  cap=lambda typ, h: (0 if typ == "D" and h < 6 else (2 if 1 <= h <= 4 else 18)),
  rwy=lambda typ, t, i: "33",
)
# --------------------------------------------------------------------------- ADB (local = TRT, UTC+3)
ADB = dict(code="ADB", lat=38.2924, lon=27.157, target_moves=232, target_pax=30_500,
  routes=[
    R("IST", "ISTANBUL", 41.2753, 28.7519, H(1, 5), 10, "DOMT", "TK TK VF", "A321 737 A320"),
    R("SAW", "ISTANBUL SAW", 40.8986, 29.3092, H(1, 5), 9, "DOMT", "PC PC VF", "A320 A321 737"),
    R("ESB", "ANKARA", 40.1281, 32.9951, H(1, 10), 6, "DOMT", "VF VF PC", "737 A320 A320"),
    R("AYT", "ANTALYA", 36.8987, 30.8005, H(1, 0), 2, "DOMT", "PC VF", "A320 737"),
    R("ADA", "ADANA", 36.9822, 35.2804, H(1, 30), 2, "DOMT", "PC VF", "A320 737"),
    R("TZX", "TRABZON", 40.9951, 39.7897, H(1, 55), 2, "DOMT", "PC VF", "A320 737"),
    R("DIY", "DIYARBAKIR", 37.8939, 40.2010, H(1, 55), 2, "DOMT", "PC VF", "A320 737"),
    R("GZT", "GAZIANTEP", 36.9472, 37.4787, H(1, 45), 2, "DOMT", "PC VF", "A320 737"),
    R("ASR", "KAYSERI", 38.7704, 35.4954, H(1, 30), 1, "DOMT", "VF", "737"),
    R("ERZ", "ERZURUM", 39.9565, 41.1702, H(2, 0), 1, "DOMT", "VF", "737"),
    R("VAN", "VAN", 38.4682, 43.3323, H(2, 15), 1, "DOMT", "PC", "A320"),
    R("SZF", "SAMSUN", 41.2545, 36.5671, H(1, 40), 1, "DOMT", "VF", "737"),
    R("MLX", "MALATYA", 38.4353, 38.0910, H(1, 45), 1, "DOMT", "VF", "737"),
    R("MQM", "MARDIN", 37.2233, 40.6317, H(2, 5), 1, "DOMT", "VF", "737"),
    R("GNY", "SANLIURFA", 37.4457, 38.8956, H(1, 55), 1, "DOMT", "PC", "A320"),
    R("HTY", "HATAY", 36.3628, 36.2822, H(1, 35), 1, "DOMT", "PC", "A320"),
    R("KYA", "KONYA", 37.979, 32.5619, H(1, 15), 1, "DOMT", "VF", "737"),
    R("ECN", "ERCAN", 35.1547, 33.4961, H(1, 35), 2, "DOMT", "PC VF", "A320 737"),
    R("FRA", "FRANKFURT", 50.0333, 8.5706, H(3, 10), 2, "EURT", "XQ LH", "737 A321"),
    R("DUS", "DUSSELDORF", 51.2895, 6.7668, H(3, 20), 2, "EURT", "XQ EW", "737 A320"),
    R("CGN", "COLOGNE", 50.8659, 7.1427, H(3, 15), 1, "EURT", "XQ", "737"),
    R("STR", "STUTTGART", 48.6899, 9.222, H(2, 55), 1, "EURT", "XQ", "737"),
    R("MUC", "MUNICH", 48.3538, 11.7861, H(2, 45), 1, "EURT", "XQ", "737"),
    R("BER", "BERLIN", 52.3667, 13.5033, H(2, 50), 1, "EURT", "XQ", "737"),
    R("HAM", "HAMBURG", 53.6304, 9.9882, H(3, 20), 1, "EURT", "XQ", "737"),
    R("HAJ", "HANOVER", 52.4611, 9.6850, H(3, 10), 1, "EURT", "XQ", "737"),
    R("NUE", "NUREMBERG", 49.4987, 11.0781, H(2, 55), 1, "EURT", "XQ", "737"),
    R("AMS", "AMSTERDAM", 52.3086, 4.7639, H(3, 40), 1, "EURT", "PC", "A320"),
    R("BRU", "BRUSSELS", 50.9014, 4.4844, H(3, 35), 1, "EURT", "PC", "A320"),
    R("VIE", "VIENNA", 48.1103, 16.5697, H(2, 25), 1, "EURT", "PC", "A320"),
    R("ZRH", "ZURICH", 47.4647, 8.5492, H(2, 55), 1, "EURT", "XQ", "737"),
    R("CDG", "PARIS", 49.0097, 2.5479, H(3, 40), 1, "EURT", "PC", "A321"),
    R("STN", "LONDON", 51.885, 0.235, H(4, 0), 1, "EURT", "PC", "A321"),
    R("GYD", "BAKU", 40.4675, 50.0467, H(2, 50), 1, "MET", "J2", "A320"),
    R("DOH", "DOHA", 25.2731, 51.6081, H(3, 50), 1, "MET", "QR", "A320"),
    R("DXB", "DUBAI", 25.2532, 55.3657, H(4, 20), 1, "MET", "FZ", "737"),
  ],
  prof={
    "DOMT": ({6: 1.3, 7: 1.4, 8: 1.2, 9: 1.0, 10: 1.0, 11: 0.9, 12: 0.9, 13: 0.9, 14: 0.9, 15: 1.0, 16: 1.0, 17: 1.1, 18: 1.1, 19: 1.0, 20: 1.0, 21: 0.9, 22: 0.7, 23: 0.5, 0: 0.2},
             {7: 0.5, 8: 1.0, 9: 1.0, 10: 1.0, 11: 0.9, 12: 0.9, 13: 0.9, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 1.0, 0: 0.7, 1: 0.3}),
    "EURT": ({5: 0.7, 6: 1.2, 7: 1.2, 8: 0.9, 9: 0.7, 10: 0.6, 11: 0.5, 12: 0.5, 13: 0.5, 14: 0.5, 15: 0.5, 16: 0.5, 17: 0.4, 18: 0.4, 19: 0.3},
             {11: 0.6, 12: 0.9, 13: 1.0, 14: 1.0, 15: 0.9, 16: 0.9, 17: 0.8, 18: 0.7, 19: 0.7, 20: 0.7, 21: 0.6, 22: 0.5, 23: 0.4, 0: 0.4, 1: 0.3}),
    "MET": ({4: 0.5, 14: 0.5, 15: 0.5}, {3: 0.5, 13: 0.5, 14: 0.5}),
  },
  cap=lambda typ, h: (2 if 2 <= h <= 4 else 16),
  rwy=lambda typ, t, i: "34R" if typ == "A" else "34L",
)

AP = {"LAX": LAX, "LGW": LGW, "BHX": BHX, "ADB": ADB}[sys.argv[1] if len(sys.argv) > 1 else "LAX"]
random.seed(hash(AP["code"]) % 100000 + 20261102)
random.seed({"LAX": 20261102, "LGW": 20261103, "BHX": 20261104, "ADB": 20261105}[AP["code"]])

def cat_of(m): return 0 if m < 120 else 1 if m < 240 else 2 if m < 480 else 3
routes = AP["routes"]
for r in routes: r["cat"] = cat_of(r["dur"])
base = sum(r["freq"] for r in routes) * 2
scale = AP["target_moves"] / base

def wlist(spec): return [spec.get(h, 0.0) for h in range(24)]
def pick(w):
    x = random.random() * sum(w)
    for h, v in enumerate(w):
        x -= v
        if x <= 0: return h
    return 23

moves = []
for ri, r in enumerate(routes):
    dw, aw = AP["prof"][r["prof"]]
    n = max(1, int(r["freq"] * scale + random.random()))
    for k in range(n):
        al = r["al"][k % len(r["al"])]; ac = r["ac"][k % len(r["ac"])]
        for typ, w in (("D", wlist(dw)), ("A", wlist(aw))):
            moves.append(dict(type=typ, h=pick(w), r=ri, al=al, ac=ac))

for typ in ("A", "D"):
    for _ in range(80):
        changed = False
        for h in range(24):
            hs = [m for m in moves if m["type"] == typ and m["h"] == h]
            cap = AP["cap"](typ, h)
            if len(hs) > cap:
                random.shuffle(hs)
                for m in hs[cap:]:
                    for d in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, 8):
                        h2 = (h + d) % 24
                        if sum(1 for x in moves if x["type"] == typ and x["h"] == h2) < AP["cap"](typ, h2):
                            m["h"] = h2; changed = True; break
        if not changed: break

flights = []
for typ in ("A", "D"):
    for h in range(24):
        hs = [m for m in moves if m["type"] == typ and m["h"] == h]
        random.shuffle(hs)
        for i, m in enumerate(hs):
            m["t"] = round(h * 60 + (i + random.uniform(0.25, 0.75)) * 60 / len(hs), 2); flights.append(m)
flights.sort(key=lambda m: m["t"])

used = set()
def fnum(al, prof):
    lo = {"DOM": 100, "DOMT": 2000, "EURT": 1, "MET": 1}.get(prof, 1)
    span = 2400 if prof in ("DOM", "DOME", "EUL") else 3000 if prof == "DOMT" else 400 if prof == "EURT" else 200
    for _ in range(5000):
        n = lo + random.randint(0, span)
        if (al, n) not in used: used.add((al, n)); return n
counters = Counter()
for m in flights:
    r = routes[m["r"]]; n = fnum(m["al"], r["prof"])
    m["fn"] = f"{m['al']} {n}"; m["cs"] = f"{ICAO.get(m['al'], m['al'] + 'X')}{n}"
    m["pax"] = int(round(SEATS[m["ac"]] * min(0.98, LF + random.uniform(-0.08, 0.08))))
    i = counters[m["type"]]; counters[m["type"]] += 1
    m["rw"] = AP["rwy"](m["type"], m["t"], i)
f = AP["target_pax"] / sum(m["pax"] for m in flights)
for m in flights: m["pax"] = min(SEATS[m["ac"]], int(round(m["pax"] * f)))

ghosts = []
for m in flights:
    dur = routes[m["r"]]["dur"]
    if m["type"] == "D" and m["t"] - 1440 + dur > 0: ghosts.append(dict(type="D", t=m["t"] - 1440, r=m["r"]))
    if m["type"] == "A" and m["t"] + 1440 - dur < 1440: ghosts.append(dict(type="A", t=m["t"] + 1440, r=m["r"]))

dep = [m for m in flights if m["type"] == "D"]; arr = [m for m in flights if m["type"] == "A"]
pax = sum(m["pax"] for m in flights)
hourly = [sum(1 for m in flights if int(m["t"] // 60) == h) for h in range(24)]
busiest = max(range(24), key=lambda h: hourly[h])
c = Counter(routes[m["r"]]["code"] for m in flights)
print(AP["code"], f"dep {len(dep)} arr {len(arr)} total {len(flights)} pax {pax:,} busiest {busiest}:00 ({hourly[busiest]})")
print("hourly", hourly)
print("top", c.most_common(8), "cats", Counter(routes[m['r']]['cat'] for m in flights))
json.dump(dict(
    routes=[dict(code=r["code"], city=r["city"], lat=r["lat"], lon=r["lon"], dur=r["dur"], cat=r["cat"]) for r in routes],
    flights=[dict(type=m["type"], t=m["t"], r=m["r"], fn=m["fn"], cs=m["cs"], ac=m["ac"], pax=m["pax"], rw=m["rw"]) for m in flights],
    ghosts=ghosts,
    stats=dict(dep=len(dep), arr=len(arr), pax=pax, hourly=hourly, busiest=busiest, top=[[k, v] for k, v in c.most_common(10)]),
), open(f"schedule_{AP['code']}.json", "w"))
