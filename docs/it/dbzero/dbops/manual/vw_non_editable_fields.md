## 📘 Documentazione Concettuale – Vista `dbops.vw_non_editable_fields`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni / trigger:
> [dbops.fn_apply_lock_columns](/dbzero/dbops/funzioni/fn_apply_lock_columns)

### 🎯 Scopo Principale

(latest review 28-04-2026)

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

**Casi NON coperti** (logica condizionale, non riducibile a "lista colonne"):

| Tabella | Pattern non coperto | Trigger responsabile |
|---|---|---|
| `vendite.promo_articoli` | whitelist campi modificabili dipendente da stato derivato (FUTURA / INIZIATA / SCADUTA) | [`vendite.trgfn_promo_articoli_guard_data_driven`](/dbzero/vendite/funzioni/trgfn_promo_articoli_guard_data_driven) |
| `catalogo.articoli_componenti` | struttura BoM immutabile (tutti i campi struttura lockati, ma `valido_al` modificabile per pattern "Chiudi riga") | [`catalogo.trgfn_articoli_componenti_block_modifica_struttura`](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) |
| `vendite.listini_versioni` | regole transizione stato BOZZA → ATTIVA → CHIUSA con campi modificabili condizionati | logica in `apps/vendite/services/listini_service.py` |

Per queste entita' il backend deve continuare a tenere la logica lato
service Python (o, in futuro, definire un meccanismo dichiarativo separato
basato su JSONB con espressioni stato-dipendenti).

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
* **Estensione futura**: se i casi condizionali (promo_articoli,
  articoli_componenti, listini_versioni) dovessero essere portati a
  un meccanismo dichiarativo, l'opzione naturale e' una nuova tabella
  `dbops.field_editability_rules` con colonne JSONB per esprimere
  espressioni di stato (es. `{"stato": "INIZIATA", "campi_modificabili":
  ["descrizione", "valido_al", "meta"]}`). Decisione architetturale da
  affrontare separatamente, non urgente.

---

### Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/dbops/20260428-05-create-vw-non-editable-fields-mctit.yaml`
- Tabella sorgente: [`dbops.automation_lock_columns`](/dbzero/dbops/tabelle/automation_lock_columns) (21 righe seedate al 28-04-2026)
- Brief BE origine: Fase 5 28-04-2026 (proposta originale `lock_columns_registry`, ridotta a vista alias dato che la tabella esisteva gia')

---

{% include-markdown "signature-core.md" %}

---
