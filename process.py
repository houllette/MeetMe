import arrow
import datetime

def list_events(service, selected_calendars, user_defined_begin_date, user_defined_end_date):
    """
    Given a google 'service' object and list of selected calendars, return a list of
    events from the selected calendars within the submitted date range.
    Each event is represented by a dict.
    """
    page_token = None
    result = [ ]
    for cal_id in selected_calendars:
        while True:
          events_list = service.events().list(calendarId=cal_id, pageToken=page_token, timeMin=user_defined_begin_date, timeMax=user_defined_end_date).execute()
          for event in events_list["items"]:
            if "summary" in event:
                if 'transparency' not in event:
                    if 'description' in event:
                        desc = event['description']
                    else:
                        desc = '(no description)'

                    if 'date' in event['start']:
                        start_date = "ALL DAY"
                        output_start_time = start_date
                    else:
                        start_date = event['start']['dateTime']
                        output_start_time = start_date.split('T')[1][0:5]

                    if 'date' in event['end']:
                        end_date = "ALL DAY"
                        output_end_time = end_date
                    else:
                        end_date = event['end']['dateTime']
                        output_end_time = end_date.split('T')[1][0:5]

                    if start_date.split('T')[0] != end_date.split('T')[0]:
                        output_date = start_date.split('T')[0] + " - " + end_date.split('T')[0]
                    else:
                        output_date = start_date.split('T')[0]

                    result.append({
                    'id': event['id'],
                    'summary': event['summary'],
                    'desc': desc,
                    'start_date': start_date,
                    'end_date': end_date,
                    'output_start_time': output_start_time,
                    'output_end_time': output_end_time,
                    'output_date': output_date
                    })
          page_token = events_list.get("nextPageToken")
          if not page_token:
            break
    return result

def conflicting_events(events, user_defined_begin_time, user_defined_end_time):
    '''
    Given a list of events, checks against user inputted time frame
    and returns list of events that fall between the requested time frame
    '''
    conflict = [ ]
    for event in events:
        if event['start_date'] == "ALL DAY" or event['end_date'] == "ALL DAY":
            conflict.append(event)
        else:
            event_start = arrow.get(event['start_date'].split('T')[1][0:8], 'HH:mm:ss')
            event_end = arrow.get(event['end_date'].split('T')[1][0:8], 'HH:mm:ss')
            request_start = arrow.get(user_defined_begin_time.split('T')[1][0:8], 'HH:mm:ss')
            request_end = arrow.get(user_defined_end_time.split('T')[1][0:8], 'HH:mm:ss')
            #starts within pre-existing event
            if event_start < request_start and request_start < event_end:
                conflict.append(event)
            #ends within pre-existing event
            elif event_start < request_end and request_end < event_end:
                conflict.append(event)
            #pre-existing event happens within request
            elif request_start < event_start and event_end < request_end:
                conflict.append(event)
    return conflict

def list_blocking(selected_event_ids, blocking_events_list):
    result = [ ]
    for event_id in selected_event_ids:
        for event in blocking_events_list:
            if event['id'] == event_id:
                result.append(event)
    return result

def condense_busytimes(events):
    condensed = [ ]
    current_date = ''
    current_start_time = ''
    current_end_time = ''
    for event in events:
        event_start = arrow.get(event['start_date'].split('T')[1][0:8], 'HH:mm:ss')
        event_end = arrow.get(event['end_date'].split('T')[1][0:8], 'HH:mm:ss')
        if event['start_date'] == "ALL DAY" or event['end_date'] == "ALL DAY":
            condensed.append({
            'date': event['output_date'],
            'start_time': 'ALL DAY',
            'end_time': 'ALL DAY'
            })
        else:
            if current_date == '': #first run through
                current_date = event['output_date']
                current_start_time = event_start
                current_end_time = event_end
            elif event['output_date'] != current_date: #new day, so new chunk of time
                #append what we have
                condensed.append({
                'date': current_date,
                'start_time': current_start_time,
                'end_time': current_end_time
                })
                current_date = event['output_date']
                current_start_time = event_start
                current_end_time = event_end
            else: #not a new day
                if event_start < current_start_time and current_start_time <= event_end:
                    current_start_time = event_start
                    if current_end_time < event_end:
                        current_end_time = event_end
                elif current_start_time < event_start and event_start <= current_end_time and current_end_time < event_end:
                    current_end_time = event_end
                elif current_start_time < event_start and event_end < current_end_time:
                    continue
                else:
                    #append what we have
                    condensed.append({
                    'date': current_date,
                    'start_time': current_start_time,
                    'end_time': current_end_time
                    })
                    current_date = event['output_date']
                    current_start_time = event_start
                    current_end_time = event_end
    condensed.append({
    'date': current_date,
    'start_time': current_start_time,
    'end_time': current_end_time
    })
    return condensed

def free_time(busytimes, user_defined_begin_time, user_defined_end_time, daterange):
    '''
    Given a list of busytimes, generates a list of free times that fall between
    the time frame and returns the list
    '''
    free_times = [ ]
    start_time = arrow.get(user_defined_begin_time.split('T')[1][0:8], 'HH:mm:ss')
    end_time = arrow.get(user_defined_end_time.split('T')[1][0:8], 'HH:mm:ss')
    current_date = '' #used in the loop
    current_start_time = '' #used in the loop
    for busytime in busytimes:
        if busytime['start_time'] == "ALL DAY" or busytime['end_time'] == "ALL DAY":
            continue
        if busytime['date'] == '' and busytime['start_time'] == '' and busytime['end_time'] == '':
            continue

        if busytime['date'] != current_date: #first event for a day
            if current_start_time != '': #this is for a free_time block that may have been started due to time left over after previous day's last event
                free_times.append({
                'date': current_date,
                'start_time': current_start_time,
                'end_time': end_time,
                'output_start_time': str(current_start_time).split('T')[1][0:5],
                'output_end_time': str(end_time).split('T')[1][0:5]
                })

            current_date = busytime['date'] #reset so this doesnt happen again
            if start_time < busytime['start_time']: #if there is some time before our first busytime
                free_times.append({
                'date': current_date,
                'start_time': start_time,
                'end_time': busytime['start_time'],
                'output_start_time': str(start_time).split('T')[1][0:5],
                'output_end_time': str(busytime['start_time']).split('T')[1][0:5]
                })
                if busytime['end_time'] < end_time:
                    current_start_time = busytime['end_time']
            else: #if there isnt any free time before first busytime
                if busytime['end_time'] <= end_time: #check to make sure busytime isnt taking up entirity of our request range (and isnt marked all day i.e. request is from 9-12 and we have busytime from 8-1)
                    current_start_time = busytime['end_time'] #start a new incomplete free_time block w/ counters outside of loop
        else: #if the busytime currently being evaluated is within the same day as the last busytime.
            if end_time <= busytime['start_time']: #closes free_time block if the next busytime is outside request range
                free_times.append({
                'date': current_date,
                'start_time': current_start_time,
                'end_time': end_time,
                'output_start_time': str(current_start_time).split('T')[1][0:5],
                'output_end_time': str(end_time).split('T')[1][0:5]
                })
                current_start_time = ''
            else:
                free_times.append({
                'date': current_date,
                'start_time': current_start_time,
                'end_time': busytime['start_time'],
                'output_start_time': str(current_start_time).split('T')[1][0:5],
                'output_end_time': str(busytime['start_time']).split('T')[1][0:5]
                })
                current_start_time = ''

            if busytime['end_time'] <= end_time: #if there is time after last busytime
                current_start_time = busytime['end_time']

    if current_start_time != '': #this is for a free_time block that may have been started due to time left over after previous day's last event
        free_times.append({
        'date': current_date,
        'start_time': current_start_time,
        'end_time': end_time,
        'output_start_time': str(current_start_time).split('T')[1][0:5],
        'output_end_time': str(end_time).split('T')[1][0:5]
        })

    end = datetime.datetime.strptime(daterange[2], "%m/%d/%Y").date()
    begin = datetime.datetime.strptime(daterange[0], "%m/%d/%Y").date()
    delta = end-begin
    date_list = [str(end - datetime.timedelta(days=x)) for x in range(0, delta.days+1)]
    date_used = { }
    for date in date_list:
        date_used[date] = False

    for date in date_list:
        for free_time in free_times:
            if date == free_time['date']:
                date_used[date] = True
        if date_used[date] == False:
            free_times.append({
            'date': date,
            start_time: start_time,
            end_time: end_time,
            'output_start_time': str(start_time).split('T')[1][0:5],
            'output_end_time': str(end_time).split('T')[1][0:5]
            })


    return free_times