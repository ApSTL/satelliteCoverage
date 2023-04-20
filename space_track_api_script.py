##
## SLTrack.py
## (c) 2019 Andrew Stokes  All Rights Reserved
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
import xlsxwriter
from datetime import datetime


class MyError(Exception):
    def __init___(self, args):
        Exception.__init__(self,"my exception was raised with arguments {0}".format(args))
        self.args = args


# See https://www.space-track.org/documentation for details on REST queries

uriBase = "https://www.space-track.org"
requestLogin = "/ajaxauth/login"
requestCmdAction = "/basicspacedata/query"
# requestOMMStarlink1 = "/class/omm/NORAD_CAT_ID/"
# requestOMMStarlink2 = "/orderby/EPOCH%20asc/format/json"

# Parameters to derive apoapsis and periapsis from mean motion (see https://en.wikipedia.org/wiki/Mean_motion)

# GM = 398600441800000.0
# GM13 = GM ** (1.0/3.0)
# MRAD = 6378.137
# PI = 3.14159265358979
# TPI86 = 2.0 * PI / 86400.0

# ACTION REQUIRED FOR YOU:
#=========================
# Provide a config file in the same directory as this file, called SLTrack.ini, with this format (without the # signs)
# [configuration]
# username = XXX
# password = YYY
# output = ZZZ
#
# ... where XXX and YYY are your www.space-track.org credentials (https://www.space-track.org/auth/createAccount for free account)
# ... and ZZZ is your Excel Output file - e.g. starlink-track.xlsx (note: make it an .xlsx file)

# Use configparser package to pull in the ini file (pip install configparser)
config = configparser.ConfigParser()
config.read("./SLTrack.ini")
configUsr = config.get("configuration", "username")
configPwd = config.get("configuration", "password")
# configOut = config.get("configuration", "output")
siteCred = {'identity': configUsr, 'password': configPwd}

# User xlsxwriter package to write the xlsx file (pip install xlsxwriter)
# workbook = xlsxwriter.Workbook(configOut)
# worksheet = workbook.add_worksheet()
# z0_format = workbook.add_format({'num_format': '#,##0'})
# z1_format = workbook.add_format({'num_format': '#,##0.0'})
# z2_format = workbook.add_format({'num_format': '#,##0.00'})
# z3_format = workbook.add_format({'num_format': '#,##0.000'})
#
# # write the headers on the spreadsheet
# now = datetime.now()
# nowStr = now.strftime("%m/%d/%Y %H:%M:%S")
# worksheet.write('A1', 'Starlink data from' + uriBase + " on " + nowStr)
# worksheet.write('A3','NORAD_CAT_ID')
# worksheet.write('B3','SATNAME')
# worksheet.write('C3','EPOCH')
# worksheet.write('D3','Orb')
# worksheet.write('E3','Inc')
# worksheet.write('F3','Ecc')
# worksheet.write('G3','MnM')
# worksheet.write('H3','ApA')
# worksheet.write('I3','PeA')
# worksheet.write('J3','AvA')
# worksheet.write('K3','LAN')
# worksheet.write('L3','AgP')
# worksheet.write('M3','MnA')
# worksheet.write('N3','SMa')
# worksheet.write('O3','T')
# worksheet.write('P3','Vel')
# wsline = 3


def space_track_api_request(start, end, norad_id):
    request_ = f"/class/gp_history/NORAD_CAT_ID/{norad_id}/orderby/TLE_LINE1 " \
                           f"ASC/EPOCH/{start}--{end}/format/3le"

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
            raise MyError(resp, "GET fail on request for Starlink satellites")

        # Write the retrieved TLE data to a text file
        with open("planet_tle.txt", "w", newline="") as text_file:
            text_file.write(resp.text)

print("Completed session")
