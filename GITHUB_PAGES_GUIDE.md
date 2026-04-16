# GitHub Pages Deployment Guide

Follow these steps to upload your dashboard to GitHub and turn on the website.

### 1. Create your Repository
1.  Log in to [GitHub](https://github.com/).
2.  Click **New** to create a repository.
3.  **Name**: `learning-dashboard` (or whatever you like).
4.  **Visibility**: Select **Public** (required for free GitHub Pages).
5.  Click **Create repository**.

### 2. Prepare your Data (The Lock)
Before uploading, you must generate the protected data files.
1.  In your local terminal, run:
    ```bash
    python3 lock_data.py
    ```
2.  Enter your chosen password.
3.  You will see two new files created: `data_[hash]_m.csv` and `data_[hash]_r.csv`.

### 3. Upload your Files
There are several ways to upload, but the simplest is to use the terminal in your project folder:

```bash
# Initialize git
git init
git add .
git commit -m "Initial commit with Static Lock"

# Connect to your new GitHub repo (copy the URL from your GitHub page)
git remote add origin https://github.com/your-username/learning-dashboard.git
git branch -M main
git push -u origin main
```

*(Alternatively, you can just drag and drop the files from your folder directly onto the GitHub website.)*

### 4. Activate the Website
1.  In your GitHub repository, click **Settings** (top tab).
2.  In the left sidebar, click **Pages**.
3.  Under **Build and deployment > Branch**, select `main` and `/ (root)`.
4.  Click **Save**.

### 5. Final Result
GitHub will give you a URL like `https://your-username.github.io/learning-dashboard/`. 
- Open that URL.
- Enter your password to unlock the data.

---

> [!CAUTION]
> **What NOT to upload**: 
> You should **NOT** upload your `bootcamp.db` or your original `milestone_matrix.csv` / `layer2_layer3_clean_matrix.csv` if you want maximum privacy. The dashboard only needs the `dashboard/` folder and the two `data_...csv` files created by the locker script.
