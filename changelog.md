# Changelog

## [2025-02-17] - Change Summary
### Merged student-side & professor-side databases into one database.
- #### Description:
    - Restructured backend database into a singular database instead of two.
- #### Motivation:
    - The student-side and professor-side, which initially each had their own database, both required information from the other database.
- #### Implications:
    - Makes things easier on the programmers, reduces redundancy, better organized

### Changed to Google's Geolocation API.
- #### Description:
    - Changed API key to Google's geolocation API which translates longitude and latitude to actual addresses.
- #### Motivation:
    - Wanted a better map visualization (something familiar to people)
- #### Implications:
    - Better user experience, easier and familiar to work with