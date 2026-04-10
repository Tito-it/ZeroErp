## Documentazione Concettuale -- Funzione `script.fn_get_search_detail`

> Vedi anche
>
Approfondimento tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
> [config.utilities](/dbzero/config/tabelle/utilities)
>
Approfondimento viste:
>
[anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)
>
Funzione complementare (livello 1):
>
[script.fn_search_soggetti_universale](/dbzero/script/funzioni/fn_search_soggetti_universale)
>
Funzione dati entita':
>
[script.fn_get_entita_ruolo_detail](/dbzero/script/funzioni/fn_get_entita_ruolo_detail)
>
Documento di design:
>
[Contesto Globale Ricerca Universale](/dev/work-done/frontend/contesto-globale-ricerca-universale)

La funzione **`script.fn_get_search_detail`** implementa il **livello 2** della ricerca universale soggetti. Dato un soggetto e un tipo ruolo, restituisce un JSONB con tutte le righe specifiche di quel soggetto per il ruolo richiesto, pensato per la row expansion nella tabella di ricerca.

---
### 🎯 Scopo Principale
* **Dettaglio per tipo ruolo**: la funzione usa un `CASE` sul `codice_interno` del tipo ruolo (immutabile, protetto da `trgfn_lock_columns`) per costruire sezioni specifiche. Gestisce CL (cliente), FO (fornitore) con logica diretta, e delega tutti gli altri ruoli a `fn_get_entita_ruolo_detail`.

* **Lazy loading**: il livello 2 viene invocato solo quando l'utente espande una riga nella tabella del livello 1. Questo evita join pesanti nella query principale di ricerca.

* **Filtro per utility**: il parametro opzionale `p_utility_id` filtra le righe cliente per una utility specifica. Per il ramo ELSE viene passato a `fn_get_entita_ruolo_detail`.

* **Output JSONB uniforme**: tutti i rami restituiscono la stessa struttura `{ tipo_ruolo: "...", righe: [...] }`, semplificando il parsing nel backend/frontend. Il campo `tipo_ruolo` contiene il `codice_interno` (es. `CL`, `FO`).

* **Ampliabile**: per aggiungere un nuovo tipo ruolo basta aggiungere un ramo `WHEN` al `CASE`, senza modificare il livello 1 ne' la struttura di output.

---

### Parametri di Input

| Nome              | Tipo       | Obbligatorio | Default | Descrizione                                                                  |
| ----------------- | ---------- | ------------ | ------- | ---------------------------------------------------------------------------- |
| `p_soggetto_id`   | `UUID`     | Si           | —       | UUID del soggetto da `anagrafiche.soggetti`                                  |
| `p_tipo_ruolo_id` | `INTEGER`  | Si           | —       | ID tipo ruolo da `config.tipi_ruoli` (> 0)                                   |
| `p_utility_id`    | `INTEGER`  | No           | `NULL`  | Filtra righe CL per utility; passato a `fn_get_entita_ruolo_detail` per ELSE |
| `p_emittente_ids` | `BIGINT[]` | No           | `NULL`  | Scope emittente: soggetto_ruolo_id emittenti (solo CL)                       |

**Guard**: `p_soggetto_id` e `p_tipo_ruolo_id` validati tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`. Se il `tipo_ruolo_id` non esiste in `config.tipi_ruoli`, viene lanciato `E_TIPO_RUOLO_NON_TROVATO` (fix 2026-04-10, era `E_GENERICO`).

---

### Valore di Ritorno

La funzione restituisce un singolo valore **JSONB** con struttura fissa:

```json
{
  "tipo_ruolo": "CL",
  "righe": [ ... ]
}
```

Il contenuto di `righe` varia per tipo ruolo:

#### CL (Cliente)

Ogni elemento dell'array rappresenta una riga cliente (un record `anagrafiche.clienti`):

| Campo                 | Tipo      | Fonte                                                  |
| --------------------- | --------- | ------------------------------------------------------ |
| `cliente_id`          | `BIGINT`  | `anagrafiche.clienti.id`                               |
| `soggetto_ruolo_id`   | `BIGINT`  | `anagrafiche.clienti.soggetto_ruolo_id`                |
| `codice`              | `VARCHAR` | `anagrafiche.billing_account.codice`                   |
| `istanza_codice`      | `VARCHAR` | `anagrafiche.istanze_utilities.codice`                 |
| `istanza_id`          | `BIGINT`  | `anagrafiche.istanze_utilities.id`                     |
| `utility_id`          | `INTEGER` | `config.utilities.id`                                  |
| `utility_codice`      | `VARCHAR` | `config.utilities.codice_interno`                      |
| `utility_descrizione` | `VARCHAR` | `config.utilities.descrizione`                         |
| `stato_cliente_id`    | `INTEGER` | `config.stati_cliente.id`                              |
| `stato_codice`        | `CHAR`    | `config.stati_cliente.codice_interno`                  |
| `stato_descrizione`   | `CHAR`    | `config.stati_cliente.descrizione_breve`               |
| `stato_macro`         | `CHAR`    | `config.stati_cliente.codice` (AT/IS/SM/CH/AN)         |
| `indirizzo`           | `TEXT`    | `vw_indirizzi_dettaglio` o fallback `fn_get_indirizzo` |
| `comune`              | `TEXT`    | `vw_indirizzi_dettaglio` o fallback `fn_get_indirizzo` |
| `data_attivazione`    | `DATE`    | `anagrafiche.clienti.data_attivazione`                 |
| `data_sospensione`    | `DATE`    | `anagrafiche.clienti.data_sospensione`                 |
| `data_riattivazione`  | `DATE`    | `anagrafiche.clienti.data_riattivazione`               |
| `data_chiusura`       | `DATE`    | `anagrafiche.clienti.data_chiusura`                    |

Ordinamento: `utility_codice`, `stato_descrizione`. Filtrato da `p_utility_id` se fornito.

#### FO (Fornitore)

| Campo               | Tipo      | Fonte                                     |
| ------------------- | --------- | ----------------------------------------- |
| `fornitore_id`      | `BIGINT`  | `anagrafiche.fornitori.id`                |
| `soggetto_ruolo_id` | `BIGINT`  | `anagrafiche.fornitori.soggetto_ruolo_id` |
| `codice`            | `VARCHAR` | `anagrafiche.fornitori.codice`            |
| `attivo`            | `BOOLEAN` | `anagrafiche.fornitori.attivo`            |
| `stato_descrizione` | `TEXT`    | Derivato: `'ATTIVO'` o `'INATTIVO'`       |
| `indirizzo`         | `TEXT`    | `fn_get_indirizzo(SEDEOP)` con fallback   |
| `comune`            | `TEXT`    | `fn_get_indirizzo(SEDEOP)` con fallback   |

#### ELSE (tutti gli altri ruoli)

| Campo               | Tipo     | Fonte                                             |
| ------------------- | -------- | ------------------------------------------------- |
| `soggetto_ruolo_id` | `BIGINT` | `anagrafiche.soggetti_ruoli.id`                   |
| `soggetto_id`       | `UUID`   | `anagrafiche.soggetti_ruoli.soggetto_id`          |
| `indirizzo`         | `TEXT`   | `fn_get_indirizzo(RES)` con fallback              |
| `comune`            | `TEXT`   | `fn_get_indirizzo(RES)` con fallback              |
| `entita_detail`     | `JSONB`  | `fn_get_entita_ruolo_detail(sr.id, p_utility_id)` |

Il campo `entita_detail` contiene i dati specifici dell'entita' (EF, VT, GE, BANK_B, RIS_UMANA, ecc.) restituiti da `fn_get_entita_ruolo_detail`.

Se nessuna riga corrisponde, `righe` e' un array vuoto `[]`.

---

### Strategia di Join (CL)

```text
soggetti_ruoli sr
  INNER JOIN clienti cl                 ON cl.soggetto_ruolo_id = sr.id
  INNER JOIN stati_cliente sc           ON sc.id = cl.stato_cliente_id
  LEFT  JOIN billing_account ba         ON ba.id = cl.billing_account_id
  LEFT  JOIN istanze_utilities iu       ON iu.id = cl.istanza_utility_id
  LEFT  JOIN utilities u                ON u.id = cl.utility_id
  LEFT  JOIN vw_indirizzi_dettaglio idv ON idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
  LEFT  JOIN LATERAL fn_get_indirizzo(sr.id, 'RES') fb_ind
    ON iu.indirizzo_dettaglio_id IS NULL
WHERE sr.soggetto_id = p_soggetto_id
  AND sr.tipo_ruolo_id = p_tipo_ruolo_id
  AND (p_utility_id IS NULL OR cl.utility_id = p_utility_id)
  AND (p_emittente_ids IS NULL
       OR script.fn_check_ba_visible_for_emittenti(
            cl.billing_account_id, p_emittente_ids
          )
  )
```

Il filtro scope emittente si applica solo nel ramo CL. Per FO e ELSE il parametro `p_emittente_ids` viene ignorato. Semantica: `NULL` = nessuna restrizione, array = filtra, `'{}'` = zero risultati.

> **Logica a 3 livelli (fix 2026-04-10)**: il filtro scope emittente e' delegato a [`script.fn_check_ba_visible_for_emittenti`](/dbzero/script/funzioni/fn_check_ba_visible_for_emittenti) che opera con precedenza:
>
> 1. **Mapping specifico**: il BA del cliente ha una riga in `emittenti_fiscali_billing_account` collegata a uno degli emittenti autorizzati → il cliente e' visibile.
> 2. **Fallback default**: un emittente autorizzato ha `is_default = true` (gestore globale) **E** il BA del cliente non ha alcun mapping specifico su nessun emittente → il cliente e' visibile (il gestore globale "copre" i BA non ancora mappati).
> 3. Se ne' il mapping specifico ne' il fallback default matchano, il cliente e' escluso.
>
> Allineamento a `clienti_repository.list_clienti` lato Python. Stessa funzione usata anche da `fn_search_soggetti_universale`.

---

### Esempi di Utilizzo

```sql
-- 1) Dettaglio cliente per row expansion (tutte le utility)
SELECT script.fn_get_search_detail(
  'a1b2c3d4-...'::uuid, 1
);

-- 2) Dettaglio cliente filtrato per utility
SELECT script.fn_get_search_detail(
  'a1b2c3d4-...'::uuid, 1, 5
);

-- 3) Dettaglio fornitore
SELECT script.fn_get_search_detail(
  'a1b2c3d4-...'::uuid, 2
);

-- 4) Uso nel backend (Python)
-- cursor.execute(
--   "SELECT script.fn_get_search_detail(%s, %s, %s)",
--   [soggetto_id, tipo_ruolo_id, utility_id]
-- )
-- result = cursor.fetchone()[0]  # JSONB -> dict Python
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati.
* **Linguaggio**: PL/pgSQL
* **Tipi parametri**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Dispatch**: `CASE` su `codice_interno` (immutabile, protetto da `trgfn_lock_columns`). Valori: `'CL'`, `'FO'`, ELSE.
* **Delegazione**: il ramo ELSE delega i dati entita' a `fn_get_entita_ruolo_detail`.
* **Ampliabilita'**: aggiungere un ramo `WHEN` al `CASE` per supportare nuovi tipi ruolo con logica specifica.

---
