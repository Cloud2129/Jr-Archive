# Architettura

## Principi

- **Tutto locale.** Nessuna chiamata cloud, nessuna dipendenza di rete a runtime.
- **La UI non contiene logica di business.** `ui/` chiama `application/`, che orchestra `services/`, che usano `repositories/` per parlare col database. Ogni livello conosce solo quello sotto di sé.
- **I dati di persistenza non attraversano la UI.** Il confine tra `db/models` (ORM SQLAlchemy) e `domain/` (DTO pydantic) è netto: la UI vede solo DTO.
- **Lo schema non si modifica per aggiungere un campo.** I campi personalizzati usano un pattern EAV (`custom_field_definitions` + `custom_field_values`), così l'utente può aggiungerne quanti vuole da interfaccia, senza nessuna migrazione.
- **Niente è hardcoded sui percorsi.** Ogni percorso passa da `config.paths.AppPaths`, calcolato in base al sistema operativo (o sovrascrivibile con `JR_CLIENT_ARCHIVE_HOME`, usato dai test).
- **Le impostazioni si modificano solo da interfaccia.** Sono righe nel database (`app_settings`), mai un file JSON da editare a mano.

## Livelli

```
ui/             PySide6: finestre, widget. Nessuna query, nessuna regola di business.
application/    Use case: orchestrazione di più servizi per un'azione utente.
services/       Logica di business pura (nessun import di PySide6 o SQLAlchemy.Session esposto all'esterno).
repositories/   Accesso ai dati: una classe per entità, query specifiche oltre al CRUD di base.
db/             Modelli ORM SQLAlchemy + migrazioni Alembic.
domain/         DTO pydantic e vocabolario condiviso (enum). Nessuna dipendenza da db/ o ui/.
config/         AppPaths, Settings, logging. Bootstrap dell'applicazione.
plugins/        Contratto per estensioni future (OCR, scanner, firma digitale, PEC, NAS, AI locale...).
utils/          Funzioni pure senza stato, condivise.
```

Regola di dipendenza: `ui -> application -> services -> repositories -> db`, e tutti possono dipendere da `domain`, `config`, `utils`. Mai il contrario.

## Database

SQLite con WAL abilitato (letture concorrenti senza bloccare la UI durante un import in background) e foreign key attive. Migrazioni con Alembic: ogni installazione utente migra il proprio database locale (percorso risolto da `AppPaths`, non in `alembic.ini`).

Tabelle principali (Fase 1):

| Tabella | Scopo |
|---|---|
| `clients` | Anagrafica cliente, codice cliente, cartella fisica |
| `folders` | Albero cartelle/sottocartelle di un cliente (self-referenziale) |
| `documents` | Catalogazione documento: checksum, tipo, stato, percorso |
| `tags` / `document_tags` | Tag molti-a-molti sui documenti |
| `document_history` | Cronologia eventi di un singolo documento (rinomina, spostamento...) |
| `custom_field_definitions` | Definizione di un campo personalizzato (tipo, obbligatorietà, ordine) |
| `custom_field_values` | Valore tipizzato di un campo personalizzato per una entità |
| `audit_log` | Log di business globale (accessi, modifiche, errori, backup, import) |
| `app_settings` | Impostazioni utente, key/value |
| `license_state` | Riga unica (Fase 8): data primo avvio, chiave di licenza attivata |

### Campi personalizzati (EAV)

Una `CustomFieldDefinition` descrive un campo (`label`, `field_type` tra TEXT/NUMBER/DATE/BOOLEAN/CHOICE, obbligatorietà, ordinamento). Una `CustomFieldValue` contiene il valore per una specifica istanza (`entity_type` + `entity_id`), in una colonna tipata (`value_text`/`value_number`/`value_date`/`value_bool`) scelta in base al tipo del campo. Aggiungere un campo è un `INSERT`, non una migrazione; i valori restano filtrabili/ordinabili in modo efficiente perché tipati, non un singolo blob testuale.

## Fase 1 - cosa esiste oggi

- `config.paths.AppPaths`: directory dati per-utente (database, archivio, log, backup, temp).
- `config.settings.AppSettings` + `SettingsService`: impostazioni tipizzate, persistite nel DB.
- `config.logging_config`: log tecnico su file con rotazione.
- `db.base.Database`: engine/sessioni SQLAlchemy, PRAGMA WAL/foreign_keys.
- Schema completo (tabelle sopra) con migrazione Alembic iniziale.
- `repositories.client_repository.ClientRepository`: ricerca istantanea, generazione codice cliente sequenziale.
- `repositories.custom_field_repository`: CRUD definizioni + upsert valori tipizzati.
- `services.audit_service.AuditService`: scrittura del log di business.
- `ui.main_window.MainWindow`: shell minima che elenca/cerca i clienti, a dimostrazione che l'intero stack (Qt -> application -> repository -> SQLite) funziona end-to-end.
- Test pytest su migrazioni, repository, servizi e smoke test della UI in modalità offscreen.

Le fasi successive (CRUD clienti completo, drag&drop, motore di riconoscimento, sync filesystem, ricerca globale, backup, licenza/demo, packaging) sono state implementate sopra queste fondamenta senza modifiche retroattive allo schema o all'architettura a livelli.

## Fase 8 - licenza & demo

Nessuna chiamata di rete, mai: la verifica della licenza è una firma Ed25519 controllata interamente offline (`utils.license_signing`). L'app distribuita contiene solo la chiave pubblica; la chiave privata resta fuori dal repository, usata da uno script di sviluppo separato (`scripts/generate_license.py`) per emettere le chiavi da consegnare ai clienti.

Al primo avvio viene scritta una sola volta `license_state.first_launch_at` (riga singola, `id=1`), che fissa in modo permanente l'inizio della finestra di demo di 60 giorni. Senza una licenza attivata, `LicenseService.status()` calcola due limiti indipendenti: `is_read_only` (scaduta la demo: blocca ogni comando di scrittura) e `client_limit_reached` (raggiunti 150 clienti: blocca solo la creazione di nuovi clienti). `application.license_guard` espone `ensure_writable`/`ensure_can_create_client`, richiamati da ogni comando applicativo che scrive dati; l'eccezione che sollevano arriva in UI tramite il pattern `except Exception` → `QMessageBox.critical` già presente in ogni dialogo, senza bisogno di disabilitare pulsanti. `backup_commands.create_backup` resta volutamente non protetto (l'export dei dati deve restare sempre possibile anche in sola lettura); `external_sync_commands.reconcile_external_move` resta volutamente non protetto (il file è già stato spostato su disco: rifiutare l'aggiornamento del DB lascerebbe un riferimento più sbagliato, non più sicuro).

## Fase 9 - packaging

`packaging/jr_client_archive.spec` produce un build PyInstaller one-folder (non one-file): l'app è offline e pensata anche per l'uso da chiavetta USB, dove l'avvio immediato di una cartella batte l'estrazione ad ogni lancio di un singolo exe compresso. Lo spec bundla `resources/` nello stesso percorso relativo al package (`jr_client_archive/resources/...`), così la risoluzione dei percorsi via `Path(__file__)` in `config.branding` continua a funzionare identica sotto PyInstaller (`_internal/`) e in sviluppo. Le dipendenze con caricamento dinamico (`qt_material`, `cryptography`, `rapidfuzz`, Pillow, SQLAlchemy) hanno hook PyInstaller scoperti automaticamente (via entry point o hook nativi); PyMuPDF e watchdog non hanno hook dedicati ma si bundlano correttamente di default, verificato con una build reale e uno smoke test dell'eseguibile risultante. Le migrazioni Alembic non fanno parte del pacchetto: a runtime lo schema viene creato/aggiornato da `Database.create_all()` (idempotente), lo stesso percorso usato anche in sviluppo da `app.main()`.
