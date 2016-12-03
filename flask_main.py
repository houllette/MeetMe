import flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import url_for
import uuid

import json
import logging

#our own processing module
from process import *

# Date handling
import arrow
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services
from apiclient import discovery

# Globals
import CONFIG
import secrets.admin_secrets  # Per-machine secrets
import secrets.client_secrets # Per-application secrets

app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key=CONFIG.secret_key

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = secrets.admin_secrets.google_key_file  ## You'll need this
APPLICATION_NAME = 'MeetMe Class Project'

# Mongo database
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
MONGO_CLIENT_URL = "mongodb://{}:{}@localhost:{}/{}".format(
    secrets.client_secrets.db_user,
    secrets.client_secrets.db_user_pw,
    secrets.admin_secrets.port,
    secrets.client_secrets.db)

# Database connection per server process
try:
    dbclient = MongoClient(MONGO_CLIENT_URL)
    db = getattr(dbclient, secrets.client_secrets.db)
    collection = db.dated
except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)

#############################
#
#  Pages (routed from URLs)
#
#############################

@app.route("/")
@app.route("/index")
def index():
    app.logger.debug("Entering index")
    if 'begin_date' not in flask.session:
      init_session_values()

    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['calendars'] = list_calendars(gcal_service)
    flask.session['db_id'] = str(ObjectId())
    return render_template('index.html')

@app.route("/invite/<db_id>")
def invite(db_id):
    app.logger.debug("Entering invite")
    if 'begin_date' not in flask.session:
      init_session_values()

    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['calendars'] = list_calendars(gcal_service)
    flask.session['db_id'] = db_id
    return render_template('invite.html')

@app.route('/create', methods=['POST'])
def create():
    selected_events = request.form.getlist('conflict')
    flask.g.block_two = flask.session['busytimes']
    chunk = condense_busytimes(list_blocking(selected_events, flask.session['busytimes']))
    collection.insert({'_id': flask.session['db_id'], 'data': {
    'start_date': flask.session['start_date'],
    'end_date': flask.session['end_date'],
    'start_time': flask.session['start_time'],
    'end_time': flask.session['end_time'],
    'busytime_chunk': chunk
    }})
    return flask.redirect(flask.url_for('calendar', db_id=flask.session['db_id']))

@app.route('/submit', methods=['POST'])
def submit():
    selected_events = request.form.getlist('conflict')
    flask.g.block_two = flask.session['busytimes']
    chunk = condense_busytimes(list_blocking(selected_events, flask.session['busytimes']))
    #FIXME: pull from database current value and call condense_busytimes on chunk, will need tweaking
    collection.insert({'_id': flask.session['db_id'], 'data': {
    'start_date': flask.session['start_date'],
    'end_date': flask.session['end_date'],
    'start_time': flask.session['start_time'],
    'end_time': flask.session['end_time'],
    'busytime_chunk': updated_chunk
    }})
    return flask.redirect(flask.url_for('calendar', db_id=flask.session['db_id']))

@app.route('/calendar/<db_id>')
def calendar(db_id):
    app.logger.debug("Entering display of calendar")
    record = collection.find( { "_id": db_id } )
    for doc in record:
        app.logger.debug(doc)
    #FIXME: Should pull from the database using the unique ID given to this
    #function to retrieve stored busytimes and display formatted calendar

    #chunk = retrieved value from database
    #free should be calculated using the "communal chunk of busytimes"
    #flask.g.free_time = free_time(chunk, flask.session['start_time'], flask.session['end_time'], flask.session['daterange'].split())

    #free_times and busy times should be sent back via ajax (easiest for making it look nice)
    #or just use flask.g variables and use jinja2 (have to figure that out to make it look nice but easiest to backend code)
    return render_template('calendar.html')


###############
# AJAX request handlers
#   These return JSON, rather than rendering pages.
###############

@app.route("/_example")
def example():
    """
    Example ajax request handler
    """
    app.logger.debug("Got a JSON request");
    rslt = { "key": "value" }
    return jsonify(result=rslt)

@app.route("/_setrange")
def setrange():
    app.logger.debug("Entering setrange")
    start_date = interpret_date(request.args.get("start_date", type=str))
    end_date = interpret_date(request.args.get("end_date", type=str))
    if start_date < end_date:
        flask.session["start_date"] = start_date
        flask.session["end_date"] = next_day(end_date)
    else:
        flask.session["start_date"] = end_date
        flask.session["end_date"] = next_day(start_date)

    start_time = interpret_time(request.args.get("start_time", type=str))
    end_time = interpret_time(request.args.get("end_time", type=str))
    if start_time < end_time:
        flask.session["start_time"] = start_time
        flask.session["end_time"] = end_time
    else:
        flask.session["start_time"] = end_time
        flask.session["end_time"] = start_time
    app.logger.debug(flask.session['start_date'])
    app.logger.debug(flask.session['end_date'])
    rslt = flask.session['calendars']
    return jsonify(result=rslt)

@app.route("/_setcalendar")
def setcalendar():
    app.logger.debug("Entering setcalendar")
    selected_calendars = request.args.get("selected_calendars", type=str).split(',')
    print(selected_calendars)
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['busytimes'] = conflicting_events(list_events(gcal_service, selected_calendars, flask.session['start_date'], flask.session['end_date']), flask.session['start_time'], flask.session['end_time'])
    rslt = flask.session['busytimes']
    return jsonify(result=rslt)


##################################
#
#  Google Calendar Authorization
#
##################################

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value.
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /index *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
  else:
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    app.logger.debug("Got credentials")
    return flask.redirect(flask.url_for('index'))

#################################
#
#  Initialize session variables
#
#################################

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main.
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')     # We really should be using tz from browser
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["start_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 8 to 5
    flask.session["start_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    if text == '':
        text = '12:00am' #just to catch an empty request
    try:
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        as_arrow = as_arrow.replace(year=2016) #HACK see below
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()
    #HACK #Workaround
    # isoformat() on raspberry Pi does not work for some dates
    # far from now.  It will fail with an overflow from time stamp out
    # of range while checking for daylight savings time.  Workaround is
    # to force the date-time combination into the year 2016, which seems to
    # get the timestamp into a reasonable range. This workaround should be
    # removed when Arrow or Dateutil.tz is fixed.
    # FIXME: Remove the workaround when arrow is fixed (but only after testing
    # on raspberry Pi --- failure is likely due to 32-bit integers on that platform)


def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
        if text[4] == '-':
            as_arrow = arrow.get(text).replace(tzinfo=tz.tzlocal())
        else:
            as_arrow = arrow.get(text, "MM/DD/YYYY").replace(tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

#######################################################
#
#  Functions (NOT pages) that return some information
#
#######################################################

def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal:
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]

        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)

def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])

###################

if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running under green unicorn)
  app.run(port=CONFIG.PORT,host="0.0.0.0")