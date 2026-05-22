## 📘 Documentazione Concettuale – Vista `dbops.vw_non_editable_fields`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni / trigger:
> [dbops.fn_apply_lock_columns](/dbzero/dbops/funzioni/fn_apply_lock_columns)
>
Sistema lock condizionali (estensione, 2026-05-22):
> [dbops.lock_columns_conditional](/dbzero/dbops/manual/lock_columns_conditional) — registro condizionale complementare
> [dbops.fn_non_editable_fields](/dbzero/dbops/manual/fn_non_editable_fields) — funzione che unisce statici + condizionali per una riga specifica

### 🎯 Scopo Principale

(latest review 2026-05-22 — aggiunto riferimento al sistema lock condizionali)

`dbops.vw_non_editable_fields` e' un **alias semantico** sopra
[`dbops.automation_lock_columns`](/dbzero/dbops/tabelle/automation_lock_columns):
elenca i campi **non editabili** (lock incondizionato a livello DB) per
ciascuna entita' coperta dal pattern `automation_lock_columns`, filtrati
su `enabled = true`.

E' pensata come **endpoint di lookup per il backend** (Python services /
DTO builder) quando serve sapere "quali campi della tabella X non possono
essere modificati post INSERT". Il nome semantico e' piu' diretto del
nome tecnico `automation_lock_columns` (storico, riflette l'origine
"automation" del meccanismo) e quindi piu' facile da consumare in codice
applicativo.

### Perche' un alias e non una nuova tabella

Brief BE Fase 5 (28-04-2026) chiedeva una nuova tabella `dbops.lock_columns_registry (schema, table, column)`.
La tabella esisteva gia' come `dbops.automation_lock_columns` con uno schema
**piu' ricco** (oltre a `target_schema, target_table, column_name`: `error_code`,
`exec_mode`, `enabled`, `note`, audit). Creare una nuova tabella avrebbe
duplicato dati e introdotto due fonti di verita'. La vista alias preserva
single source of truth.

---

### Schema esposto

| Colonna | Tipo | Significato |
|---|---|---|
| `target_schema` | `text` | schema della tabella che contiene la colonna lockata |
| `target_table` | `text` | nome della tabella |
| `column_name` | `text` | colonna lockata |
| `error_code` | `text` | codice errore sollevato dal trigger di lock (default `'CODICE_NON_MODIFICABILE'`); il backend puo' usarlo per messaggio user-friendly mappato in `config.messaggi_errore` |
| `exec_mode` | `text` | modalita' di applicazione del lock (es. `'AUTO'`); riservato all'orchestrator dei trigger automation |
| `note` | `text` | descrizione testuale (tipicamente nome del trigger che applica il lock) |

### Filtro applicato

```sql
WHERE enabled = true
```

Le righe con `enabled = false` rappresentano lock **registrati ma temporaneamente
disabilitati** (es. durante una migrazione di dati supervisionata) e non
devono apparire come lock attivi al consumo BE.

---

### Cosa NON copre

`vw_non_editable_fields` restituisce solo i lock **incondizionati**: la colonna
non e' mai modificabile dopo l'INSERT, indipendentemente da stato/contesto.
Questo pattern e' applicato ai codici stabili (`codice`, `codice_interno`),
identificatori esterni (numero documento, codici SDI), ecc.

**Casi NON coperti da questa vista** (logica condizionale, non riducibile a "lista colonne fissa"):

| Tabella | Pattern non coperto | Soluzione |
| --- | --- | --- |
| `catalogo.articoli` | `is_composito`, `requires_serial`, `is_solo_componente` bloccati se BoM attiva | ✅ **Risolto** via `dbops.lock_columns_conditional` + `fn_non_editable_fields` (2026-05-22) |
| `vendite.promo_articoli` | whitelist campi modificabili dipendente da stato derivato (FUTURA / INIZIATA / SCADUTA) | trigger [`vendite.trgfn_promo_articoli_guard_data_driven`](/dbzero/vendite/funzioni/trgfn_promo_articoli_guard_data_driven) + logica service Python |
| `catalogo.articoli_componenti` | struttura BoM immutabile (tutti i campi struttura lockati, ma `valido_al` modificabile per "Chiudi riga") | trigger [`catalogo.trgfn_articoli_componenti_block_modifica_struttura`](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) |
| `vendite.listini_versioni` | regole transizione stato BOZZA → ATTIVA → CHIUSA con campi modificabili condizionati | logica in `apps/vendite/services/listini_service.py` |

I casi non ancora migrati al sistema condizionale richiedono logica nel service Python.
Quando la regola e' esprimibile come query SQL booleana su `$1` (id riga), si puo'
registrare in `dbops.lock_columns_conditional` e consumare via `fn_non_editable_fields`.

---

### Esempi

**1) Lookup tutti i campi non editabili di una tabella:**

```sql
SELECT column_name, error_code, note
  FROM dbops.vw_non_editable_fields
 WHERE target_schema = 'anagrafiche'
   AND target_table  = 'fornitori';
-- column_name | error_code               | note
-- ------------+--------------------------+--------------------------------------
-- codice      | CODICE_NON_MODIFICABILE  | da trigger trg_fornitori_a10_protect_account_code_upd ...
```

**2) Tutti i lock per uno schema (es. mappa UI di un dominio):**

```sql
SELECT target_table, array_agg(column_name ORDER BY column_name) AS locked_columns
  FROM dbops.vw_non_editable_fields
 WHERE target_schema = 'anagrafiche'
 GROUP BY target_table
 ORDER BY target_table;
```

**3) Uso BE: costruzione DTO hint per il frontend.**

```python
# apps/<dominio>/services/<entita>_service.py

def _readonly_fields(schema: str, table: str) -> list[str]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM dbops.vw_non_editable_fields "
            "WHERE target_schema = %s AND target_table = %s",
            [schema, table],
        )
        return [row[0] for row in cur.fetchall()]
```

Il FE riceve la lista `readonly_fields` e disabilita i form input
corrispondenti, mostrando il messaggio mappato da `error_code` (via
`config.messaggi_errore` o tabella i18n FE dedicata).

---

### Note operative

* **Single source of truth**: la vista non ha contenuto proprio. Ogni
  modifica al pattern di lock (aggiunta colonna, disabilitazione, cambio
  `error_code`) si fa **solo su `dbops.automation_lock_columns`** -- la
  vista riflette automaticamente. Niente cache, niente refresh.
* **Performance**: la tabella sottostante ha PK su
  `(target_schema, target_table, column_name)` che soddisfa il pattern
  di lookup tipico (filtro su schema+table). Le query del backend
  saranno index-only scans.
* **`enabled = false` = disabilitazione temporanea**: usata in scenari
  di manutenzione (es. patch di dati con autorizzazione esplicita). In
  produzione tutti i lock dovrebbero essere `enabled = true`. La vista
  filtra di proposito le righe disabilitate per **non esporre falsi
  positivi** al backend.
* **Quando il backend espone questa lista al FE**: e' una lista "view-only";
  non e' la fonte di verita' delle regole di editabilita' complete (vedi
  sezione "Cosa NON copre"). Per coperture totali bisogna combinare la
  vista con la logica stato-dipendente nei service.
* **Sistema condizionale implementato (2026-05-22)**: i casi lock condizionali
  sono ora gestibili via `dbops.lock_columns_conditional` +
  `dbops.fn_non_editable_fields`. Per i detail endpoint che hanno l'id riga,
  usare `fn_non_editable_fields` al posto di questa vista — restituisce
  statici + condizionali in un unico array ordinato.
  Vedi [lock_columns_conditional](/dbzero/dbops/manual/lock_columns_conditional)
  e [fn_non_editable_fields](/dbzero/dbops/manual/fn_non_editable_fields).

---

### Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/dbops/20260428-05-create-vw-non-editable-fields-mctit.yaml`
- Tabella sorgente: [`dbops.automation_lock_columns`](/dbzero/dbops/tabelle/automation_lock_columns) (21 righe seedate al 28-04-2026)
- Brief BE origine: Fase 5 28-04-2026 (proposta originale `lock_columns_registry`, ridotta a vista alias dato che la tabella esisteva gia')

---

{% include-markdown "signature-core.md" %}

---
