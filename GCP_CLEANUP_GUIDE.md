# GCP Cleanup Guide (Shutting Down the Experiment)

Since we are moving to GitHub Pages, you should disable your Google Cloud project to ensure **zero** risk of accidental API costs or data being stored on Google's servers.

### 1. Shut down the App Engine Service
1.  Go to the **[App Engine Settings](https://console.cloud.google.com/appengine/settings)** page.
2.  Click **DISABLE APPLICATION**. 
    - This immediately stops anything from running and prevents any future traffic.

### 2. Delete the Project (Total Clean Slate)
If you don't plan to use Google Cloud for anything else soon, deleting the project is the safest "nuclear" option.
1.  Go to the **[IAM & Admin > Settings](https://console.cloud.google.com/iam-admin/settings)** page.
2.  Click **SHUT DOWN**.
3.  Enter your Project ID (`wave6-dashboard`) to confirm.
    - This will delete all files, buckets, and settings associated with the failed deployment.

### 3. Remove Local Files
Once you've done the above, you can safely delete these 3 files from your local folder:
- `app.yaml`
- `main.py`
- `requirements.txt`
- `GCP_INSTRUCTIONS.md`

**Doing Step 2 (Shut Down Project) is the most effective way to ensure no unwanted costs ever occur.**
