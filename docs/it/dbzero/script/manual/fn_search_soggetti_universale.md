## Documentazione Concettuale -- Funzione `script.fn_search_soggetti_universale`

> Vedi anche
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> * [config.comuni](/dbzero/config/tabelle/comuni)
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> * [config.utilities](/dbzero/config/tabelle/utilities)
>
> Funzione complementare (livello 2):
>
> * [script.fn_get_search_detail](/dbzero/script/funzioni/fn_get_search_detail)
>
> Documento di design:
>
> * [Contesto Globale Ricerca Universale](/dev/work-in-progress/frontend/contesto-globale-ricerca-universale)

La funzione **`script.fn_search_soggetti_universale`** implementa il **livello 1** della ricerca universale soggetti. Dato un termine di ricerca e un tipo ruolo, restituisce una lista paginata di soggetti con i dati essenziali per la visualizzazione in tabella.

---

### Scopo Principale

* **Ricerca per tipo ruolo**: il parametro `p_tipo_ruolo_id` e' obbligatorio. Il dropdown frontend mostra solo i ruoli accessibili all'utente corrente.

* **ILIKE + pg_trgm**: la ricerca opera su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva` con pattern `%termine%`, sfruttando indici GIN trigram per performance.

* **Paginazione integrata**: `LIMIT/OFFSET` + `COUNT(*) OVER()` in una singola query. Il conteggio totale e' restituito su ogni riga tramite window function, evitando una seconda round-trip.

* **Hard cap 10.000**: una CTE iniziale limita i risultati filtrati a 10.000 righe per proteggere le performance su dataset molto grandi.

* **Utility aggregate**: per i soggetti con ruolo CLIENTE, aggrega i codici utility (`string_agg(DISTINCT u.codice_interno)`) tramite LEFT JOIN leggero. Per altri ruoli la colonna `utility_list` e' `NULL`.

---

### Parametri di Input

| Nome              | Tipo        | Obbligatorio | Default | Descrizione                                           |
| ----------------- | ----------- | ------------ | ------- | ----------------------------------------------------- |
| `p_search_term`   | `TEXT`      | Si           | —       | Testo di ricerca (minimo 3 caratteri)                 |
| `p_tipo_ruolo_id` | `INTEGER`   | Si           | —       | ID tipo ruolo da `config.tipi_ruoli` (> 0)            |
| `p_emittente_ids` | `INTEGER[]` | No           | `NULL`  | Filtro opzionale per scope emittente (da implementare)|
| `p_limit`         | `INTEGER`   | No           | `50`    | Righe per pagina (max 200, cap automatico)            |
| `p_offset`        | `INTEGER`   | No           | `0`     | Offset paginazione                                    |

**Guard**: `p_tipo_ruolo_id` e `p_search_term` sono validati tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`.

---

### Valore di Ritorno

La funzione restituisce una tabella (`RETURNS TABLE`) con le seguenti colonne:

| Colonna                    | Tipo      | Fonte / Note                                      |
| -------------------------- | --------- | ------------------------------------------------- |
| `total_count`              | `BIGINT`  | Conteggio totale via `COUNT(*) OVER()`             |
| `soggetto_id`              | `UUID`    | `anagrafiche.soggetti.id`                          |
| `soggetto_ruolo_id`        | `BIGINT`  | `anagrafiche.soggetti_ruoli.id`                    |
| `tipo_ruolo_id`            | `INTEGER` | `anagrafiche.soggetti_ruoli.tipo_ruolo_id`         |
| `soggetto_codice`          | `TEXT`    | `anagrafiche.soggetti.codice`                      |
| `ragione_sociale_completa` | `TEXT`    | `anagrafiche.soggetti.ragione_sociale_completa`    |
| `id_fiscale_univoco`       | `TEXT`    | `anagrafiche.soggetti.id_fiscale_univoco_cf_piva`  |
| `utility_list`             | `TEXT`    | `string_agg(DISTINCT codice_interno)` da utilities |

Se nessun soggetto corrisponde, la funzione restituisce **zero righe**.

---

### Strategia Query (3 CTE)

```text
filtered (CTE 1)
  soggetti_ruoli sr
    INNER JOIN soggetti s       ON s.id = sr.soggetto_id
  WHERE tipo_ruolo + ILIKE
  LIMIT 10.000  (hard cap)

with_utility (CTE 2)
  filtered f
    LEFT JOIN clienti cl        ON cl.soggetto_ruolo_id = f.soggetto_ruolo_id
    LEFT JOIN utilities u       ON u.id = cl.utility_id
  GROUP BY (tutti i campi filtered)

paged (CTE 3)
  COUNT(*) OVER() + ORDER BY + LIMIT/OFFSET
```

I LEFT JOIN su `clienti`/`utilities` nella CTE 2 producono `NULL` per ruoli diversi da CLIENTE, senza impatto sulle performance grazie al filtraggio gia' avvenuto in CTE 1.

---

### Indici Utilizzati

| Indice                                          | Tabella                  | Tipo     | Scopo                          |
| ----------------------------------------------- | ------------------------ | -------- | ------------------------------ |
| `ix_soggetti_ragione_sociale_completa_trgm`     | `anagrafiche.soggetti`   | GIN trgm | ILIKE su ragione_sociale       |
| `ix_soggetti_id_fiscale_univoco_cf_piva_trgm`   | `anagrafiche.soggetti`   | GIN trgm | ILIKE su id_fiscale            |
| `uq_soggetto_ruolo` (soggetto_id, tipo_ruolo_id)| `anagrafiche.soggetti_ruoli` | UNIQUE | Filtro tipo_ruolo_id       |

---

### Esempi di Utilizzo

```sql
-- 1) Ricerca clienti per nome, prima pagina
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, NULL, 50, 0
);

-- 2) Ricerca fornitori per P.IVA parziale
SELECT * FROM script.fn_search_soggetti_universale(
  '0123456', 2, NULL, 25, 0
);

-- 3) Seconda pagina (offset 50)
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, NULL, 50, 50
);
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati, puo' essere parallelizzata.
* **Linguaggio**: PL/pgSQL
* **Tipi colonne**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).

---
