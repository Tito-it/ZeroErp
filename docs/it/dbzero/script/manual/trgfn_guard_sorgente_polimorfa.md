## ⚙️ Documentazione – `script.trgfn_guard_sorgente_polimorfa()` (Trigger Polimorfo di Sorgente)
 
> **Versione**: 2025-10-26
> **Stato**: Da testare

---

### 👀 Vedi anche
>
> **Approfondimento tabelle:**:
> 
>  `config.sorgenti`(/dbzero/config/tabelle/sorgenti)   
>  `vendite.attivita_fatturabili`(/dbzero/vendite/tabelle/attivita_fatturabili)     
> 
> **Approfondimento funzioni**:
> 
>  `script.fn_log_and_raise_error`(/dbzero/script/funzioni/>fn_log_and_raise_error)
  
---

### 🎯 Scopo Principale

`script.trgfn_guard_sorgente_polimorfa()` fornisce un **controllo unificato e riusabile** sulla **coerenza dei riferimenti di sorgente** (origine dati) per tabelle applicative che adottano il pattern:

* `sorgente_tipo_id` → **`config.sorgenti`** (mappa *schema.tabella* di destinazione e la chiave da usare);
* `sorgente_riga` (BIGINT) **oppure** `sorgente_uid` (UUID) → valore della chiave nella tabella target.

**Obiettivo**: quando una riga dichiara una sorgente, la funzione verifica **l’esistenza reale** della riga referenziata nella tabella di destinazione configurata; in caso negativo, **blocca** l’operazione con errore **fail‑fast** (log strutturato + eccezione).

---

### 🧭 Quando si attiva

* **BEFORE INSERT OR UPDATE** sulla tabella che la aggancia (es.: `vendite.attivita_fatturabili`).
* Si attiva **solo** se `NEW.sorgente_tipo_id IS NOT NULL`.
* In caso di inconsistenza, **non scrive** e **solleva errore** tramite `script.fn_log_and_raise_error`.

---

### 🧩 Dipendenze & Configurazione

### 1) `config.sorgenti` (routing polimorfo)

Campi rilevanti:

* `id` — chiave della sorgente (referenziata da `sorgente_tipo_id`).
* `target_table REGCLASS` — tabella target della sorgente (es. `'vendite.ordini_righe'::regclass`).
* `key_selector TEXT` — **`'id'`** per chiave numerica (`id`), **`'uid'`** per chiave UUID (`uid`).
* `attivo BOOLEAN` — solo sorgenti attive sono valide.

> **Nota**: `key_selector` è protetto da CHECK `IN ('id','uid')` e default `id`. `target_table` dovrebbe essere trattato come **immutabile** (lock via trigger) dopo la creazione.

### 2) Tabelle che usano il trigger

La tabella chiamante deve esporre i seguenti campi:

* `sorgente_tipo_id BIGINT NULL` — opzionale; se NULL la verifica è bypassata.
* `sorgente_riga BIGINT NULL` — usato quando `key_selector='id'`.
* `sorgente_uid UUID NULL` — usato quando `key_selector='uid'`.

> Esempio tipico: `vendite.attivita_fatturabili`.

---

### 🔎 Comportamento dettaglio (flow)

1. **Short‑circuit**: se `NEW.sorgente_tipo_id IS NULL` → `RETURN NEW` (nessuna verifica).
2. **Caricamento configurazione**: legge da `config.sorgenti` (solo record `attivo=TRUE`) i campi `target_table` e `key_selector` per `NEW.sorgente_tipo_id`.
3. **Validazione configurazione**: se `target_table` **o** `key_selector` mancanti → errore `E_SORG_CONF`.
4. **Selezione chiave**:

   * se `key_selector='id'` → richiede `NEW.sorgente_riga` (BIGINT); se NULL → `E_SORG_KEY_MISSING`.
   * se `key_selector='uid'` → richiede `NEW.sorgente_uid` (UUID); se NULL → `E_SORG_KEY_MISSING`.
5. **Verifica esistenza**: esegue `SELECT 1 FROM target_table WHERE <key_col> = $1`.

   * key_col = `id` se selector=`id`; `uid` se selector=`uid`.
   * La query è costruita in modo **sicuro** con `regclass` e parametri bind.
6. **Esito**:

   * se non trovata → `E_SORG_NOT_FOUND` con payload dettagliato (tabella target, key_selector, valori sorgente).
   * se trovata → `RETURN NEW`.

---

### 🚨 Codici Errore & Messaggi

Tutti gli errori sono generati via `script.fn_log_and_raise_error(<area>, <tabella>, <codice>, <json_detail>, <uuid>, <args...>)` con `area = TG_TABLE_SCHEMA`.

| Codice               | Significato                             | Quando scatta                                                      | Dettagli `jsonb`                                                                    |
| -------------------- | --------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `E_SORG_CONF`        | Configurazione sorgente mancante/errata | `target_table` o `key_selector` NULL, sorgente non attiva          | `sorgente_tipo_id`, `target_table`, `key_selector`                                  |
| `E_SORG_KEY_MISSING` | Chiave sorgente assente                 | Manca `sorgente_riga` per selector `id` o `sorgente_uid` per `uid` | `sorgente_tipo_id`, `key_selector`                                                  |
| `E_SORG_KEYSEL`      | Selector non supportato                 | Valore non in (`id`,`uid`)                                         | `sorgente_tipo_id`, `key_selector`                                                  |
| `E_SORG_NOT_FOUND`   | Riga target inesistente                 | La SELECT su tabella target non trova la chiave                    | `sorgente_tipo_id`, `target_table`, `key_selector`, `sorgente_riga`, `sorgente_uid` |

> I codici sono pensati per essere tracciabili in dashboard e log applicativi.

---

### 🛠️ Attivazione (esempio)

```sql
-- Rimuove l’eventuale trigger precedente
DROP TRIGGER IF EXISTS trg_attivita_fatturabili_a10_ins_upd_guard_fonte ON vendite.attivita_fatturabili;

-- Collega il trigger polimorfo
CREATE TRIGGER trg_attivita_fatturabili_a10_ins_upd_guard_fonte
  BEFORE INSERT OR UPDATE ON vendite.attivita_fatturabili
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_guard_sorgente_polimorfa();

COMMENT ON TRIGGER trg_attivita_fatturabili_a10_ins_upd_guard_fonte ON vendite.attivita_fatturabili IS
  'Verifica polimorfa dell\'esistenza della riga sorgente (config.sorgenti → target_table, key_selector).';
```

> **Precondizioni**: la sorgente (`config.sorgenti`) deve avere `target_table` settato e `key_selector` coerente con il campo che userai (`id` → `sorgente_riga`, `uid` → `sorgente_uid`).

---

### 📈 Performance & Sicurezza

* **SQL dinamico sicuro**: usa `regclass` e bind parameter (`USING`) → nessuna injection.
* **Indice**: assicurarsi che la tabella target abbia indice sulla colonna chiave (`id` o `uid`).
* **Costo**: un singolo probe `SELECT 1` per riga modificata.

---

### 🧪 Edge cases & comportamento

* **Sorgente disattiva** (`attivo=FALSE`): trattata come configurazione errata → `E_SORG_CONF`.
* **Chiave non valorizzata**: `E_SORG_KEY_MISSING` in base al selector.
* **Cambio di configurazione**: si consiglia di proteggere `target_table` e `key_selector` con trigger di **lock colonne**.

---
