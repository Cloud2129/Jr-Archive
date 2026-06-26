# JR Client Archive

Archivio documentale desktop, locale e offline per studi professionali (e adattabile ad altri settori). Nessun dato lascia il computer dell'utente.

## Stato del progetto

In sviluppo per fasi. Vedi [ARCHITECTURE.md](ARCHITECTURE.md) per l'architettura e la roadmap completa.

- [x] Fase 1 - Fondamenta: configurazione, database, logging, shell applicativa
- [x] Fase 2 - Gestione clienti
- [x] Fase 3 - Gestione documenti (ingestione, drag&drop, anteprima, sincronizzazione watchdog)
- [x] Fase 6 - Ricerca globale
- [x] Fase 7 - Backup & restore
- [x] Fase 8 - Licenza/demo
- [x] Fase 9 - Packaging

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

## Packaging (creazione dell'eseguibile)

L'app si distribuisce come eseguibile standalone con PyInstaller, in modalità one-folder (non one-file): l'app è interamente offline, quindi una cartella che l'utente può copiare su una chiavetta USB o in una directory di installazione è preferibile a un singolo exe compresso (avvio più rapido, niente estrazione in una directory temporanea ad ogni lancio).

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pyinstaller packaging/jr_client_archive.spec
```

Il risultato è in `dist/jr-client-archive/`: l'eseguibile `jr-client-archive` (o `jr-client-archive.exe` su Windows) più una cartella `_internal/` con tutte le dipendenze e le risorse (tema qt-material incluso). Nessuna installazione di Python è richiesta sulla macchina di destinazione.

Lo schema del database viene creato/aggiornato a runtime da `Database.create_all()` al primo avvio (non da Alembic): le migrazioni restano uno strumento di sviluppo, non fanno parte del pacchetto distribuito.
