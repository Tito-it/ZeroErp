## Documentazione Concettuale -- Funzione `script.fn_get_entita_ruolo_detail`

> Vedi anche
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> * [config.utilities](/dbzero/config/tabelle/utilities)
> * [anagrafiche.vw_clienti_codice_ba](/dbzero/anagrafiche/views/vw_clienti_codice_ba)
>
> Funzione chiamante:
>
> * [script.fn_get_search_detail](/dbzero/script/funzioni/fn_get_search_detail)
>
> Ricerca universale:
>
> * [script.fn_search_soggetti_universale](/dbzero/script/manual/fn_search_soggetti_universale)

La funzione **`script.fn_get_entita_ruolo_detail`** restituisce in JSONB i dati specifici dell'entita' legata a un ruolo. La versione dinamica usa `config.tipi_ruoli.entita_tabella` per risolvere la tabella/vista a runtime, eliminando il CASE hardcoded.

---

### Scopo Principale

* **Dati entita' per ruolo**: dato un `soggetto_ruolo_id`, recupera automaticamente il tipo ruolo e interroga la tabella/vista configurata in `tipi_ruoli.entita_tabella`.

* **Query dinamica**: usa `EXECUTE format()` con `to_jsonb(e.*)` per convertire tutta la riga in JSONB, strippando le colonne di sistema (`data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza`, `id`, `soggetto_ruolo_id`) e rinominando `id` in `entita_id`.

* **Filtro opzionale per utility**: il parametro `p_utility_id` filtra le righe solo se la tabella ha la colonna `utility_id` (verifica dinamica via `pg_attribute`). Per tabelle senza `utility_id` viene ignorato.

* **Output JSONB uniforme**: `{ tipo_ruolo: "...", righe: [...] }` con un array di oggetti contenenti `entita_id` e tutti i campi specifici della tabella (meno le colonne di sistema).

* **Fallback senza tabella**: se `entita_tabella` e' NULL per il tipo ruolo (es. VE, DI, RE, PSP), restituisce `meta` da `soggetti_ruoli`.

* **Ampliabile senza modifiche SQL**: per aggiungere un nuovo tipo ruolo, basta un UPDATE/INSERT su `tipi_ruoli.entita_tabella`. Nessuna modifica al codice della funzione.

---

### Parametri di Input

| Nome                  | Tipo      | Obbligatorio | Default | Descrizione                                                                |
| --------------------- | --------- | ------------ | ------- | -------------------------------------------------------------------------- |
| `p_soggetto_ruolo_id` | `BIGINT`  | Si           | ---     | ID del record `anagrafiche.soggetti_ruoli`                                 |
| `p_utility_id`        | `INTEGER` | No           | `NULL`  | Filtra righe per utility specifica (solo se la tabella ha `utility_id`)    |

**Guard**: `p_soggetto_ruolo_id` validato tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`. Se il `soggetto_ruolo_id` non esiste in `anagrafiche.soggetti_ruoli`, viene lanciato `E_GENERICO`.

---

### Valore di Ritorno

JSONB con struttura fissa:

```json
{
  "tipo_ruolo": "CL",
  "righe": [ ... ]
}
```

#### Righe con entita_tabella (query dinamica)

Ogni oggetto in `righe` contiene:

* `entita_id` — l'ID della riga nella tabella entita'
* Tutti i campi della tabella/vista **escluse** le colonne di sistema: `id`, `soggetto_ruolo_id`, `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza`

I campi variano in base alla tabella configurata in `tipi_ruoli.entita_tabella`.

#### Mappatura tipi ruolo e tabelle

| codice_interno | entita_tabella                     | Note                                     |
| -------------- | ---------------------------------- | ---------------------------------------- |
| CL             | `anagrafiche.vw_clienti_codice_ba` | Vista clienti + billing_account + stato  |
| FO             | `anagrafiche.fornitori`            | Tabella fornitori                        |
| EF             | `anagrafiche.emittenti_fiscali`    | Tabella emittenti fiscali                |
| VT             | `anagrafiche.vettori`              | Tabella vettori                          |
| GE             | `anagrafiche.gestori`              | Tabella gestori                          |
| BANK_B         | `anagrafiche.bank_branches`        | Tabella filiali bancarie                 |
| RIS_UMANA      | `anagrafiche.risorse_umane`        | Tabella risorse umane                    |
| VE, DI, RE...  | NULL                               | Fallback: meta da soggetti_ruoli         |

#### Fallback senza entita_tabella

| Campo               | Tipo     | Fonte                             |
| ------------------- | -------- | --------------------------------- |
| `soggetto_ruolo_id` | `BIGINT` | `anagrafiche.soggetti_ruoli.id`   |
| `meta`              | `JSONB`  | `anagrafiche.soggetti_ruoli.meta` |

---

### Strategia Query Dinamica

```text
-- 1) Recupera tipo ruolo e tabella entita'
SELECT codice_interno, entita_tabella
FROM soggetti_ruoli sr JOIN tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
WHERE sr.id = p_soggetto_ruolo_id

-- 2a) Se entita_tabella IS NOT NULL:
--     Verifica se la tabella ha utility_id (pg_attribute)
--     EXECUTE format() con to_jsonb(e.*) - colonne_sistema
--     + jsonb_build_object('entita_id', e.id)
--     Filtro utility_id solo se colonna esiste e parametro fornito

-- 2b) Se entita_tabella IS NULL:
--     Restituisce meta da soggetti_ruoli
```

---

### Esempi di Utilizzo

```sql
-- 1) Dati entita' per un cliente (query dinamica su vw_clienti_codice_ba)
SELECT script.fn_get_entita_ruolo_detail(123);

-- 2) Dati entita' cliente filtrati per utility
SELECT script.fn_get_entita_ruolo_detail(123, 5);

-- 3) Dati entita' per un fornitore (query dinamica su fornitori)
SELECT script.fn_get_entita_ruolo_detail(456);

-- 4) Uso in fn_get_search_detail
SELECT script.fn_get_entita_ruolo_detail(sr.id, p_utility_id)
FROM anagrafiche.soggetti_ruoli sr
WHERE sr.soggetto_id = '...'::uuid;
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati.
* **Linguaggio**: PL/pgSQL
* **SQL dinamico**: `EXECUTE format()` con `to_jsonb(e.*) - text[]` per stripping colonne. La tabella e' validata come `regclass`. Parametri passati via `USING` (safe, no SQL injection).
* **Tipi parametri**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Ampliabilita'**: per aggiungere un nuovo tipo ruolo con tabella dedicata, basta un UPDATE su `tipi_ruoli.entita_tabella` — zero modifiche SQL. Validazione garantita dal trigger `trg_tipi_ruoli_a10_guard_entita_ref_ins_upd`.

---
