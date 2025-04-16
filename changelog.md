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
### Changed how student location at an event is recorded.
- #### Description:
    - Instead of periodically monitoring the student’s location during the event, a check-in time & location and a check-out time & location will be captured at the start and end of the event (through the check-in form).
- #### Motivation:
    - iOS Safari kills background JavaScript unless the webpage executing the JavaScript is frontmost and Safari is actually active. Safari does not remain active when the device is asleep. iPhones are a popular phone choice so our system would exclude a great number of students if we depended on a background JS script to verify attendance.
- #### Implications:
    - Less invasive attendance verification. Also reduces student device battery & resource consumption.
    - Simplifies backend logic.

### Refactored the student attendance verification logic.
- #### Description:
    - Instead of the system deciding on an attendance status for the student (e.g., “Attended”, “Late”), the email report will provide the professor with the student’s check-in and check-out times, along with the event’s official start and end times. The report will include only students who checked in and out within 100m of the official event location.
- #### Motivation:
    - There were a multitude of variables we felt we needed to consider and safeguard against (e.g., late arrival, event ending early) for the system to handle, fully, the attendance verification logic.
- #### Implications:
    - Simplifies backend logic. Offloads attendance verification responsibility from the system to the professor.
    - `attendance_status` table is system database is now deprecated.

### Improved the student check-in process to support multiple courses and professors.
- #### Description:
    - Students may now check-in to an event for multiple courses through the check-in form. Previously, they could only check-in for one course.
- #### Motivation:
    - Feedback from Nathan & Kayla.
    - If students are enrolled in more than one course requiring them to attend an event, they are likely to want to use one event to receive credit in both.
- #### Implications:
    - Improves the user experience by eliminating redundancy.
    - Theoretically reduces network traffic and load on the system. Instead of handling multiple separate POST requests for a student checking in for multiple courses, the system only needs to handle one.
    - Slight adjustments to backend logic. Does not overcomplicate things, though.

## [2025-04-16] – Change Summary
### Improved the event-creation process to support recurring events.
- #### Description:
    - Admins/Professor may now create events that repeat on a schedule (e.g, weekly, monthly).
- #### Motivation:
    - Feedback from Nathan & Kayla.
- #### Implications:
    - Improves the user experience.
    - Slightly increases complexity of backend logic.
    - Requires more careful consideration of the QR code generation logic.