##
## SLTrack.py
## (c) 2019 Andrew Stokes  All Rights Reserved
## Taken from https://www.space-track.org/documentation#howto-api_python
##
##
## Simple Python app to extract Starlink satellite history data from www.space-track.org into a spreadsheet
## (Note action for you in the code below, to set up a config file with your access and output details)
##
##
##  Copyright Notice:
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  For full licencing terms, please refer to the GNU General Public License
##  (gpl-3_0.txt) distributed with this release, or see
##  http://www.gnu.org/licenses/.
##

import requests
import configparser


class MyError(Exception):
    def __init___(self, args):
        Exception.__init__(self,"my exception was raised with arguments {0}".format(args))
        self.args = args


# See https://www.space-track.org/documentation for details on REST queries

uriBase = "https://www.space-track.org"
requestLogin = "/ajaxauth/login"
requestCmdAction = "/basicspacedata/query"


# Use configparser package to pull in the ini file (pip install configparser)
config = configparser.ConfigParser()
config.read("./SLTrack.ini")
configUsr = config.get("configuration", "username")
configPwd = config.get("configuration", "password")
siteCred = {'identity': configUsr, 'password': configPwd}


def space_track_api_request(start, end, norad_ids):
    """
    Return Three line elements from SpaceTrack, using their API access.

    :param start: [str] start date of TLE data, in the format "YYYY-MM-DD"
    :param end:  [str] end date of TLE data, in the format "YYYY-MM-DD"
    :param norad_ids: [str] String containing the Norad IDs of satellites (comma-sep.)
    :return:
    """
    # norad_ids = str(norad_ids).strip("[]").replace(" ", "")
    request_ = f"/class/gp_history/NORAD_CAT_ID/{norad_ids}/orderby/TLE_LINE1 ASC/EPOCH/{start}--{end}/format/3le"

    # use requests package to drive the RESTful session with space-track.org
    with requests.Session() as session:
        # run the session in a with block to force session to close if we exit

        # need to log in first. note that we get a 200 to say the website got the data,
        # not that we are logged in
        resp = session.post(uriBase + requestLogin, data=siteCred)
        if resp.status_code != 200:
            raise MyError(resp, "POST fail on login")

        # this query picks up all satellites from the catalog. Note - a 401
        # failure shows you have bad credentials
        resp = session.get(uriBase + requestCmdAction + request_)
        if resp.status_code != 200:
            print(resp)
            raise MyError(resp, "GET fail on request for satellites")

        return resp


print("Completed TLE request session")


if __name__ == "__main__":
    start = "2023-03-01"
    end = "2023-03-02"
    name = "FLOCK"