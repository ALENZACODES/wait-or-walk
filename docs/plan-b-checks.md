# Plan B journeys checked by hand against the TTC schedule

Source: TTC Routes and Schedules (GTFS), City of Toronto Open Data, schedule dated Oct 20, 2026. Each check reads the raw schedule files, not the app data, and shows one scheduled weekday morning trip (Monday to Friday service, effective Nov 1, 2026). Checked Nov 15, 2026, and each journey is also an automated test in tests/test_logic.mjs. These are schedule checks only; the app has not been tested with riders.

## Union to College: route 97 northbound (Line 1, direct)

- Headsign in the schedule: North, 97C Yonge towards Eglinton Station
- Trip 50977894: board at Front St West at Bay St (151 m from Union station) at 7:32:00, get off at Yonge St at Carlton St North Side, College Station (113 m from College station) at 7:45:15, 10 stops later
- Stops in between: Bay St at Wellington St West; Bay St at King St West; Yonge St at King St East; Yonge St at Richmond St East; Yonge St at Queen St East, Queen Station; Yonge St at Shuter St; Yonge St at Dundas St East, TMU Station; Yonge St at Elm St and more
- Result: the schedule confirms this route runs from Union towards College in this direction. Matches what the app shows.

## Finch to Eglinton: route 97 southbound (Line 1, direct)

- Headsign in the schedule: South, 97B Yonge towards St Clair Station via Yonge Blvd
- Trip 50977787: board at Yonge St at Finch Ave West, Finch Station (65 m from Finch station) at 7:51:51, get off at 2190 Yonge St (71 m from Eglinton station) at 8:29:45, 30 stops later
- Stops in between: Yonge St at Kempford Blvd; Yonge St at Churchill Ave; Yonge St at Ellerslie Ave; Yonge St at Park Home Ave; Yonge St at North York Blvd; Yonge St at Elmhurst Ave; Yonge St at Sheppard Ave West, Sheppard Station; Yonge St at Florence Ave and more
- Result: the schedule confirms this route runs from Finch towards Eglinton in this direction. Matches what the app shows.

## Kipling to Jane: route 149 eastbound (Line 2, direct)

- Headsign in the schedule: East, 149 Etobicoke-Bloor towards Jane Station
- Trip 50947754: board at Kipling Station (12 m from Kipling station) at 7:35:00, get off at Jane Station (27 m from Jane station) at 7:55:00, 12 stops later
- Stops in between: Bloor St West at Resurrection Rd; Bloor St West at Green Lanes East Side; Bloor St West at Islington Ave; Bloor St West at Eagle Rd East Side; Bloor St West at Thompson Ave West Side; Bloor St West at Royal York Rd; Bloor St West at Prince Edward Dr South; Bloor St West at The Kingsway and more
- Result: the schedule confirms this route runs from Kipling towards Jane in this direction. Matches what the app shows.

## Main Street to Broadview: route 62 westbound (Line 2, direct)

- Headsign in the schedule: West, 62 Mortimer towards Broadview Station
- Trip 50965887: board at Main Street Station (25 m from Main Street station) at 7:31:00, get off at Broadview Station (73 m from Broadview station) at 7:53:00, 26 stops later
- Stops in between: Doncaster Ave at Main St West Side; Chisholm Ave at Orley Ave; Chisholm Ave at Lumsden Ave; Lumsden Ave at Westlake Ave; Lumsden Ave at Gledhill Ave; Mortimer Ave at Woodbine Ave West Side; Mortimer Ave at Woodmount Ave; Mortimer Ave at Glebemount Ave and more
- Result: the schedule confirms this route runs from Main Street towards Broadview in this direction. Matches what the app shows.

## Dundas West to Union: route 504 eastbound (Line 2 to Line 1: ride past the delay, change at St Andrew for Union)

- Headsign in the schedule: East, 504 King towards Broadview Station
- Trip 50960008: board at Dundas West Station (134 m from Dundas West station) at 7:30:00, get off at King St West at York St, St Andrew Station (90 m from St Andrew station) at 8:18:54, 30 stops later
- Stops in between: Roncesvalles Ave at Boustead Ave South Side; Roncesvalles Ave at Howard Park Ave South Side; Roncesvalles Ave at Grenadier Rd; Roncesvalles Ave at High Park Blvd South Side; Roncesvalles Ave at Galley Ave; Roncesvalles Ave at Marion St South Side; Roncesvalles Ave at Queen St West; Queen St West at Roncesvalles Ave East Side and more
- Result: the schedule confirms this route runs from Dundas West towards St Andrew in this direction. Matches what the app shows.

