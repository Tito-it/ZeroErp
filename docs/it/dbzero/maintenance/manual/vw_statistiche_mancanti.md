## 📘 Documentazione Concettuale – Vista `maintenance.vw_statistiche_mancanti`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`maintenance.fn_analyze_statistiche`](/dbzero/maintenance/manual/fn_analyze_statistiche)

---
### 🎯 Scopo Principale
(latest review 14-10-2026)

Le tabelle che, **per chi interroga la vista**, resterebbero senza statistiche
dopo un `ANALYZE`. È la prova che usa
[`fn_analyze_statistiche`](/dbzero/maintenance/manual/fn_analyze_statistiche)
subito dopo il suo lavoro, e si può leggere a mano per sapere oggi quali
tabelle il pianificatore stima alla cieca.

| Colonna | Contenuto |
| --- | --- |
| `relid` | la tabella (`regclass`) |
| `schema_nome`, `tabella_nome` | i suoi nomi |
| `relkind` | `r` ordinaria, `p` partizionata |
| `motivo` | `NON_ANALIZZABILE` (il ruolo non ha `MAINTAIN`: `ANALYZE` la salterebbe) oppure `MAI_ANALIZZATA` (`pg_class.reltuples < 0`: mai un `ANALYZE` né un `VACUUM`) |

⚠️ `MAI_ANALIZZATA` si legge da `pg_class`, che sta nel catalogo e sopravvive a
un crash. I contatori di `pg_stat_*` (`last_analyze`) no.

---

### Il perimetro, per struttura

Tabelle ordinarie e partizionate, **tranne**:

* gli schemi di sistema (`pg_catalog`, `information_schema`, `pg_toast`);
* le tabelle temporanee delle **altre** sessioni (quelle della sessione corrente
  restano dentro: è ciò che lascia a un pgTAP costruire il suo caso);
* gli oggetti che appartengono a un'**estensione** (`pgagent`, PostGIS,
  topology), riconosciuti da `pg_depend`, non da un elenco di nomi;
* una tabella partizionata **senza partizioni**: non ha dati da descrivere e
  resta a `reltuples = -1` anche dopo `ANALYZE` (provato su PostgreSQL 18.6,
  2026-10-14).

### ⚠️ Risponde per chi la interroga

Il diritto si legge col ruolo corrente. Come `zeroerp_app` **ogni** tabella di
progetto è `NON_ANALIZZABILE`, ed è giusto: l'applicazione non analizza. La
risposta che conta è quella del ruolo del job.

Brief: `brief-db-statistiche-tabelle-job-notturno` (D15).
