## Documentazione – `script.trgfn_guard_sorgente_polimorfa_tipizzata()` (Guard sorgente, modello A — colonne tipizzate)

> **Versione**: 2026-07-18 (ex `trgfn_guard_sorgente_polimorfa`, rinominata dal
> brief-db-guard-sorgente-polimorfa; corpo invariato)
> **Stato**: disponibile, **NON agganciata ad alcuna tabella** (vedi «Stato di aggancio»)

---

### 👀 Vedi anche
>
**Approfondimento tabelle:**
>
[config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
>
**Approfondimento funzioni**:
>
[script.trgfn_guard_sorgente_polimorfa_testuale](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_testuale) — la sorella per il modello B
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

Valida la **coerenza dei riferimenti di sorgente** per le tabelle che adottano il
**modello A — colonne tipizzate alternative**:

* `sorgente_tipo_id` → **`config.sorgenti`** (dice tabella target e chiave da usare);
* `sorgente_riga` (BIGINT) è **la chiave** quando `key_selector='id'`;
* `sorgente_uid` (UUID) è **la chiave** quando `key_selector='uid'`.

Quando una riga dichiara una sorgente, la funzione verifica **l'esistenza reale**
della riga referenziata nella `target_table` configurata; in caso negativo **blocca**
con errore fail-fast (log strutturato + eccezione via `fn_log_and_raise_error`).

⚠️ **Non usarla sulle tabelle di collegamento a chiave unica testuale**
(`pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti`): lì `sorgente_uid` è
TEXT con formato dettato dal `key_selector` e `sorgente_riga` **non è una chiave
documento** — il guard giusto è la sorella
**`trgfn_guard_sorgente_polimorfa_testuale`** (modello B). I due modelli sono
descritti in [config.sorgenti — §Convenzione chiave sorgente](/dbzero/config/tabelle/sorgenti).

---

### Stato di aggancio (storia, da conoscere)

* Il target di progetto era `vendite.attivita_fatturabili`; il trigger fu agganciato
  (20251026-02) e poi **rimosso deliberatamente** (20260225-45): *«nel flusso
  commessa-only `sorgente_tipo_id` è sempre COMMESSA e la FK `commessa_attivita_id`
  copre già la validazione»*.
* La rinomina (20260718-16) NON riaggancia nulla; **decisione confermata da Tid il
  2026-07-18 (D6 del brief-db-guard-sorgente-polimorfa): resta staccata**. La
  condizione di riaggancio e i prerequisiti (tra cui il conflitto con la
  sentinella `sorgente_riga = 0` del trigger normalize) sono registrati nella
  doc permanente della tabella:
  [attivita_fatturabili — §Validazione polimorfa della sorgente](/dbzero/vendite/tabelle/attivita_fatturabili).
* Stato vivo, sempre aggiornato: interrogare `pg_trigger` (query nella guida
  [Sorgente polimorfa](/guide/sorgente-polimorfa) §5).

---

### Comportamento (flow)

1. `NEW.sorgente_tipo_id IS NULL` → nessuna verifica (`RETURN NEW`).
2. Legge `target_table` + `key_selector` da `config.sorgenti` (solo `attivo=true`);
   mancanti → `E_SORG_CONF`.
3. `key_selector='id'` → richiede `NEW.sorgente_riga` (NULL → `E_SORG_KEY_MISSING`);
   `key_selector='uid'` → richiede `NEW.sorgente_uid` (NULL → `E_SORG_KEY_MISSING`);
   altro valore → `E_SORG_KEYSEL`.
4. Probe `SELECT 1 FROM <target_table> WHERE id|uid = $1` (regclass + bind: sicuro).
5. Non trovata → `E_SORG_NOT_FOUND` con payload dettagliato; trovata → `RETURN NEW`.

### 🚨 Codici errore

| Codice | Quando |
| --- | --- |
| `E_SORG_CONF` | configurazione sorgente mancante/errata o sorgente non attiva |
| `E_SORG_KEY_MISSING` | chiave assente rispetto al `key_selector` |
| `E_SORG_KEYSEL` | `key_selector` fuori da (`id`,`uid`) |
| `E_SORG_NOT_FOUND` | riga inesistente nella tabella target |

---

### Requisiti della tabella che (eventualmente) la aggancia

* `sorgente_tipo_id BIGINT NULL` — se NULL la verifica è bypassata;
* `sorgente_riga BIGINT NULL` — chiave per selector `id` (niente DEFAULT fittizi:
  0 non è mai un id valido);
* `sorgente_uid UUID NULL` — chiave per selector `uid`.

Naming trigger: `trg_<tabella>_a10_guard_sorgente_ins_upd`
(`BEFORE INSERT OR UPDATE OF sorgente_tipo_id, sorgente_riga, sorgente_uid`).
