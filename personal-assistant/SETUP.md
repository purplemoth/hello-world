# My Assistant – setup guide

This is a small chat app that runs on your own computer and opens in your web browser. It keeps your "things to remember" in Todoist, and it can look at Gmail and Google Calendar to help you plan.

**What it can do:** save things to a Remember list, read your to-dos, add to-dos, tick them off, look at and add calendar events, search and read emails, and write email *drafts*.

**What it can never do:** send an email, or delete anything. It also asks you to say yes before it adds or changes anything.

Setup takes about 45 minutes, once. Steps 3 and 4 are the fiddly ones, so take them slowly.

---

## 1. Install Python (5 mins)

Python is the free programming language the app is written in.

- **Mac:** go to python.org/downloads, download the latest version and run the installer.
- **Windows:** do the same. On the first installer screen, tick **"Add Python to PATH"**.

## 2. Get the app's files onto your computer

Download this `personal-assistant` folder from GitHub (green **Code** button → **Download ZIP**), unzip it, and put it somewhere easy to find, such as your Documents folder.

## 3. Get your two keys (10 mins)

A "key" is a long password that lets the app use a service on your behalf. Keep them private.

**Claude key** (this is what the app's thinking runs on)
1. Go to console.anthropic.com and create an account. This is separate from your normal Claude subscription.
2. Add a small amount of credit under **Billing**. You pay a little for each conversation. Set a monthly spending limit there so there are no surprises.
3. Go to **API Keys** → **Create Key**, and copy it.

**Todoist key**
1. In Todoist, go to **Settings → Integrations → Developer**.
2. Copy the **API token**.

Then, in the `personal-assistant` folder, make a copy of the file `.env.example` and name the copy `.env`. Open it in a plain text editor (TextEdit on Mac, Notepad on Windows) and paste your two keys in where shown.

> Files starting with a dot are hidden on a Mac. In Finder, press **Cmd + Shift + .** to show them.

## 4. Let the app into Gmail and Google Calendar (20 mins)

Google makes you register the app first. It's a one-off. It sounds technical, but you're mainly ticking boxes.

1. Go to **console.cloud.google.com** and sign in with your personal Gmail.
2. At the top, click the project picker → **New Project**. Call it `My Assistant` → **Create**.
3. In the search bar, search **Gmail API** → **Enable**. Then search **Google Calendar API** → **Enable**.
4. Search **OAuth consent screen** (this is the "can this app access your account?" page Google will show you).
   - Choose **External**, app name `My Assistant`, and put your Gmail address in both email boxes.
   - When you reach **Test users** (sometimes called **Audience**), add your own Gmail address.
5. Search **Credentials** → **Create credentials** → **OAuth client ID** → application type **Desktop app** → **Create**.
6. Click **Download JSON**. Rename the downloaded file to exactly `credentials.json` and move it into the `personal-assistant` folder.

## 5. Install and start the app

Open **Terminal** (Mac: search for Terminal in Spotlight) or **Command Prompt** (Windows), then type these lines one at a time, pressing Enter after each. Replace the path with wherever you put the folder.

```
cd ~/Documents/personal-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, use `python` instead of `python3`, and `.venv\Scripts\activate` instead of the `source` line.

Your browser will open with the chat window. The first time you ask about email or calendar, a Google sign-in page will open. Google will warn that the app "isn't verified". That's expected, because it's your own private app. Click **Continue**.

## Using it day to day

Each time you want to use it, open Terminal and run:

```
cd ~/Documents/personal-assistant
source .venv/bin/activate
streamlit run app.py
```

Close the Terminal window to stop it.

Things to try:
- "Remember that Sarah's birthday is 3 March"
- "What's on my Remember list?"
- "What have I got on this week?"
- "Help me plan Saturday – I want to fit in a matinee"
- "Any emails about my theatre booking?"
- "Draft a reply to Ben saying I can make Thursday"

## Good to know

- **Privacy:** your messages, plus any emails or events the app looks at, are sent to Anthropic to generate replies. Keep this for personal life. Don't use it for NHS or case information.
- **Apple Notes** isn't connected, because Apple doesn't allow outside apps to connect to it. Your Remember list lives in Todoist instead, in a project called **Remember**. The app creates it automatically.
- **Costs:** only the Claude key costs anything. Check your usage at console.anthropic.com.
- **Never share** your `.env`, `credentials.json` or `token.json` files. They're your logins.
- **If something breaks:** close Terminal and start the app again. If Google sign-in stops working, delete `token.json` from the folder and sign in again.
