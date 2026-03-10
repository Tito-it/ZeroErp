## Documentazione Concettuale -- Funzione `script.fn_get_search_detail`

> Vedi anche
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
> * [config.utilities](/dbzero/config/tabelle/utilities)
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)
>
> Funzione complementare (livello 1):
>
> * [script.fn_search_soggetti_universale](/dbzero/script/funzioni/fn_search_soggetti_universale)
>
> Documento di design:
>
> * [Contesto Globale Ricerca Universale](/dev/work-in-progress/frontend/contesto-globale-ricerca-universale)

La funzione **`script.fn_get_search_detail`** implementa il **livello 2** della ricerca universale soggetti. Dato un soggetto e un tipo ruolo, restituisce un JSONB con tutte le righe specifiche di quel soggetto per il ruolo richiesto, pensato per la row expansion nella tabella di ricerca.

---

### Scopo Principale

* **Dettaglio per tipo ruolo**: la funzione usa un `CASE` sul `codice_interno` del tipo ruolo per costruire sezioni specifiche. Attualmente gestisce CLIENTE, FORNITORE e un caso generico per tutti gli altri ruoli.

* **Lazy loading**: il livello 2 viene invocato solo quando l'utente espande una riga nella tabella del livello 1. Questo evita join pesanti nella query principale di ricerca.

* **Output JSONB uniforme**: tutti i rami restituiscono la stessa struttura `{ tipo_ruolo: "...", righe: [...] }`, semplificando il parsing nel backend/frontend.

* **Ampliabile**: per aggiungere un nuovo tipo ruolo basta aggiungere un ramo `WHEN` al `CASE`, senza modificare il livello 1 ne' la struttura di output. Sezioni aggiuntive (contratti, saldi, PDR/POD) possono essere aggiunte all'interno di ogni ramo.

---

### Parametri di Input

| Nome              | Tipo      | Obbligatorio | Descrizione                                    |
| ----------------- | --------- | ------------ | ---------------------------------------------- |
| `p_soggetto_id`   | `UUID`    | Si           | UUID del soggetto da `anagrafiche.soggetti`    |
| `p_tipo_ruolo_id` | `INTEGER` | Si           | ID tipo ruolo da `config.tipi_ruoli` (> 0)     |

**Guard**: entrambi validati tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`. Se il `tipo_ruolo_id` non esiste in `config.tipi_ruoli`, viene lanciato `E_GENERICO`.

---

### Valore di Ritorno

La funzione restituisce un singolo valore **JSONB** con struttura fissa:

```json
{
  "tipo_ruolo": "CLIENTE",
  "righe": [ ... ]
}
```

Il contenuto di `righe` varia per tipo ruolo:

#### CLIENTE

Ogni elemento dell'array rappresenta una riga cliente (un record `anagrafiche.clienti`):

| Campo               | Tipo      | Fonte                                       |
| ------------------- | --------- | ------------------------------------------- |
| `cliente_id`        | `BIGINT`  | `anagrafiche.clienti.id`                    |
| `soggetto_ruolo_id` | `BIGINT`  | `anagrafiche.clienti.soggetto_ruolo_id`     |
| `istanza_codice`    | `VARCHAR` | `anagrafiche.istanze_utilities.codice`      |
| `istanza_id`        | `BIGINT`  | `anagrafiche.istanze_utilities.id`          |
| `utility_id`        | `INTEGER` | `config.utilities.id`                       |
| `utility_codice`    | `VARCHAR` | `config.utilities.codice_interno`           |
| `stato_cliente_id`  | `INTEGER` | `config.stati_cliente.id`                   |
| `stato_codice`      | `CHAR`    | `config.stati_cliente.codice_interno`       |
| `stato_descrizione` | `CHAR`    | `config.stati_cliente.descrizione_breve`    |
| `stato_macro`       | `CHAR`    | `config.stati_cliente.codice` (AT/IS/SM/CH/AN) |
| `indirizzo`         | `TEXT`    | `vw_indirizzi_dettaglio.indirizzo_normalizzato` |
| `comune`            | `TEXT`    | `vw_indirizzi_dettaglio.descrizione_comune` |
| `data_attivazione`  | `DATE`    | `anagrafiche.clienti.data_attivazione`      |
| `data_chiusura`     | `DATE`    | `anagrafiche.clienti.data_chiusura`         |

Ordinamento: `utility_codice`, `stato_descrizione`.

#### FORNITORE

| Campo               | Tipo      | Fonte                                    |
| ------------------- | --------- | ---------------------------------------- |
| `fornitore_id`      | `BIGINT`  | `anagrafiche.fornitori.id`               |
| `soggetto_ruolo_id` | `BIGINT`  | `anagrafiche.fornitori.soggetto_ruolo_id`|
| `codice`            | `VARCHAR` | `anagrafiche.fornitori.codice`           |
| `attivo`            | `BOOLEAN` | `anagrafiche.fornitori.attivo`           |
| `stato_operativo`   | `VARCHAR` | `anagrafiche.fornitori.stato_operativo`  |
| `stato_descrizione` | `TEXT`    | Derivato: `'ATTIVO'` o `'INATTIVO'`     |

#### Generico (altri ruoli)

| Campo               | Tipo      | Fonte                                     |
| ------------------- | --------- | ----------------------------------------- |
| `soggetto_ruolo_id` | `BIGINT`  | `anagrafiche.soggetti_ruoli.id`           |
| `soggetto_id`       | `UUID`    | `anagrafiche.soggetti_ruoli.soggetto_id`  |
| `meta`              | `JSONB`   | `anagrafiche.soggetti_ruoli.meta`         |
| `data_insert`       | `TIMESTAMPTZ` | `anagrafiche.soggetti_ruoli.data_insert` |

Se nessuna riga corrisponde, `righe` e' un array vuoto `[]`.

---

### Strategia di Join (CLIENTE)

```text
soggetti_ruoli sr
  INNER JOIN clienti cl                 ON cl.soggetto_ruolo_id = sr.id
  INNER JOIN stati_cliente sc           ON sc.id = cl.stato_cliente_id
  LEFT  JOIN istanze_utilities iu       ON iu.id = cl.istanza_utility_id
  LEFT  JOIN utilities u                ON u.id = cl.utility_id
  LEFT  JOIN vw_indirizzi_dettaglio idv ON idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
WHERE sr.soggetto_id = p_soggetto_id
  AND sr.tipo_ruolo_id = p_tipo_ruolo_id
```

Il JOIN a `vw_indirizzi_dettaglio` recupera indirizzo normalizzato e comune direttamente dalla view, evitando join aggiuntivi a `config.stradario` e `config.comuni`.

---

### Esempi di Utilizzo

```sql
-- 1) Dettaglio cliente per row expansion
SELECT script.fn_get_search_detail(
  'a1b2c3d4-...'::uuid, 1
);

-- 2) Dettaglio fornitore
SELECT script.fn_get_search_detail(
  'a1b2c3d4-...'::uuid, 2
);

-- 3) Uso nel backend (Python)
-- cursor.execute("SELECT script.fn_get_search_detail(%s, %s)", [soggetto_id, tipo_ruolo_id])
-- result = cursor.fetchone()[0]  # JSONB -> dict Python
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati.
* **Linguaggio**: PL/pgSQL
* **Tipi parametri**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Ampliabilita'**: aggiungere un ramo `WHEN 'NUOVO_RUOLO' THEN ...` al `CASE` per supportare nuovi tipi ruolo.

---
