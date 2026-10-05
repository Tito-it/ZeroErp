## Documentazione – `script.trgfn_guard_sorgente_polimorfa_testuale()` (Guard sorgente, modello B — chiave unica testuale)

> **Versione**: 2026-07-18 (brief-db-guard-sorgente-polimorfa, migration 20260718-17)
> **Stato**: **attiva** su `pratiche.pratiche_sorgenti` (20260718-18) e
> `vendite.commesse_sorgenti` (20260718-19)

---

### 👀 Vedi anche
>
**Approfondimento tabelle:**
>
[config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
> [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
>
**Approfondimento funzioni**:
>
[script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata) — la sorella per il modello A
> [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — il «rubinetto» che normalizza prima di scrivere
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

Valida la sorgente polimorfa delle **tabelle di collegamento a chiave unica
TESTUALE** (modello B): la colonna `sorgente_uid` è **TEXT** e contiene la chiave
nel **formato dettato da `config.sorgenti.key_selector`**:

* `key_selector='id'` → **`id::text`** del documento (testo numerico);
* `key_selector='uid'` → **uuid testuale** del documento.

È la convenzione descritta in
[config.sorgenti — §Convenzione chiave sorgente](/dbzero/config/tabelle/sorgenti),
quella su cui sono costruite le `vw_stato_sorgente_*` e il lineage. Il guard
garantisce che ogni riga scritta sia **risolvibile**: formato giusto E documento
esistente. Prima del 2026-07-18 questa convenzione non era blindata da nulla — le
righe fuori formato restavano «non risolte» in silenzio (bug latente censito dal
brief-db-guard-sorgente-polimorfa §1c).

`sorgente_riga` qui **non è una chiave documento** (è la grana di riga del link,
es. riga preventivo) e **non viene validata** da questo guard (decisione D4 del
brief: eventuale verifica in fase 2 via colonna `target_righe_table` in config).

---

### Comportamento (flow)

1. `NEW.sorgente_tipo_id IS NULL` → nessuna verifica (`RETURN NEW`).
2. Legge `target_table` + `key_selector` da `config.sorgenti` (solo `attivo=true`);
   mancanti → `E_SORG_CONF`.
3. `btrim(NEW.sorgente_uid)` vuota/NULL → `E_SORG_KEY_MISSING`.
4. **Formato** secondo il selector, sul valore **così come verrà salvato** e in **forma
   canonica** (dal 2026-10-05):
   * `id`: la chiave deve essere un intero scritto come `id::text` — niente zeri davanti,
     spazi, segno → altrimenti `E_SORG_FORMATO` (546);
   * `uid`: la chiave deve essere un uuid scritto come `uid::text` — minuscolo, con i
     trattini → altrimenti `E_SORG_FORMATO` (546);
   * selector fuori catalogo → `E_SORG_KEYSEL`.

   Il controllo usa i building block
   [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id) /
   [script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid): la stessa
   regola con cui la chiave viene poi **cercata**. Prima il guard accettava `'007'`, `' 42 '` o un
   uuid maiuscolo: il documento esisteva, ma la chiave salvata non veniva mai ritrovata da chi
   legge lo stato o il lineage. Il guard **rifiuta**, non corregge.
5. **Esistenza**: probe `SELECT 1 FROM <target_table> WHERE id|uid = $1`
   (regclass + bind, con la chiave già convertita) → non trovata → `E_SORG_NOT_FOUND`.

### 🚨 Codici errore

| Codice | Quando |
| --- | --- |
| `E_SORG_CONF` | configurazione sorgente mancante/errata o sorgente non attiva |
| `E_SORG_KEY_MISSING` | `sorgente_uid` NULL o vuota |
| `E_SORG_FORMATO` (546) | formato non conforme al `key_selector` del tipo |
| `E_SORG_KEYSEL` | `key_selector` fuori da (`id`,`uid`) |
| `E_SORG_NOT_FOUND` | documento inesistente nella tabella target |

---

### Difesa in profondità col «rubinetto»

`vendite.fn_link_commessa_sorgente` (punto unico di scrittura dei link commessa)
**normalizza** la chiave prima di scrivere: se riceve l'uuid di un documento a
chiave `id` (comportamento storico dei chiamanti BE), lo **traduce** in `id::text`
via `target_table.uid`. Il guard quindi non scatta mai nel flusso vivo: esiste per
i writer che saltano la fn (INSERT diretti, codice futuro) — falliscono qui in
modo parlante, non in silenzio tra sei mesi in una proiezione di stato.

### Trigger attivi

* `trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd`
  (`BEFORE INSERT OR UPDATE OF sorgente_tipo_id, sorgente_uid`)
* `trg_commesse_sorgenti_a10_guard_sorgente_ins_upd`
  (`BEFORE INSERT OR UPDATE OF sorgente_tipo_id, sorgente_uid`)

Test: `db/pgtap/script/test-guard-sorgente-polimorfa-testuale-v1.sql`.
