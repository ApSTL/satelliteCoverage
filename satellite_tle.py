from skyfield.api import load


# Fetch the latest TLEs for all of Planet's satellites
planet_url = "http://celestrak.com/NORAD/elements/planet.txt"
satellites = load.tle_file(planet_url)

platforms = {"FLOCK": "flock_ids.txt", "SKYSAT": "skysat_ids.txt"}

for platform, file_ in platforms:
	with open(file_, "a") as filename:
		for s in satellites:
			if platform not in s.name:
				continue
			filename.write(str(s.model.satnum) + ',')
