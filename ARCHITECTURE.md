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

Le funzionalità descritte nelle fasi successive (CRUD clienti completo, drag&drop, motore di riconoscimento, sync filesystem, ricerca globale, backup, licenza demo, packaging) non sono ancora implementate: lo schema e l'infrastruttura sono già pronti a riceverle senza richiedere modifiche retroattive.
