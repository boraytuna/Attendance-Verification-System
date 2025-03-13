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