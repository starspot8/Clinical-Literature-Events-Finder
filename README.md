# Clinical Literature & Events Finder

Search journals, clinical research, and medical conferences from a single search box. Literature comes from Europe PMC (including PubMed/MEDLINE), PDFs are offered only for open access articles, and events can be added to your calendar. Free, no account, no data stored.

> **Disclaimer:** This tool supports literature searching. It is not a substitute for clinical judgment. Always consult the original article before making clinical decisions.

## Why this exists

Busy clinicians need a fast way to find current evidence, older landmark papers, and upcoming meetings without juggling several websites. Clinical Literature & Events Finder puts all three in one place and works on any device.

## Features

- **Journals tab:** reviews, meta-analyses, systematic reviews, and practice guidelines
- **Research tab:** randomized controlled trials and clinical trials
- **Top 10 results** per search, with abstract preview, authors, journal, year, and citation count
- **Historical search:** filter by year range (for example 1990 to 2005) and sort by relevance, newest, or most cited
- **Retraction filter:** retracted publications are excluded
- **Legal PDFs only:** a download button appears only when the article is open access, and the file is fetched directly from the original source
- **Seminars tab:** upcoming conferences with official links and one-click "Add to calendar" (Google Calendar)
- **Responsive:** works on phones, tablets, and desktops
- **Privacy by design:** the app has no backend and stores no searches, files, or personal data

## Data sources

| Purpose | Source |
| --- | --- |
| Articles and open access PDF links | [Europe PMC REST API](https://europepmc.org/RestfulWebService) (indexes PubMed/MEDLINE) |
| Conferences | `events.json` in this repository (curated manually) |

Planned: Crossref and Unpaywall for richer metadata and additional open access links.

## How it works

The page runs entirely in the browser. When you search, your browser sends the query directly to Europe PMC and displays the results. Nothing passes through a server owned by this project.

## Run it

No build step is needed.

1. Open `index.html` through any static web server, or publish the repository with GitHub Pages.
2. Keep `index.html` and `events.json` in the same folder.

> The Seminars tab loads `events.json`, so it will not work if you open `index.html` directly from your file system. Use GitHub Pages or a local server.

### Deploy with GitHub Pages

1. Make the repository **Public**.
2. Go to **Settings > Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select `main` and `/ (root)`, then **Save**.
4. After a minute or two, the site is live at `https://<your-username>.github.io/<repository-name>/`.

## Updating the seminar list

Edit `events.json`. Each event looks like this:

```json
{
  "t": "Event name",
  "s": "2027-03-18",
  "e": "2027-03-21",
  "l": "City, Country",
  "u": "https://official-event-website.example",
  "src": "where the date was found"
}
```

- `s` and `e` are the start and end dates in `YYYY-MM-DD` format.
- Events whose end date has passed are hidden automatically.
- Please verify dates on the organizer's official website before adding an event.

## Roadmap

- [ ] Crossref and Unpaywall integration
- [ ] Filter seminars by specialty and region
- [ ] Downloadable calendar files (.ics)
- [ ] Indonesian-language query assistance
- [ ] Indonesian journal sources (for example Garuda, DOAJ)

## Limitations

- Search results depend on Europe PMC availability and indexing.
- Older articles often lack abstracts, and free PDFs are less common for them.
- Seminar dates are curated manually and may change. Always confirm with the organizer.

## Acknowledgements

Article data is provided by [Europe PMC](https://europepmc.org), which is funded by a consortium of research funders and hosted at EMBL-EBI.
