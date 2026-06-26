# JR Client Archive

Archivio documentale desktop, locale e offline per studi professionali (e adattabile ad altri settori). Nessun dato lascia il computer dell'utente.

## Stato del progetto

In sviluppo per fasi. Vedi [ARCHITECTURE.md](ARCHITECTURE.md) per l'architettura e la roadmap completa.

- [x] Fase 1 - Fondamenta: configurazione, database, logging, shell applicativa
- [ ] Fase 2 - Gestione clienti
- [ ] Fase 3 - Gestione documenti
- [ ] Fase 4 - Motore di riconoscimento
- [ ] Fase 5 - Sincronizzazione filesystem
- [ ] Fase 6 - Ricerca globale
- [ ] Fase 7 - Backup & restore
- [ ] Fase 8 - Licenza/demo
- [ ] Fase 9 - Packaging

## Requisiti

- Python 3.13

## Setup ambiente di sviluppo

```bash
python3.13 -m venv .venv
source .venv/bin/activate          # su Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Avvio dell'applicazione

```bash
jr-client-archive
# oppure
python -m jr_client_archive.app
```

Al primo avvio l'app crea automaticamente la propria cartella dati nella posizione standard del sistema operativo (es. `~/.local/share/JR Client Archive` su Linux), contenente database, archivio clienti, log e backup. Per puntare altrove (utile anche nei test), impostare la variabile d'ambiente `JR_CLIENT_ARCHIVE_HOME`.

## Migrazioni database

Lo schema è gestito con Alembic e si applica al database dell'utente corrente (risolto tramite `AppPaths`):

```bash
alembic upgrade head                                  # applica le migrazioni
alembic revision --autogenerate -m "descrizione"       # genera una nuova migrazione
```

## Test

```bash
QT_QPA_PLATFORM=offscreen pytest
```
