The data-fetching backend of this project expects the data to come from a google sheet.
To set this up, do the following:
1. Go to https://console.cloud.google.com/
2. In the search bar, write: Create a project, and click it
3. Click: APIs and services
4. Click: Enable APIs and services
5. search for: Google Sheets API, click it and then click Enable
6. Click: Credentials
7. Click: Create credentials, then click: Service account
8. Name it and then click: Done
9. A generated e-mail will be listed under Service Accounts, click it
10. Click: Keys
11. Click: Add Keys, and then click: Create new key, choose JSON
12. Move the file that's downloaded to the root directory of this project
13. Rename this file to: client_secret.json
14. Copy the e-mail from step 9. (click Service Accounts to see it again, or copy it from client_secret.json -from the field called client_email)
15. Open the Google spreadsheet that contains the data
16. In the Google spreadsheet, click: Share
17. In the entry-field, paste the copied e-mail address from 14.
18. Untick: Notify people, then click: Share
19. Create a file called: key.txt
20. In key.txt, enter the spreadsheet_id that appears in the web URL to the spreadsheet for example if the URL is:
    https://docs.google.com/spreadsheets/d/123_abc/edit?gid=0#gid=0
    then the spreadsheet_id is 123_abc

If the requirements have been installed and the data is on the form mentioned below, then main.py can just be run.
Column 1: Dates of the format DD/MM, e.g. 1/7 (1st of June), 21/8 (21st of August), 1/12 (1st of December), 23/12 (23rd of December)
          Years are indicated in this column as a single entry, e.g. 2024, all other columns of such rows should be empty
          The most recent dates should be at the top of the spreadsheet
Column 2: Weight, in units of kg
Column 3: Waist circumference in units of cm
Column 4: Body fat in units of %
Column 5: Body fat in units of kg
Column 6: Hydration in units of %
Column 7: Activity (Text input)
Column 8: Notes (Text input)

To make adjustments to the input data, these should be made in the function called get_data in backend.py.