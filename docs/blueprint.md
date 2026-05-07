FYP FUNDAMENTALS

# FYP BLUEPRINT

- What is the Title of your FYP? Is it Unique?
Predicting Air Pollution Levels in Malaysia Using Real Time Web Data

- What is the Concept of your FYP? Is it Unique? (Is it a Program?)
Planned to make a HTML UI and use FastAPI for backend. People usually only see the PM2.5 but doesn’t know what it is. Expect first looking to understand. The same as µg/m³.
The plan of this process: Fetch → Clean → Align (time+location) → Merge → Feature build → Forecast → Alerts/Explain → Display
Then, using Real-time multi-source pipeline (Malaysia-specific), which:
- Integrate APIMS + METMalaysia weather + NASA FIRMS into one pipeline (data cleaning, joining, automation) (Real-Time update).
- Many papers do modeling, but fewer do a working pipeline + system.
From it, you can make your own understanding mostly “why the air quality is like this” from METMalaysia and FIRMS. METMalaysia have the data of wind, humidity, rain, and wind direction, while FIRMS are fire data. From there create the logic statement.
QUESTION NOT ANSWERED: Later what you want to show using the 3 different source in your UI?
[Also NOTE: Stay “updated” when you’re offline (what’s actually possible). While offline, you can: Show the last cached data. Show “Last updated: …”]
Then, use statistics realtime graph for the air qualities. From the realtime graph:
- Refer to “WHAT ANALYSTS WANT TO SPOT ON (FROM THE CHARTS)”  page

- What TOOLS are you going to use to make your FYP?
Visual Studio Code

- What Programming Language you are going to use to make your FYP?
Python, HTML, CSS, JavaScript, Python FastAPI

# Link for the API
- APIMS:
https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY/CAQM_MCAQM_Current_Reading/MapServer/0/query?f=json&outFields=*&returnGeometry=false&spatialRel=esriSpatialRelIntersects&where=1%3D1 (Updated HOURLY)
https://eqms.doe.gov.my/api3/publicportalapims/apitablehourly?stateid=1&datetime=2026-02-11T16:00:00& (TO BE SPECIFIC, CAN CHANGE THE DATE HERE) (Maybe can change the DATE to make like between date ___ and date____ ?) (And can adjust 1 hour automatically using code by referring through my timestamp?)

- METGovMy:
https://www.met.gov.my/json/cuaca_semasa/data.json  (In UTC Timestamp) (Updated to Latest) (Maybe can adjust to APIMS by decreasing the timestamp automatically like “data.json?timestamp=____” ?)

- NASA FIRMS:
https://firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/VIIRS_SNPP_NRT/95,-6,119.5,7.6/1
(MAP_KEY is loaded from a local `.env` file at runtime — never committed. Bounding box widened from `99,0.8,119.5,7.6` to `95,-6,119.5,7.6` to include all of Sumatra and Indonesian Borneo, the main transboundary haze source regions per ASMC.)

# WHY PEOPLE NEED INTEGRATE APIMS + METMALAYSIA WEATHER + NASA FIRMS INTO ONE PIPELINE? (DATA CLEANING, JOINING & AUTOMATION)
Yes, people do need it, especially in Malaysia/ASEAN where air quality can change quickly during haze/fire episodes.
Why a real-time multi-source pipeline is useful (not just “nice to have”)
- Health + daily decisions: Air pollution (especially fine particles like PM2.5) is strongly linked to respiratory and cardiovascular harm, and WHO estimates millions of premature deaths globally are associated with air pollution exposure.
- Malaysia has real disruptions: During haze periods, Malaysia has official response triggers like school actions/closures or moving to online learning when API gets very high (e.g., API > 200 is used in guidance). A forecast helps people prepare before the readings cross thresholds.
- Transboundary haze is real: ASMC reports and alerts show smoke haze/hotspots in the region can drift into western Peninsular Malaysia depending on winds and weather.
What your pipeline adds beyond “existing apps”
Malaysia already has APIMS for official air quality readings. 
But many users still lack:
- Short-term prediction (1–24h) + confidence (“will it get worse later today?”)
- Cause/explanation (“is this local traffic + weather trapping pollution, or regional fires?”)
- One place that combines signals:
  - APIMS readings
  - METMalaysia weather API (wind/rain/stability)
  - NASA FIRMS near-real-time fire hotspots (available within hours)
Who would actually use it
- Schools/parents (outdoor activity decisions, online learning readiness)
- People with asthma/heart conditions planning travel/exercise
- Event organizers, delivery/logistics, local councils (risk alerts + planning)
If your FYP delivers a working pipeline + dashboard + alert logic + “why it’s happening” explanations, that’s a strong “real-world system” contribution (not just another prediction model).
# INFORMATION ABOUT BIGGEST GAPS PEOPLE SAY THEY HAVE ABOUT “AIR INFORMATION”
Here are the biggest gaps people say they have about “air information” (pulled from Reddit discussions, app reviews, and government/official investigation-style sources)—with sources for each.
1) They don’t understand what the numbers mean (AQI vs PM2.5, and “which AQI”)
People regularly mix up AQI (an index) with PM2.5 (one pollutant measurement), so they don’t know what they’re actually looking at or comparing. 
Some also get confused when AQI values differ across devices/apps because they’re using different AQI standards (e.g., US vs China AQI).

Example 1: Mixing up AQI and PM2.5
Think of it like this:
- PM2.5 = the amount of tiny dust/smoke in the air (a measurement, like “60 µg/m³”).
- AQI = a converted score (0–500) that tells how risky the air is, with colors (green/yellow/red).
What people often do (wrong)
They see PM2.5 = 60 and assume:
“Oh AQI is 60… that’s not too bad.”
What it actually means
If PM2.5 is around 60 µg/m³, the AQI is roughly ~153 (red zone in US AQI terms).
So the person underestimates the danger because they treated PM2.5 like it was AQI.
✅ In short: PM2.5 is an ingredient. AQI is the final “risk score.”

2) They lack hyperlocal accuracy (wrong nearest station, sparse monitoring)
Users complain that apps can assume the wrong location or not show a truly nearby station, which makes the “air info” feel irrelevant or untrustworthy. 
You can also see this in App Store reviews (example from Malaysia) mentioning inaccurate location tracking, while still relying on the app during haze. 
On the “trusted investigations” side, a U.S. GAO report notes that existing monitoring networks can’t provide all the information users need (coverage/real-time needs), and lower-cost sensors can help fill gaps—if used carefully.
3) They don’t know what sensors can/can’t measure (PM vs gases, weather effects)
A common misunderstanding: many consumer sensors detect particles (PM) but not gases, and conditions like fog/humidity can distort PM readings—so people don’t know when readings are “real” vs influenced by weather.
4) They lack trust because calibration/quality control isn’t obvious
People often suspect sensor data is “wrong,” but don’t know that calibration and environment (humidity/temperature) strongly affect low-cost sensor accuracy. A 2024 scientific preprint focuses specifically on PurpleAir correction models for warm/humid climates, showing why raw readings may need correction. 
The EPA’s air sensor guidebook is essentially built around this gap—helping users plan, interpret, communicate, and understand sensor performance limits.
5) They want “what to do now” + “why it’s happening,” not just a score
A lot of frustration comes from apps showing a number, but not giving clear, situation-specific guidance (e.g., outdoor exercise, masks, ventilation) or explaining causes (fires/traffic/weather). The EPA guidebook explicitly includes how to interpret, communicate, and act on sensor results—highlighting that this is a real user need.
If you tell me your target users (Malaysia public? schools? clinics? runners? parents with kids?), I can map these gaps into specific app/program features (alerts, education screens, “why this happened” explanations, indoor/outdoor split, sensor confidence score, etc.).

# how do I get apims, metmalaysia and firms into my html and use fastapi to make sure it goes real time? keep updated even though i go offline
You can absolutely do this with HTML (frontend) + FastAPI (backend). The key idea is:
- FastAPI runs on a server (your laptop or cloud) and keeps fetching data on a schedule (every X minutes).
- It stores the latest data in a database/cache.
- Your HTML page just calls your FastAPI endpoints to display “real-time” updates.

Simple architecture (what you’re building)
Data Sources (APIMS + METMalaysia + FIRMS)
→ FastAPI fetcher (scheduled job)
→ Store into DB (SQLite/Postgres)
→ FastAPI endpoints (/latest, /weather, /fires, /forecast)
→ HTML page fetch() every 30–60 seconds

# What analysts want to spot on (from the charts)
1) Threshold exceedances (health-relevant)
They look for when levels cross action thresholds (not just “up/down”). A common way is an index view (AQI/API): categories like Good/Moderate/Unhealthy, and AQI > 100 is when it becomes unhealthy (first for sensitive groups, then everyone as it rises). 
For PM2.5, analysts also compare against health guidelines (WHO has tightened PM2.5 guideline values).
UI needs: threshold lines + “minutes/hours above threshold” + “first exceedance time” + severity.
2) Episode shape: spike vs sustained haze
A 10-minute spike is different from a 12-hour sustained elevation. Real-time reporting often uses weighted short-term averages (e.g., NowCast concept) to reflect rapidly changing conditions like fire events.
UI needs: toggle between raw hourly and rolling averages (3h/12h/24h), plus “episode duration”.
3) Anomalies that look like sensor problems
Analysts routinely look for flatlines, sudden step-changes, impossible values, or one station that doesn’t match neighbors. There are dashboards designed specifically for QC that combine algorithms to flag anomalous measurements.
UI needs: automatic “data quality flags” + a “why flagged” tooltip.
4) “Where did it come from?” (direction/source clues)
A standard technique is combining pollutant concentration with wind direction (a “pollution rose”) to infer source direction relative to a station.
UI needs: wind overlay + pollution rose (or at least wind direction arrows during peaks).

# Aim & Objectives
Aim 1: Build a Malaysia-specific real-time data pipeline that combines official air-quality readings with weather and fire signals.
Objective 1: Implement a backend (e.g., FastAPI scheduler) that fetches → cleans → time/location-aligns → merges data from:
- DOE Malaysia APIMS air-quality readings,
- METMalaysia MET API Web Services (wind, humidity, rain, etc.),
- NASA FIRMS near real-time active fire/hotspots.

Aim 2: Provide short-term air pollution prediction (1–24 hours) so users can prepare before conditions worsen.
Objective 2: Generate and display a 1–24h forecast/nowcast and trigger alerts when pollution reaches “actionable” levels (e.g., API > 200 guidance used during haze periods).

Aim 3: Improve user understanding and trust by explaining why air quality changes and keeping the UI useful even when connectivity is limited (internet is weak).
Objective 3: In the UI, include:
- a “possible cause” explanation that links weather conditions + hotspot activity (METMalaysia + FIRMS),
- and an offline-friendly mode that shows last cached data + last updated timestamp (your blueprint explicitly notes this).
[This is how it looks: APIMS = your main air-quality signal (current readings + the thing you want to predict next, e.g., API/PM2.5). Then, METMalaysia weather = factors that change pollution (wind, rain, humidity, temperature), used as inputs to explain/forecast changes. Finally, NASA FIRMS = smoke/fire sources (hotspots near or upwind), also used as inputs.]
