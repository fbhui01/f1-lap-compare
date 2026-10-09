import os
import sys
import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def pick(options):
    for i in range(len(options)):
        print(" ", i + 1, "-", options[i])
    while True:
        ans = input("enter a number\n").strip()
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            return int(ans) - 1
        print("type a number between 1 and", len(options))


def getlap(session, d):
    lap = session.laps.pick_drivers(d).pick_fastest()
    if lap is None:
        print(d, "didnt set a valid lap in this session, try someone else")
        sys.exit()
    tel = lap.get_car_data().add_distance()
    return lap, tel



if not os.path.exists("cache"):
    os.mkdir("cache")
fastf1.Cache.enable_cache("cache")
fastf1.set_log_level("WARNING")

now = pd.Timestamp.now(tz="UTC").tz_localize(None)

print("----- F1 lap comparison -----")

while True:
    ans = input("\nwhich year? (2018-" + str(now.year) + ", press enter for " + str(now.year) + ")\n").strip()
    if ans == "":
        year = now.year
        break
    if ans.isdigit() and 2018 <= int(ans) <= now.year:
        year = int(ans)
        break
    print("enter a year between 2018 and", now.year)

print("\ngetting the", year, "calendar...")
schedule = fastf1.get_event_schedule(year, include_testing=False)
schedule = schedule[schedule["Session1DateUtc"] < now]

if len(schedule) == 0:
    print("no races have happened yet in", year)
    sys.exit()

races = []
for i, race in schedule.iterrows():
    races.append("Round " + str(race["RoundNumber"]) + ": " + race["EventName"] + " (" + race["Location"] + ")")

print("\nwhich race?")
event = schedule.iloc[pick(races)]

sessions = []
for n in range(1, 6):
    name = event["Session" + str(n)]
    date = event["Session" + str(n) + "DateUtc"]
    if name and pd.notna(date) and date < now:
        sessions.append(name)

if "Qualifying" in sessions:
    sessions.remove("Qualifying")
    sessions.insert(0, "Qualifying")

print("\nwhich session? (qualifying is best for comparing)")
sess = sessions[pick(sessions)]

print("\nloading data (first time takes a minute or two)...")
try:
    session = fastf1.get_session(year, int(event["RoundNumber"]), sess)
    session.load(weather=False, messages=False)
    session.car_data
except Exception as e:
    print("couldnt load that session, check your internet or try another one")
    print("error:", e)
    sys.exit()

codes = list(session.results["Abbreviation"])
drivers = []
for i, d in session.results.iterrows():
    drivers.append(d["Abbreviation"] + "  " + d["FullName"] + " (" + d["TeamName"] + ")")

print("\nfirst driver?")
d1 = codes[pick(drivers)]

print("\nsecond driver?")
while True:
    d2 = codes[pick(drivers)]
    if d2 != d1:
        break
    print("thats the same driver, pick someone else")

lap1, tel1 = getlap(session, d1)
lap2, tel2 = getlap(session, d2)

time1 = lap1["LapTime"].total_seconds()
time2 = lap2["LapTime"].total_seconds()
print("\n" + d1, round(time1, 3), "s")
print(d2, round(time2, 3), "s")
if time1 < time2:
    print(d1, "was faster by", round(time2 - time1, 3), "s")
else:
    print(d2, "was faster by", round(time1 - time2, 3), "s")

dist = tel1["Distance"].to_numpy()
t1 = tel1["Time"].dt.total_seconds().to_numpy()
t2 = np.interp(dist, tel2["Distance"].to_numpy(), tel2["Time"].dt.total_seconds().to_numpy())
gap = t2 - t1


fig, ax = plt.subplots(4, 1, figsize=(12, 10), sharex=True,
                       gridspec_kw={"height_ratios": [3, 2, 1, 2]})

ax[0].plot(tel1["Distance"], tel1["Speed"], color="red", label=d1)
ax[0].plot(tel2["Distance"], tel2["Speed"], color="orange", label=d2)
ax[0].set_ylabel("Speed (km/h)")
ax[0].legend()

ax[1].plot(tel1["Distance"], tel1["Throttle"], color="red")
ax[1].plot(tel2["Distance"], tel2["Throttle"], color="orange")
ax[1].set_ylabel("Throttle (%)")

ax[2].step(tel1["Distance"], tel1["Brake"].astype(int), where="post", color="red")
ax[2].step(tel2["Distance"], tel2["Brake"].astype(int), where="post", color="orange")
ax[2].set_ylabel("Brake")
ax[2].set_yticks([0, 1])
ax[2].set_yticklabels(["Off", "On"])

ax[3].plot(dist, gap, color="orange")
ax[3].axhline(0, color="red")
ax[3].set_ylabel("Gap to " + d1 + " (s)")
ax[3].set_xlabel("Distance (m)")

for a in ax:
    a.grid(alpha=0.3)

fig.suptitle(d1 + " vs " + d2 + " - " + session.event["EventName"] + " " + str(year) + " " + session.name)
plt.tight_layout()

save = input("\nsave the graph? (y/n)\n").strip().lower()
if save == "y" or save == "yes":
    filename = str(year) + "_" + session.event["EventName"].replace(" ", "_") + "_" + d1 + "_vs_" + d2 + ".png"
    plt.savefig(filename, dpi=200)
    print("saved as", filename)

print("opening graph... (close the window to finish)")
plt.show()