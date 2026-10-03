/* ================= CONFIG: Google Drive import =================
   GOOGLE_CLIENT_ID and GOOGLE_API_KEY enable "From Google Drive" in the + menu.
   If they are emptied, the option only shows a "not set up yet" message.
   Google Cloud setup: enable "Google Drive API" + "Google Picker API"; OAuth client type "Web application" with
   Authorized JavaScript origins https://anthonyjonesdavid-cmyk.github.io (+ http://localhost:8823 for local testing)
   Authorized redirect URI       https://anthonyjonesdavid-cmyk.github.io/cr-e7db3ac20e09/   (fallback sign-in for the Home Screen app) */
const GOOGLE_CLIENT_ID = '183934120007-49hgfavrkltjo02tr78tmn08mb7g3v3r.apps.googleusercontent.com';
const GOOGLE_API_KEY   = 'AIzaSyCsbQ40mGeh2FYmlrdK7i28MQvuxCEKRNs';  // browser API key (restrict it to the Picker API + referrer https://anthonyjonesdavid-cmyk.github.io/*)
const GOOGLE_APP_ID    = '183934120007';  // Cloud project NUMBER (Picker setAppId)
const DRIVE_FOLDER_IMPORT = true;     // true = drive.readonly scope (as configured in the consent screen) + whole folders can be picked; false = drive.file, files only
// Default Drive folder: the Picker opens here and "Import Entire Folder" lists it. Can be changed in Settings by pasting a folder link.
const DRIVE_DEFAULT_FOLDER = { id: '0ByhXYqPJBamsS2h2X01uS29uaU0', resourceKey: '0-jrOuagpWxzlX6dXlyqbz5Q', name: 'Comics' };
