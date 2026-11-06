# Europe's bomb hoax wave: 2–5 November 2026

This is a 60-second vertical explainer, 1080×1920 at 60 fps with sound. It shows the
hoax bomb threats made against passenger flights in Europe between Monday 2 and Thursday
5 November 2026.

Every route, outcome and number on screen comes from the reporting below, as published
up to 6 November 2026. Where outlets give different counts, the video says so and shows
the reported range.

## What the video shows

| Day | Flight | Outcome shown | Sources |
|---|---|---|---|
| Mon 2 Nov | Wizz Air W6 4302, London Luton → Sofia | Threat received over Bosnia & Herzegovina. The flight diverted to Budapest, escorted by a Hungarian Gripen. | [Euronews](https://www.euronews.com/2026/11/02/wizz-air-flight-from-london-to-sofia-diverts-after-bomb-threat), [Aviation24](https://www.aviation24.be/airlines/wizz-air/flight-diverted-to-budapest-after-bomb-threat-escorted-by-hungarian-gripen-fighters/), [AeroCorner](https://aerocorner.com/news/wizz-air-w64302-luton-sofia-budapest-bomb-threat-gripen/) |
| Tue 3 Nov | LOT, London Heathrow → Warsaw | Diverted to Modlin. Modlin closed, then reopened after the search. | [Reuters factbox (US News)](https://www.usnews.com/news/world/articles/2026-11-03/factbox-europe-wide-bomb-threats-disrupt-air-travel), [CNN](https://edition.cnn.com/2026/11/03/europe/bomb-threat-airport-warsaw-intl) |
| Tue 3 Nov | SAS, Copenhagen → Warsaw | Landed at Chopin and the aircraft was checked. The threat was not confirmed. | Reuters factbox, [AeroTime](https://www.aerotime.aero/articles/ryanair-wizz-air-lot-polish-sas-targeted-bomb-threat) |
| Tue 3 Nov | Ryanair, Lisbon & Dublin → Rome | Searched at Fiumicino. The Italian Air Force escorted a Ryanair plane into Rome. | Reuters factbox, AeroTime |
| Tue 3 Nov | Ryanair, Manchester → Murcia | Parts of the airport were cordoned off. | Reuters factbox, [Gulf Business](https://gulfbusiness.com/en/2026/aviation/bomb-threats-target-seven-flights-across-europe-triggering-diversions-and-airport-shutdowns/) |
| Tue 3 Nov | Milan-Bergamo & Dublin → Sofia | Threats against both, per Bulgaria's transport ministry. | Reuters factbox |
| Tue 3 Nov | Total: 7 flights (Ryanair ×4, LOT, SAS, Wizz Air) | The UK government called them "malicious hoax threats". | [AirHelp](https://www.airhelp.com/en-int/flight-disruptions/ryanair-wizz-air-lot-sas-seven-flights-bomb-hoaxes-03112026/), [CNBC](https://www.cnbc.com/2026/11/05/bomb-threats-flights-europe.html) |
| Thu 5 Nov | Aer Lingus EI402, Dublin → Rome | Diverted to Évreux air base in France. 151 passengers and 6 crew were safe, and French Air Force jets were dispatched. | [France 24](https://www.france24.com/en/europe/20261105-dublin-rome-flight-diverted-to-france-over-bomb-threat), [Irish Times](https://www.irishtimes.com/world/europe/2026/11/05/bomb-threat-diverts-aer-lingus-plane-going-from-dublin-to-rome-french-pm-says/), [NBC News](https://www.nbcnews.com/world/europe/bomb-threat-plane-dublin-rome-diverted-aer-lingus-france-rcna607594) |
| Thu 5 Nov | Finnair AY1761, Helsinki → Rome | Escorted into Rome by Italian Air Force jets. The bomb squad found nothing. | NBC News, Reuters factbox |
| Thu 5 Nov | Ryanair London, Copenhagen & Madrid → Sofia | The London flight diverted to Plovdiv, and Bulgaria's air force escorted all three. | [Al Jazeera](https://www.aljazeera.com/news/2026/11/5/bomb-threat-diverts-dublin-rome-flight-to-france), [Gulf News](https://gulfnews.com/business/aviation/europe-flight-disruptions-20-planes-targeted-by-hoax-bomb-threats-for-third-day-1.500737879) |
| Thu 5 Nov | Wizz Air, Milan → Warsaw | Diverted to Vienna. | Al Jazeera |
| Thu 5 Nov | easyJet, Newcastle & Glasgow → Prague | Met by police in Prague. Prague Airport received one anonymous email naming four flights. | [CNN](https://www.cnn.com/2026/11/05/europe/europe-bomb-threat-intl), Reuters factbox |
| Thu 5 Nov | Finnair Helsinki → Vienna, Air Serbia Belgrade → Bucharest, LOT Warsaw → Brussels | All landed and nothing was found. | Reuters factbox, CNBC |
| Thu 5 Nov | Madrid-Barajas | 3 emailed threats in under 20 minutes affected 6 Iberia and Air Europa flights. In Warsaw, a LOT jet was stopped on the taxiway. | CNN, Reuters factbox |
| Thu 5 Nov | Total: at least 27 flights | No explosives were found. Counts vary by outlet: CNN 14+, France 24 25+, RTÉ 27+. | [RTÉ](https://www.rte.ie/news/europe/2026/1105/1598073-europe-flight-threats/), France 24, CNN |
| How / who | Anonymous emails (Czech, Italian and Spanish authorities). No one identified. The EU says it is not yet clear whether the threats are linked. | | CNN, France 24, [Cyprus Mail / Reuters](https://cyprus-mail.com/2026/11/06/europe-flight-bomb-threats-raise-hybrid-attack-fears) |

## How the totals are built

- **About 35 flights hit:** 1 on Monday, 7 on Tuesday and at least 27 on Thursday. The
  map draws the 18 Thursday flights that were named individually. The counter then adds
  the other 9 to reach the reported 27.
- **At least 5 diverted:** Budapest, Modlin, Évreux, Plovdiv and Vienna.
- **At least 7 fighter escorts:**
  - Hungarian Gripen on Monday.
  - Italian Air Force into Rome on Tuesday.
  - On Thursday: the French Air Force for EI402, Italian jets for AY1761, and three
    Bulgarian escorts of Ryanair flights to Sofia.
- **0 bombs found:** every authority that reported searches found no explosives.

## Not shown

The video leaves out who is responsible, because no one has been publicly identified.
It also leaves out flights reported without route details, such as an Aegean flight
and a Cork Airport service.

## Rebuild

```bash
ln -s ../airports-24h/node_modules node_modules   # three is not needed, only topojson-client + world-atlas
node render.js events events.json
python3 hoax_audio.py events.json soundtrack.wav
for i in 0 1 2 3; do node render.js chunk $((i*900)) $(((i+1)*900)) out/c$i.mp4 & done; wait
# concat out/c0..c3.mp4 and mux soundtrack.wav with ffmpeg
```
