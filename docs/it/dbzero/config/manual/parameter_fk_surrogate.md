## 📘 Documentazione Concettuale – Tabella `config.parameter_fk_surrogate`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate)
> [config.trgfn_parameters_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameters_fk_surrogate_dispatch)
> [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameter_overrides_fk_surrogate_dispatch)

### 🎯 Scopo Principale

(latest review 02-05-2026)

La tabella **`config.parameter_fk_surrogate`** e' il **registry** del framework
"FK-surrogata" sui parametri applicativi. Una riga = un pattern di `code` (di
`config.parameters`) che, se matchato, vincola il `default_value` (e
`overridden_value` lato `parameter_overrides`) ad esistere in una specifica
colonna di una tabella di catalogo.

Implementa il principio descritto in
[linee-guida-sql §6b](/it/linee-guida-sql.md#6b-riferimenti-esterni-a-tabelle-di-catalogo-chiave-naturale-stabile):
qualunque parametro che referenzia una tabella di catalogo deve farlo per
**chiave naturale stabile** (di norma `codice_interno`, immutabile via
`script.trgfn_lock_columns`), mai per `id`.

### Perche' un registry e non un guard ad-hoc

Il primo guard ad-hoc (DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*, 20260427-05) era
hard-coded sul singolo pattern: aggiungere un secondo pattern (DEFAULT_UTILITY)
avrebbe richiesto un secondo trigger duplicato, e cosi' via per ogni pattern
futuro. Il framework parametrico:

* generalizza il check via `script.fn_check_parameter_fk_surrogate(code, value)`
  che fa lookup dinamico su questo registry;
* dispatcher unico su `parameters` (`config.trgfn_parameters_fk_surrogate_dispatch`)
  e dispatcher speculare su `parameter_overrides`
  (`config.trgfn_parameter_overrides_fk_surrogate_dispatch`);
* aggiungere un nuovo pattern = una sola riga seed in 80_data, zero codice DB nuovo.

Pattern allineato a `dbops.automazione_chiusura_scadenze` (linee-guida-sql §7c):
configurazione dichiarativa + motore unico.

---

### Campi chiave e semantica

* **`id`** *(bigserial)* – PK tecnica.
* **`code_pattern`** *(varchar(200))* – pattern del `code` di
  `config.parameters` da intercettare. UNIQUE.
* **`match_mode`** *(varchar(10))* – `EXACT` (uguaglianza) | `LIKE` (pattern SQL
  standard con `%`/`_`). Default `EXACT`. Constraint
  `chk_parameter_fk_surrogate_match_mode`.
* **`target_schema`** *(varchar(63))* – schema della tabella di lookup.
* **`target_table`** *(varchar(63))* – tabella di lookup (es. `utilities`,
  `tipi_soggetto_dettaglio`).
* **`target_column`** *(varchar(63))* – colonna chiave naturale stabile della
  tabella di lookup. Default `codice_interno`. Permesso override per casi
  documentati (es. ISO codes su tabelle stati, dove la chiave naturale e'
  `code_iso2`/`code_iso3`).
* **`enabled`** *(boolean)* – soft-disable per la riga. Il dispatcher ignora
  righe con `enabled = false`.
* **`note`** *(text)* – descrizione operativa.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Risoluzione del pattern

Quando piu' righe possono matchare, l'ordine di priorita' e':

1. `match_mode = 'EXACT'` con `code_pattern = code` — match esatto vince.
2. `match_mode = 'LIKE'` con `code LIKE code_pattern` — primo pattern LIKE (a
   parita' di lunghezza, ordinamento alfabetico).
3. A parita' di match_mode, vince il pattern con `length(code_pattern)` maggiore
   (piu' specifico).

In pratica: usare LIKE per famiglie di parametri (`DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%`),
EXACT per parametri singoli (`DEFAULT_UTILITY`).

---

### Esempi

**1) Aggiungere un pattern per famiglia di code:**

```sql
INSERT INTO config.parameter_fk_surrogate
  (code_pattern, match_mode, target_schema, target_table, target_column, note)
VALUES
  ('DEFAULT_LISTINO_TIPOLOGIA_%','LIKE','config','listini_tipologie','codice_interno',
   'Default tipologia listino per ruolo applicativo.');
```

**2) Aggiungere un pattern singolo (EXACT):**

```sql
INSERT INTO config.parameter_fk_surrogate
  (code_pattern, match_mode, target_schema, target_table, target_column, note)
VALUES
  ('DEFAULT_VALUTA','EXACT','config','valute','code_iso3',
   'Default valuta sistema. Chiave naturale ISO 4217.');
```

**3) Disabilitare temporaneamente un pattern (rollback parziale):**

```sql
UPDATE config.parameter_fk_surrogate
   SET enabled = false
 WHERE code_pattern = 'DEFAULT_UTILITY';
```

---

### Note operative

* **Tabelle target**: la colonna `target_column` deve essere una colonna di
  catalogo *immutabile*. La convenzione standard e' `codice_interno`, che e'
  protetto automaticamente da `script.trgfn_lock_columns` quando la colonna
  esiste (provisioning via `dbops.fn_run_automations_lock_columns`). Per
  colonne diverse (es. ISO code) verificare immutabilita' caso per caso.
* **Tabelle SENZA chiave naturale stabile**: NON aggiungere righe puntando ad
  `id`. Va prima esposta una chiave naturale (vedi tech debt
  `DEFAULT_IVA_ID` -> richiede aggiunta di `codice_interno` su `config.iva`).
* **Override riga registry**: il dispatcher legge `enabled` runtime; per
  manutenzione bastano UPDATE.
* **Niente FK fisica** dal registry verso le tabelle target: il lookup e'
  dinamico via `format()`/`EXECUTE`. Conseguenza: typo in `target_table` causa
  errore SQL al primo scatto del dispatcher (non a INSERT del registry). Il
  pgTAP della suite copre il caso "pattern attivo + tabella inesistente"
  per evitare regressioni.

---

{% include-markdown "signature-core.md" %}

---
