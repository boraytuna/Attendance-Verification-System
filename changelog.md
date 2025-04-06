# Changelog

## [2025-02-17] - Change Summary
### Merged student-side & professor-side databases into one database.
- #### Description:
    - Restructured backend database into a singular database instead of two.
- #### Motivation:
    - The student-side and professor-side, which initially each had their own database, both required information from the other database.
- #### Implications:
    - Makes things easier on the programmers, reduces redundancy, better organized.

### Changed to Google's Geolocation API.
- #### Description:
    - Changed API key to Google's geolocation API which translates longitude and latitude to actual addresses.
- #### Motivation:
    - Wanted a better map visualization (something familiar to people).
- #### Implications:
    - Better user experience, easier and familiar to work with.

## [2025-03-10] - Change Summary
### Changed to student interface front-end to be rendered in a single html template rather than multiple different html templates
- #### Description:
    - The front-end student interface was rendered using multiple html templates (1 per each frame). Changed to using a single html template.
- #### Motivation:
    - Wanted cleaner/better organization on the back-end.
- #### Implications:
    - Easier for developers- all student-interface front-end code within one file.

## [2025-03-17] - Change Summary
### Switched from Python to JavaScript-based geolocation
- #### Description:
  - Implemented real-time student location tracking in the browser via JavaScript APIs instead of using Python-based libraries.
- #### Motivation:
  - Python libraries did not provide sufficient accuracy or real-time tracking when the phone was locked. JavaScript geolocation is more reliable and familiar to users.
- #### Implications:
  - Requires careful handling of browser permissions and background states for continuous tracking. Improves precision and user experience for verifying attendance in real time.


## [2025-04-06] – Change Summary
### Changed
- Refactored attendance verification logic: moved decision-making from backend to professors.
- Removed hardcoded attendance status labels (e.g., "Attended", "Late").
- Professors now receive an email report with:
  - Student names, emails, check-in/out times
  - Official event start/end times
  - Only includes students who checked in and out within 100m of event location.
### Removed
- Dropped deprecated `attendance_status` table
- Cleaned 3 invalid rows from `events` table with missing address and recurrence info.
