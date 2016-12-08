import arrow
import datetime
from dateutil import tz  # For interpreting local times

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
          events_list = service.events().list(calendarId=cal_id, singleEvents=True, orderBy="startTime", pageToken=page_token, timeMin=user_defined_begin_date, timeMax=user_defined_end_date).execute()
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
                    'start_time': start_date,
                    'end_time': end_date,
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
            if event_start <= request_start and request_start < event_end:
                conflict.append(event)
            #ends within pre-existing event
            elif event_start < request_end and request_end < event_end:
                conflict.append(event)
            #pre-existing event happens within request
            elif request_start < event_start and event_end < request_end:
                conflict.append(event)
    return conflict

def list_blocking(selected_event_ids, blocking_events_list):
    '''
    Returns list of events that conflict that the user has selected cannot be moved
    '''
    result = [ ]
    for event_id in selected_event_ids:
        for event in blocking_events_list:
            if event['id'] == event_id:
                result.append(event)
    return result

def sort_busytimes(busytimes):
    '''
    Given a list of busytimes, returns list of busytimes in order of time,
    this will result in the same list for creation, but made for when other
    add their busytimes
    '''
    sorted_busytimes = []
    partial_sorted = []
    current_date = ''
    for busytime in busytimes:
        if busytime['date'] == '' and busytime['start_time'] == '' and busytime['end_time'] == '':
            continue

        if busytime['date'] == '':
            current_date = busytime['date']
            partial_sorted.append(busytime)
        elif busytime['date'] != current_date:
            sorted_busytimes += sorted(partial_sorted, key=lambda k: k['start_time'])
            partial_sorted = [ ]
            current_date = busytime['date']
            partial_sorted.append(busytime)
        else:
            partial_sorted.append(busytime)
    sorted_busytimes += sorted(partial_sorted, key=lambda k: k['start_time'])
    return sorted_busytimes

def combine(main_busytime_list, merging_list):
    """
    given two lists of busytimes, returns list of busytimes that have events of the same day together
    """
    merged = [ ]
    days = { }
    current_date = ''
    #this creates the dates dict
    for busytime in main_busytime_list:
        if busytime['date'] == '':
            days[busytime['date']] = [ ]
            days[busytime['date']].append(busytime)
            print("APPEND 1"+str(busytime)+"\n\n")
        else:
            if busytime['date'] != current_date:
                days[busytime['date']] = [ ]
                days[busytime['date']].append(busytime)
                current_date = busytime['date']
                print("APPEND 2"+str(busytime)+"\n\n")
            else:
                days[busytime['date']].append(busytime)
                print("APPEND 3"+str(busytime)+"\n\n")
    print("DAYS FROM CREATION "+str(days)+"\n\n")
    for busytime in merging_list:
        if busytime['date'] in days:
            days[busytime['date']].append(busytime)
            print("APPEND 4"+str(busytime)+"\n\n")
        else:
            days[busytime['date']] = [ ]
            days[busytime['date']].append(busytime)
            print("APPEND 5"+str(busytime)+"\n\n")
    for day in days:
        print("DAY TOTAL: "+str(days[day])+"\n\n")
        merged += days[day]
    print("MERGED "+str(merged)+"\n\n")
    return merged

def condense(busytimes):
    condensed = [ ]
    flagged = [ ]
    print(str(busytimes))
    for time in busytimes:
        print("\ntime\n"+str(time)+"\n\n")
        if len(flagged) == 0 or time not in flagged:
            chunk_start = arrow.get(time['start_time'])
            chunk_end = arrow.get(time['end_time'])
            for compare in busytimes:
                print("\ncompare\n"+str(compare)+"\n\n")
                compare_start = arrow.get(compare['start_time'])
                compare_end = arrow.get(compare['end_time'])
                if chunk_start <= compare_start and compare_start <= chunk_end and chunk_end <= compare_end:
                    chunk_end = compare_end
                    print("\nremoving 1\n"+str(compare)+"\n\n")
                    print("current chunk\n"+str(chunk_start)+"\n"+str(chunk_end)+"\n\n")
                    #busytimes.remove(compare)
                    flagged.append(compare)
                elif compare_start <= chunk_start and chunk_start <= compare_end and compare_end <= chunk_end:
                    chunk_start = compare_start
                    print("\nremoving 2\n"+str(compare)+"\n\n")
                    print("current chunk\n"+str(chunk_start)+"\n"+str(chunk_end)+"\n\n")
                    #busytimes.remove(compare)
                    flagged.append(compare)
                elif chunk_start <= compare_start and compare_end <= chunk_end:
                    print("\nremoving 3\n"+str(compare)+"\n\n")
                    print("current chunk\n"+str(chunk_start)+"\n"+str(chunk_end)+"\n\n")
                    #busytimes.remove(compare)
                    flagged.append(compare)
                elif compare_start <= chunk_start and chunk_end <= compare_end:
                    chunk_start = compare_start
                    chunk_end = compare_end
                    print("\nremoving 4\n"+str(compare)+"\n\n")
                    print("current chunk\n"+str(chunk_start)+"\n"+str(chunk_end)+"\n\n")
                    #busytimes.remove(compare)
                    flagged.append(compare)
            print("about to add current chunk\n"+str(chunk_start)+"\n"+str(chunk_end)+"\n\n")
            condensed.append({
            'date': chunk_start.isoformat().split("T")[0],
            'start_time': chunk_start.isoformat(),
            'end_time': chunk_end.isoformat(),
            })
    print("condensed "+str(condensed))
    return condensed

def freetime(busytimes, start_time, end_time, daterange):
    free_times = [ ]
    start_time = arrow.get(start_time)
    end_time = arrow.get(end_time)

    end = datetime.datetime.strptime(daterange[1].split('T')[0], "%Y-%m-%d").date()
    begin = datetime.datetime.strptime(daterange[0].split('T')[0], "%Y-%m-%d").date()
    delta = end-begin
    date_list = [str(end - datetime.timedelta(days=x)) for x in range(0, delta.days+1)]

    days = { }
    current_date = ''
    #this creates the dates dict
    for busytime in sort_busytimes(busytimes):
        if busytime['date'] == '':
            days[busytime['date']] = [ ]
            days[busytime['date']].append(busytime)
        else:
            if busytime['date'] != current_date:
                days[busytime['date']] = [ ]
                days[busytime['date']].append(busytime)
                current_date = busytime['date']
            else:
                days[busytime['date']].append(busytime)
    date_list.reverse()
    for date in date_list:
        print(date)
        display = True
        chunk_start = start_time
        chunk_end = end_time
        if date in days:
            for busytime in days[date]:
                print(str(busytime))
                busy_start = arrow.get(busytime['start_time'].split('T')[1][0:8], 'HH:mm:ss').replace(year=2016, tzinfo=tz.tzlocal())
                busy_end = arrow.get(busytime['end_time'].split('T')[1][0:8], 'HH:mm:ss').replace(year=2016, tzinfo=tz.tzlocal())
                print("busy start "+busy_start.isoformat())
                print("busy_end "+busy_end.isoformat())
                print("chunk start "+chunk_start.isoformat())
                print("chunk_end "+chunk_end.isoformat()+"\n\n")
                if busy_start <= chunk_start and chunk_end <= busy_end:
                    display = False
                    break
                elif busy_start <= chunk_start and chunk_start <= busy_end and busy_end <= chunk_end:
                    chunk_start = busy_end
                    print("\nchunk started\n\n")
                elif busy_start <= chunk_end and chunk_end <= busy_end: # and busy_start <= chunk_start:
                    chunk_end = busy_start
                    print("\nchunk closed\n\n")
                elif chunk_start <= busy_start and busy_end <= chunk_end:
                    chunk_end = busy_start
                    print("\nchunk appending\n\n")
                    free_times.append({
                    'date': date,
                    'start_time': chunk_start.isoformat(),
                    'end_time': chunk_end.isoformat()
                    })
                    chunk_start = busy_end
                    chunk_end = end_time
        else:
            pass
        if display:
            free_times.append({
            'date': date,
            'start_time': chunk_start.isoformat(),
            'end_time': chunk_end.isoformat()
            })

    return free_times