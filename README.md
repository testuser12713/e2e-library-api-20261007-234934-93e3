# Stadtbibliothek-Ausleih-API

REST-API für die Ausleihe einer kleinen Stadtbibliothek. Sie verwaltet Bücher,
Mitglieder und Ausleihen, erzwingt die Ausleihregeln (max. 3 offene Ausleihen pro
Mitglied, nur freie Exemplare, Rückgabe schließt die Ausleihe) und bietet CRUD,
Ausleihe/Rückgabe, eine Überfälligkeitsliste sowie eine paginierte Buchsuche.
Alle schreibenden Endpunkte sind per `X-API-Key` geschützt; jede Fehlerantwort
hat dasselbe JSON-Format.

## Tech-Stack

- **Sprache**: Python 3.12 (getestet mit 3.13)
- **Framework**: FastAPI
- **Validierung**: Pydantic v2
- **ORM**: SQLAlchemy 2.0
- **Datenbank**: SQLite (Standard `sqlite:///./library.db`)
- **Server**: Uvicorn
- **Tests**: pytest + `fastapi.testclient.TestClient` + httpx
- **Konfiguration**: pydantic-settings, API-Key aus der Umgebungsvariable

## Installation

```bash
py -m venv .venv
.venv\Scripts\activate        # unter Linux/macOS: source .venv/bin/activate
py -m pip install -r requirements.txt
```

## Starten

Die App legt ihre Tabellen beim Start selbst an und benötigt keine externe
Datenbank. Der dokumentierte Startbefehl lautet:

```bash
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Danach ist die API unter `http://localhost:8000` erreichbar, die
Health-Prüfung unter `GET /health` antwortet mit `{"status": "ok"}`.

## Konfiguration

Die Konfiguration wird aus Umgebungsvariablen (optional aus einer `.env`-Datei)
gelesen:

| Variable | Pflicht | Standard | Bedeutung |
| --- | --- | --- | --- |
| `LIBRARY_API_KEY` | nein | – | Schlüssel für alle schreibenden Endpunkte (`X-API-Key`). |
| `DATABASE_URL` | nein | `sqlite:///./library.db` | SQLAlchemy-Verbindungs-URL. |

**Ohne gesetzten `LIBRARY_API_KEY`** startet die App normal, lesende Endpunkte
funktionieren weiterhin, und schreibende Endpunkte antworten mit `503`. Sobald
ein Schlüssel gesetzt ist, verlangen schreibende Endpunkte den passenden Header
`X-API-Key` und antworten sonst mit `401`.

Schlüssel für eine Sitzung setzen (Beispiel, kein echter Schlüssel im Repo):

```bash
# Windows (cmd)
set LIBRARY_API_KEY=<dein-schluessel>
# Windows (PowerShell)
$env:LIBRARY_API_KEY = "<dein-schluessel>"
# Linux/macOS
export LIBRARY_API_KEY=<dein-schluessel>
```

## Tests

```bash
py -m pytest
```

Die Suite läuft gegen eine eigene In-Memory-SQLite-Datenbank und benötigt keine
externen Dienste und keinen gesetzten API-Key.

## Endpunkte

Alle Fehlerantworten haben die Form
`{"error": {"code": "<code>", "message": "<nachricht>"}}`.

### Health

- `GET /health` → `200 {"status": "ok"}`

### Bücher

- `POST /books` → `201 BookRead` | `409` doppelte ISBN | `422`
- `GET /books?q=&limit=20&offset=0` → `200 BookPage`
- `GET /books/{book_id}` → `200 BookRead` | `404`
- `PUT`/`PATCH /books/{book_id}` → `200 BookRead` | `404` | `409` | `422`
- `DELETE /books/{book_id}` → `204` | `404`

### Mitglieder

- `POST /members` → `201 MemberRead` | `409` doppelte E-Mail | `422`
- `GET /members` → `200 list[MemberRead]`
- `GET`/`PUT`/`PATCH`/`DELETE /members/{member_id}` → `200`/`200`/`200`/`204` | `404` | `409` | `422`

### Ausleihen

- `POST /loans` → `201 LoanRead` | `404` unbekanntes Buch/Mitglied | `409` (max. 3 offene Ausleihen oder kein freies Exemplar) | `422`
- `GET /loans?member_id=&book_id=` → `200 list[LoanRead]`
- `GET /loans/{loan_id}` → `200 LoanRead` | `404`
- `POST /loans/{loan_id}/return` → `200 LoanRead` | `404` | `409` bereits zurückgegeben
- `GET /loans/overdue` → `200 list[LoanRead]` (nur offene Ausleihen mit Fälligkeit vor heute)

Datenregeln: `loaned_on` = heute, `due_on` = heute + 14 Tage, `returned_on` =
heute bei der Rückgabe.

## Funktionen

- Bücher-CRUD inklusive case-insensitiver Teilersuche über Titel und Autor mit
  Pagination (`items`, `total`, `limit`, `offset`).
- Mitglieder-CRUD mit eindeutiger E-Mail.
- Ausleihe und Rückgabe mit den Ausleihregeln (max. 3 offene Ausleihen pro
  Mitglied, nur freie Exemplare).
- Überfälligkeitsliste.
- API-Key-Schutz für alle schreibenden Endpunkte.
- Einheitliches Fehlerformat für 401/404/409/422.
