"""Generate a representative 24-hour Heathrow schedule (departures + arrivals).

Route list, daily frequencies and block times are modelled on Heathrow's real
network; individual times and flight numbers are synthetic but follow the
airport's daily rhythm (night quota before 06:00, morning long-haul arrival
bank, evening Asia departures, ~44 movements/hour/runway cap, runway
alternation at 15:00).
"""
import json, math, random

random.seed(20261101)

H = lambda h, m=0: h * 60 + m

# code, city label, lat, lon, block minutes, daily freq (each way), profile, airlines, aircraft mix
R = [
    # ---------------- 0-2 h ----------------
    ("DUB", "DUBLIN", 53.4213, -6.2701, H(1, 15), 16, "EU", "BA EI", "A320 A320 A321 A320"),
    ("EDI", "EDINBURGH", 55.9500, -3.3725, H(1, 25), 14, "EU", "BA", "A320 A319 A321"),
    ("GLA", "GLASGOW", 55.8719, -4.4331, H(1, 25), 9, "EU", "BA", "A320 A319"),
    ("MAN", "MANCHESTER", 53.3537, -2.2750, H(1, 5), 6, "EU", "BA", "A319 A320"),
    ("ABZ", "ABERDEEN", 57.2019, -2.1978, H(1, 35), 6, "EU", "BA", "A319 A320"),
    ("BHD", "BELFAST", 54.6181, -5.8725, H(1, 20), 7, "EU", "BA EI", "A320 A319"),
    ("NCL", "NEWCASTLE", 55.0375, -1.6917, H(1, 10), 4, "EU", "BA", "A319"),
    ("JER", "JERSEY", 49.2079, -2.1955, H(1, 0), 3, "EU", "BA", "A319"),
    ("INV", "INVERNESS", 57.5425, -4.0475, H(1, 35), 2, "EU", "BA", "A319"),
    ("AMS", "AMSTERDAM", 52.3086, 4.7639, H(1, 15), 15, "EU", "BA KL KL", "A320 E190 737 A321"),
    ("CDG", "PARIS CDG", 49.0097, 2.5479, H(1, 15), 11, "EU", "BA AF", "A320 A319 A321"),
    ("BRU", "BRUSSELS", 50.9014, 4.4844, H(1, 10), 7, "EU", "BA SN", "A320 A319"),
    ("FRA", "FRANKFURT", 50.0333, 8.5706, H(1, 35), 12, "EU", "BA LH", "A320 A321 A320"),
    ("DUS", "DUSSELDORF", 51.2895, 6.7668, H(1, 20), 5, "EU", "BA EW", "A320 A319"),
    ("HAM", "HAMBURG", 53.6304, 9.9882, H(1, 35), 5, "EU", "BA", "A320"),
    ("MUC", "MUNICH", 48.3538, 11.7861, H(1, 50), 10, "EU", "BA LH", "A320 A321"),
    ("ZRH", "ZURICH", 47.4647, 8.5492, H(1, 40), 11, "EU", "BA LX", "A320 A220 A321"),
    ("GVA", "GENEVA", 46.2381, 6.1090, H(1, 40), 10, "EU", "BA LX", "A320 A220"),
    ("CPH", "COPENHAGEN", 55.6180, 12.6561, H(1, 55), 8, "EU", "BA SK", "A320 A320"),
    ("LUX", "LUXEMBOURG", 49.6233, 6.2044, H(1, 15), 3, "EU", "BA LG", "A319 E190"),
    ("SNN", "SHANNON", 52.7020, -8.9248, H(1, 20), 2, "EU", "EI", "A320"),
    ("ORK", "CORK", 51.8413, -8.4911, H(1, 15), 2, "EU", "EI", "A320"),
    ("GOT", "GOTHENBURG", 57.6628, 12.2798, H(1, 55), 2, "EU", "BA", "A320"),
    ("LYS", "LYON", 45.7256, 5.0811, H(1, 35), 3, "EU", "BA", "A319"),
    ("MRS", "MARSEILLE", 43.4393, 5.2214, H(1, 55), 3, "EU", "BA", "A320"),
    ("NCE", "NICE", 43.6584, 7.2159, H(1, 55), 6, "EU", "BA", "A320 A321"),
    ("TLS", "TOULOUSE", 43.6291, 1.3638, H(1, 45), 3, "EU", "BA", "A320"),
    ("BER", "BERLIN", 52.3667, 13.5033, H(1, 50), 6, "EU", "BA", "A320 A321"),
    ("STR", "STUTTGART", 48.6899, 9.2220, H(1, 35), 3, "EU", "BA", "A319"),
    ("MXP", "MILAN", 45.6306, 8.7231, H(1, 50), 8, "EU", "BA AZ", "A320 A321"),
    ("PRG", "PRAGUE", 50.1008, 14.2600, H(1, 55), 4, "EU", "BA OK", "A320"),
    # ---------------- 2-4 h ----------------
    ("MAD", "MADRID", 40.4719, -3.5626, H(2, 20), 12, "EU", "BA IB IB", "A320 A321 A320"),
    ("BCN", "BARCELONA", 41.2971, 2.0785, H(2, 10), 8, "EU", "BA VY", "A320 A321"),
    ("LIS", "LISBON", 38.7813, -9.1359, H(2, 40), 7, "EU", "BA TP", "A320 A321"),
    ("OPO", "PORTO", 41.2481, -8.6814, H(2, 15), 2, "EU", "BA", "A320"),
    ("FCO", "ROME", 41.8003, 12.2389, H(2, 35), 7, "EU", "BA AZ", "A320 A321"),
    ("VCE", "VENICE", 45.5053, 12.3519, H(2, 10), 2, "EU", "BA", "A320"),
    ("VIE", "VIENNA", 48.1103, 16.5697, H(2, 15), 6, "EU", "BA OS", "A320 A321"),
    ("OSL", "OSLO", 60.1939, 11.1004, H(2, 5), 6, "EU", "BA SK", "A320"),
    ("ARN", "STOCKHOLM", 59.6519, 17.9186, H(2, 25), 6, "EU", "BA SK", "A320"),
    ("HEL", "HELSINKI", 60.3172, 24.9633, H(2, 55), 5, "EU", "BA AY", "A321 A320"),
    ("WAW", "WARSAW", 52.1657, 20.9671, H(2, 30), 4, "EU", "BA LO", "A320 737"),
    ("BUD", "BUDAPEST", 47.4369, 19.2556, H(2, 30), 3, "EU", "BA", "A320"),
    ("ATH", "ATHENS", 37.9364, 23.9445, H(3, 45), 5, "EU", "BA A3", "A321 A320"),
    ("OTP", "BUCHAREST", 44.5711, 26.0850, H(3, 15), 3, "EU", "BA RO", "A320 737"),
    ("IST", "ISTANBUL", 41.2753, 28.7519, H(3, 50), 7, "EU", "BA TK TK", "A321 A330 A321"),
    ("KEF", "REYKJAVIK", 63.9850, -22.6056, H(3, 0), 2, "EU", "FI BA", "737 A320"),
    ("AGP", "MALAGA", 36.6749, -4.4991, H(2, 50), 3, "EU", "BA", "A320"),
    ("PMI", "PALMA", 39.5517, 2.7388, H(2, 20), 2, "EU", "BA", "A320"),
    ("GIB", "GIBRALTAR", 36.1512, -5.3497, H(2, 50), 1, "EU", "BA", "A320"),
    ("MLA", "MALTA", 35.8575, 14.4775, H(3, 5), 2, "EU", "KM BA", "A320"),
    ("RAK", "MARRAKECH", 31.6069, -8.0363, H(3, 35), 1, "EU", "BA", "A320"),
    ("CMN", "CASABLANCA", 33.3675, -7.5900, H(3, 10), 1, "EU", "AT", "737"),
    ("RIX", "RIGA", 56.9236, 23.9711, H(2, 45), 2, "EU", "BT", "A220"),
    ("SOF", "SOFIA", 42.6967, 23.4114, H(3, 0), 1, "EU", "BA", "A320"),
    ("BEG", "BELGRADE", 44.8184, 20.3091, H(2, 55), 1, "EU", "JU", "A320"),
    ("ZAG", "ZAGREB", 45.7429, 16.0688, H(2, 20), 1, "EU", "OU", "A220"),
    ("ALG", "ALGIERS", 36.6910, 3.2154, H(2, 35), 1, "EU", "AH", "737"),
    ("TUN", "TUNIS", 36.8510, 10.2272, H(2, 45), 1, "EU", "TU", "A320"),
    # ---------------- 4-8 h ----------------
    ("JFK", "NEW YORK JFK", 40.6413, -73.7781, H(7, 35), 18, "NAE", "BA BA BA VS VS AA AA DL", "777 A350 787 A350 A330 777 787 A330"),
    ("EWR", "NEWARK", 40.6895, -74.1745, H(7, 40), 5, "NAE", "UA UA BA VS", "787 777 777 787"),
    ("BOS", "BOSTON", 42.3656, -71.0096, H(7, 5), 6, "NAE", "BA BA VS DL AA", "777 A350 A330 A330 777"),
    ("YYZ", "TORONTO", 43.6777, -79.6248, H(7, 35), 6, "NAE", "AC AC BA", "787 777 777"),
    ("YUL", "MONTREAL", 45.4706, -73.7408, H(7, 10), 3, "NAE", "AC BA", "787 777"),
    ("PHL", "PHILADELPHIA", 39.8744, -75.2424, H(7, 50), 2, "NAE", "AA BA", "777 777"),
    ("BDA", "BERMUDA", 32.3640, -64.6787, H(7, 20), 1, "NAE", "BA", "777"),
    ("DXB", "DUBAI", 25.2532, 55.3657, H(6, 55), 10, "ME", "EK EK EK BA BA VS", "A380 A380 777 777 A350 A330"),
    ("DOH", "DOHA", 25.2731, 51.6081, H(6, 35), 8, "ME", "QR QR QR BA", "A380 A350 777 777"),
    ("AUH", "ABU DHABI", 24.4330, 54.6511, H(6, 55), 4, "ME", "EY EY BA", "A380 787 777"),
    ("BAH", "BAHRAIN", 26.2708, 50.6336, H(6, 25), 2, "ME", "GF BA", "787 777"),
    ("KWI", "KUWAIT", 29.2266, 47.9689, H(6, 0), 2, "ME", "KU BA", "777 777"),
    ("RUH", "RIYADH", 24.9576, 46.6988, H(6, 10), 3, "ME", "SV SV BA", "787 777 777"),
    ("JED", "JEDDAH", 21.6796, 39.1565, H(6, 15), 3, "ME", "SV SV BA", "777 787 777"),
    ("MCT", "MUSCAT", 23.5933, 58.2844, H(7, 5), 2, "ME", "WY BA", "787 787"),
    ("TLV", "TEL AVIV", 32.0055, 34.8854, H(5, 0), 6, "EU", "BA BA LY", "A321 777 787"),
    ("AMM", "AMMAN", 31.7226, 35.9932, H(5, 0), 2, "EU", "RJ BA", "787 A321"),
    ("BEY", "BEIRUT", 33.8209, 35.4884, H(4, 45), 2, "EU", "ME BA", "A321 A321"),
    ("CAI", "CAIRO", 30.1219, 31.4056, H(4, 55), 4, "EU", "MS BA", "787 A321"),
    ("LCA", "LARNACA", 34.8751, 33.6249, H(4, 35), 2, "EU", "BA", "A321"),
    ("GYD", "BAKU", 40.4675, 50.0467, H(5, 45), 1, "EU", "J2", "787"),
    ("LOS", "LAGOS", 6.5774, 3.3212, H(6, 35), 3, "AFRW", "BA VS BA", "777 A330 777"),
    ("ACC", "ACCRA", 5.6052, -0.1668, H(6, 40), 2, "AFRW", "BA", "787"),
    ("ABV", "ABUJA", 9.0068, 7.2632, H(6, 15), 1, "AFRW", "BA", "777"),
    ("ADD", "ADDIS ABABA", 8.9779, 38.7993, H(7, 40), 1, "AFR", "ET", "787"),
    # ---------------- 8 h + ----------------
    ("IAD", "WASHINGTON", 38.9531, -77.4565, H(8, 5), 5, "NAE", "BA BA UA VS", "777 A350 777 A330"),
    ("ORD", "CHICAGO", 41.9742, -87.9073, H(8, 55), 6, "NAE", "BA AA UA BA", "777 777 787 A350"),
    ("ATL", "ATLANTA", 33.6407, -84.4277, H(9, 20), 4, "NAE", "DL DL VS BA", "A330 A350 A330 777"),
    ("MIA", "MIAMI", 25.7959, -80.2870, H(9, 35), 4, "NAE", "BA AA BA", "777 777 A380"),
    ("DFW", "DALLAS", 32.8998, -97.0403, H(10, 15), 4, "NAE", "AA AA BA", "777 787 777"),
    ("IAH", "HOUSTON", 29.9902, -95.3368, H(10, 5), 3, "NAE", "BA UA BA", "777 787 A380"),
    ("MCO", "ORLANDO", 28.4312, -81.3081, H(9, 20), 1, "NAE", "BA", "777"),
    ("BGI", "BARBADOS", 13.0746, -59.4925, H(8, 45), 1, "NAE", "BA", "777"),
    ("LAX", "LOS ANGELES", 33.9416, -118.4085, H(11, 0), 7, "NAW", "BA BA VS VS AA UA", "A380 777 787 A350 777 787"),
    ("SFO", "SAN FRANCISCO", 37.6213, -122.3790, H(11, 0), 5, "NAW", "BA BA UA VS", "A380 777 787 787"),
    ("SEA", "SEATTLE", 47.4502, -122.3088, H(9, 45), 3, "NAW", "BA VS DL", "777 A350 A330"),
    ("YVR", "VANCOUVER", 49.1967, -123.1815, H(9, 40), 3, "NAW", "BA AC AC", "777 787 787"),
    ("YYC", "CALGARY", 51.1215, -114.0076, H(9, 0), 1, "NAW", "WS", "787"),
    ("DEN", "DENVER", 39.8561, -104.6737, H(9, 40), 2, "NAW", "BA UA", "777 787"),
    ("LAS", "LAS VEGAS", 36.0840, -115.1537, H(10, 40), 1, "NAW", "BA", "777"),
    ("PHX", "PHOENIX", 33.4342, -112.0116, H(10, 50), 1, "NAW", "BA", "777"),
    ("AUS", "AUSTIN", 30.1975, -97.6664, H(10, 15), 1, "NAE", "BA", "787"),
    ("MEX", "MEXICO CITY", 19.4361, -99.0719, H(11, 40), 1, "SAM", "BA", "777"),
    ("GRU", "SAO PAULO", -23.4356, -46.4731, H(11, 40), 2, "SAM", "BA LA", "777 777"),
    ("GIG", "RIO DE JANEIRO", -22.8090, -43.2506, H(11, 30), 1, "SAM", "BA", "777"),
    ("EZE", "BUENOS AIRES", -34.8222, -58.5358, H(13, 55), 1, "SAM", "BA", "777"),
    ("NBO", "NAIROBI", -1.3192, 36.9278, H(8, 40), 2, "AFR", "BA KQ", "787 787"),
    ("JNB", "JOHANNESBURG", -26.1392, 28.2460, H(11, 5), 3, "AFR", "BA BA VS", "A380 777 A350"),
    ("CPT", "CAPE TOWN", -33.9715, 18.6021, H(11, 40), 1, "AFR", "BA", "777"),
    ("MRU", "MAURITIUS", -20.4302, 57.6836, H(12, 0), 1, "AFR", "MK", "A350"),
    ("DEL", "DELHI", 28.5562, 77.1000, H(8, 55), 6, "ASIA", "BA BA AI AI VS", "777 787 777 787 787"),
    ("BOM", "MUMBAI", 19.0896, 72.8656, H(9, 30), 6, "ASIA", "BA BA AI VS", "777 A350 777 787"),
    ("BLR", "BENGALURU", 13.1986, 77.7066, H(10, 20), 2, "ASIA", "BA AI", "777 787"),
    ("HYD", "HYDERABAD", 17.2403, 78.4294, H(10, 5), 2, "ASIA", "BA AI", "787 787"),
    ("MAA", "CHENNAI", 12.9941, 80.1709, H(10, 20), 1, "ASIA", "BA", "787"),
    ("ISB", "ISLAMABAD", 33.5490, 72.8256, H(8, 20), 2, "ASIA", "PK BA", "777 787"),
    ("LHE", "LAHORE", 31.5216, 74.4036, H(8, 35), 2, "ASIA", "PK VS", "777 787"),
    ("DAC", "DHAKA", 23.8433, 90.3978, H(10, 20), 1, "ASIA", "BG", "787"),
    ("CMB", "COLOMBO", 7.1808, 79.8841, H(11, 0), 1, "ASIA", "UL", "A330"),
    ("MLE", "MALDIVES", 4.1918, 73.5291, H(10, 45), 1, "ASIA", "BA", "777"),
    ("SIN", "SINGAPORE", 1.3644, 103.9915, H(13, 10), 6, "ASIA", "SQ SQ SQ BA BA QF", "A380 A350 777 777 A350 A380"),
    ("HKG", "HONG KONG", 22.3080, 113.9185, H(12, 15), 6, "ASIA", "CX CX CX BA BA", "A350 777 A350 777 A350"),
    ("HND", "TOKYO", 35.5494, 139.7798, H(14, 0), 4, "ASIA", "BA JL NH BA", "777 777 777 A350"),
    ("ICN", "SEOUL", 37.4602, 126.4407, H(13, 50), 2, "ASIA", "KE BA", "A380 777"),
    ("PEK", "BEIJING", 40.0799, 116.6031, H(10, 30), 2, "ASIA", "CA BA", "777 787"),
    ("PVG", "SHANGHAI", 31.1443, 121.8083, H(12, 0), 2, "ASIA", "MU VS", "777 787"),
    ("BKK", "BANGKOK", 13.6900, 100.7501, H(11, 50), 2, "ASIA", "TG BA", "777 777"),
    ("KUL", "KUALA LUMPUR", 2.7456, 101.7099, H(13, 10), 1, "ASIA", "MH", "A350"),
    ("PER", "PERTH", -31.9385, 115.9672, H(17, 20), 1, "ASIA", "QF", "787"),
]

SEATS = {"A319": 143, "A320": 177, "A321": 205, "E190": 98, "A220": 135, "737": 186,
         "A330": 275, "787": 245, "777": 320, "A350": 320, "A380": 490}
LF = {"A319": .80, "A320": .82, "A321": .84, "E190": .76, "A220": .78, "737": .80,
      "A330": .85, "787": .86, "777": .86, "A350": .86, "A380": .87}

# hour weights (LHR local time) for each profile
def W(spec):
    w = [0.0] * 24
    for k, v in spec.items():
        w[k] = v
    return w

PROF = {
    "EU": (W({6: 1.3, 7: 1.4, 8: 1.1, 9: .9, 10: .9, 11: .9, 12: 1.0, 13: .9, 14: .9, 15: .9, 16: 1.0, 17: 1.1, 18: 1.1, 19: 1.0, 20: .8, 21: .55, 22: .12}),
           W({7: .55, 8: .95, 9: 1.1, 10: 1.0, 11: .9, 12: .95, 13: 1.0, 14: .9, 15: .95, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.05, 20: 1.0, 21: .95, 22: .7, 23: .18})),
    "NAE": (W({8: .5, 9: .8, 10: 1.0, 11: 1.1, 12: 1.0, 13: .9, 14: .9, 15: .9, 16: .9, 17: .8, 18: .7, 19: .5, 20: .25}),
            W({5: .35, 6: 1.6, 7: 1.6, 8: 1.3, 9: 1.0, 10: .7, 11: .45, 12: .2, 18: .15, 19: .3, 20: .35, 21: .3})),
    "NAW": (W({9: .4, 10: .9, 11: 1.0, 12: 1.0, 13: .9, 14: .9, 15: .9, 16: .8, 17: .4}),
            W({6: .2, 7: .4, 8: .5, 9: .6, 10: .8, 11: 1.0, 12: 1.0, 13: .9, 14: .7, 15: .4})),
    "ME": (W({8: .5, 9: .7, 10: .6, 13: .7, 14: .7, 15: .6, 16: .3, 19: .5, 20: .8, 21: .9, 22: .45}),
           W({6: .7, 7: .9, 8: .5, 12: .5, 13: .8, 14: .6, 15: .2, 18: .4, 19: .7, 20: .5})),
    "ASIA": (W({9: .25, 11: .25, 12: .3, 13: .2, 17: .2, 18: .55, 19: .85, 20: 1.0, 21: 1.0, 22: .6}),
             W({4: .9, 5: 1.25, 6: 1.25, 7: .8, 8: .4, 13: .25, 14: .2, 15: .25, 16: .2, 17: .25, 18: .3})),
    "AFR": (W({19: .7, 20: 1.0, 21: 1.0, 22: .6}),
            W({5: .8, 6: 1.1, 7: 1.0, 8: .6})),
    "AFRW": (W({9: .6, 10: .8, 11: .7, 12: .4, 21: .6, 22: .4}),
             W({5: .6, 6: .8, 17: .5, 18: .7, 19: .6})),
    "SAM": (W({19: .5, 20: .9, 21: 1.0, 22: .5}),
            W({11: .6, 12: 1.0, 13: .9, 14: .4})),
}

def pick_hour(w):
    tot = sum(w)
    x = random.random() * tot
    for h, v in enumerate(w):
        x -= v
        if x <= 0:
            return h
    return 23

def cat_of(minutes):
    if minutes < 120: return 0
    if minutes < 240: return 1
    if minutes < 480: return 2
    return 3

routes = []
for i, (code, city, lat, lon, dur, freq, prof, al, ac) in enumerate(R):
    routes.append(dict(code=code, city=city, lat=lat, lon=lon, dur=dur, cat=cat_of(dur), freq=freq,
                       prof=prof, al=al.split(), ac=ac.split()))

# ---- flight numbers: unique per airline
fn_used = set()
fn_next = {}
FN_BASE = {"BA": {"EU": 300, "NAE": 100, "NAW": 260, "ME": 100, "ASIA": 10, "AFR": 50, "AFRW": 70, "SAM": 240}}
def flight_no(al, prof):
    base = FN_BASE.get(al, {}).get(prof, 1 + (hash(al) % 7) * 3)
    for _ in range(4000):
        n = base + random.randint(0, 899 if (al == "BA" and prof == "EU") else 180)
        if (al, n) not in fn_used:
            fn_used.add((al, n))
            return f"{al} {n}"
    raise RuntimeError

# ---- build movements: one departure + one arrival per frequency unit
moves = []
for ri, r in enumerate(routes):
    dw, aw = PROF[r["prof"]]
    n = int(r["freq"] * 1.25 + random.random() * 0.999) if r["freq"] > 1 else 1
    for k in range(n):
        al = r["al"][k % len(r["al"])]
        ac = r["ac"][k % len(r["ac"])]
        for typ, w in (("D", dw), ("A", aw)):
            h = pick_hour(w)
            moves.append(dict(type=typ, h=h, r=ri, al=al, ac=ac))

# extra late-running arrivals just after midnight (delayed from last evening)
for code in ("MAD", "FCO", "ATH"):
    ri = next(i for i, r in enumerate(routes) if r["code"] == code)
    moves.append(dict(type="A", h=0, r=ri, al="BA", ac="A320", late=True))

# night quota: arrivals before 06:00 limited (first scheduled ~04:30)
CAP = {"A": 44, "D": 45}
def hour_cap(typ, h):
    if typ == "A":
        if h == 0: return 3
        if h < 4: return 0
        if h == 4: return 6
        if h == 5: return 12
        if h == 23: return 10
    else:
        if h < 6: return 0
        if h == 22: return 22
        if h == 23: return 2
    return CAP[typ]

for typ in ("A", "D"):
    for _ in range(50):
        changed = False
        for h in range(24):
            hs = [m for m in moves if m["type"] == typ and m["h"] == h]
            cap = hour_cap(typ, h)
            if len(hs) > cap:
                random.shuffle(hs)
                for m in hs[cap:]:
                    # move to the nearest hour with room (prefer later for night arrivals)
                    for d in (1, -1, 2, -2, 3, -3, 4, -4, 5, 6):
                        h2 = h + d
                        if 0 <= h2 < 24 and sum(1 for x in moves if x["type"] == typ and x["h"] == h2) < hour_cap(typ, h2):
                            m["h"] = h2
                            changed = True
                            break
        if not changed:
            break

# spread within each hour
flights = []
for typ in ("A", "D"):
    for h in range(24):
        hs = [m for m in moves if m["type"] == typ and m["h"] == h]
        random.shuffle(hs)
        k = len(hs)
        lo = 30 if (typ == "A" and h == 4) else 0
        span = 60 - lo
        for i, m in enumerate(hs):
            t = h * 60 + lo + (i + random.uniform(0.25, 0.75)) * span / k
            m["t"] = round(t, 2)
            flights.append(m)

flights.sort(key=lambda m: m["t"])
for m in flights:
    r = routes[m["r"]]
    m["fn"] = flight_no(m["al"], r["prof"])
    lf = LF[m["ac"]] + random.uniform(-0.07, 0.07)
    m["pax"] = int(round(SEATS[m["ac"]] * min(lf, 0.98)))
    # westerly operations; runway alternation at 15:00
    if m["type"] == "A":
        m["rw"] = "27R" if m["t"] < 900 else "27L"
    else:
        m["rw"] = "27L" if m["t"] < 900 else "27R"
    m.pop("h", None)

# previous-day departures still airborne at 00:00, next-day arrivals already airborne at 24:00
ghosts = []
for m in flights:
    dur = routes[m["r"]]["dur"]
    if m["type"] == "D" and m["t"] - 1440 + dur > 0:
        ghosts.append(dict(type="D", t=m["t"] - 1440, r=m["r"], fn=m["fn"], ghost=1))
    if m["type"] == "A" and m["t"] + 1440 - dur < 1440 and not m.get("late"):
        ghosts.append(dict(type="A", t=m["t"] + 1440, r=m["r"], fn=m["fn"], ghost=1))

PAX_TARGET = 229_800
f = PAX_TARGET / sum(m["pax"] for m in flights)
for m in flights:
    m["pax"] = min(int(round(m["pax"] * f)), SEATS[m["ac"]])
dep = [m for m in flights if m["type"] == "D"]
arr = [m for m in flights if m["type"] == "A"]
pax = sum(m["pax"] for m in flights)
hourly = [sum(1 for m in flights if int(m["t"] // 60) == h) for h in range(24)]
busiest = max(range(24), key=lambda h: hourly[h])
from collections import Counter
c = Counter(routes[m["r"]]["code"] for m in flights)
print(f"departures {len(dep)} arrivals {len(arr)} total {len(flights)} pax {pax:,}")
print("hourly", hourly, "busiest", busiest, hourly[busiest])
print("top", [(routes[[r['code'] for r in routes].index(k)]['city'], v) for k, v in c.most_common(8)])
print("cats", Counter(routes[m['r']]['cat'] for m in flights))
print("ghosts", len(ghosts))
print("first dep", dep[0]["t"], "last dep", dep[-1]["t"], "first arr", arr[0]["t"], "last arr", arr[-1]["t"])

out = dict(
    routes=[dict(code=r["code"], city=r["city"], lat=r["lat"], lon=r["lon"], dur=r["dur"], cat=r["cat"]) for r in routes],
    flights=[dict(type=m["type"], t=m["t"], r=m["r"], fn=m["fn"], ac=m["ac"], pax=m["pax"], rw=m["rw"]) for m in flights],
    ghosts=ghosts,
    stats=dict(dep=len(dep), arr=len(arr), pax=pax, hourly=hourly, busiest=busiest,
               top=[[k, v] for k, v in c.most_common(10)]),
)
json.dump(out, open("schedule.json", "w"))
