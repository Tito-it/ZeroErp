## Documentazione Concettuale -- Funzione `script.fn_search_soggetti_universale`

> Vedi anche
>
Approfondimento tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [anagrafiche.vw_clienti_codice_ba](/dbzero/anagrafiche/views/vw_clienti_codice_ba)
>
Funzione complementare (livello 2):
>
[script.fn_get_search_detail](/dbzero/script/funzioni/fn_get_search_detail)
>
Funzione dati entita':
>
[script.fn_get_entita_ruolo_detail](/dbzero/script/funzioni/fn_get_entita_ruolo_detail)
>
Documento di design:
>
[Contesto Globale Ricerca Universale](/dev/work-in-progress/frontend/contesto-globale-ricerca-universale)

La funzione **`script.fn_search_soggetti_universale`** implementa il **livello 1** della ricerca universale soggetti. Dato un termine di ricerca e un tipo ruolo, restituisce una lista paginata di soggetti con i dati essenziali per la visualizzazione in tabella.

---
### 🎯 Scopo Principale
* **Ricerca per tipo ruolo**: il parametro `p_tipo_ruolo_id` e' obbligatorio. Il dropdown frontend mostra solo i ruoli accessibili all'utente corrente.

* **Ricerca multi-campo**: la ricerca opera su 4 campi con pattern `%termine%` (ILIKE + GIN trgm):
  1. `ragione_sociale_completa` — nome/ragione sociale del soggetto
  2. `id_fiscale_univoco_cf_piva` — codice fiscale o P.IVA
  3. `codice` soggetto — codice univoco generato
  4. **codice entita' dinamico** — codice specifico del tipo ruolo (es. billing_account per CL, codice fornitore per FO), configurato in `tipi_ruoli.entita_tabella`

* **Ricerca codice entita' dinamica**: la tabella e la colonna del codice entita' sono letti da `config.tipi_ruoli.entita_tabella` e `entita_colonna_codice`. Se `entita_tabella` e' NULL per un tipo ruolo, la ricerca per codice entita' non viene eseguita. La query usa `RETURN QUERY EXECUTE` con `format()` per costruire dinamicamente il frammento `EXISTS`.

* **Paginazione integrata**: `LIMIT/OFFSET` + `COUNT(*) OVER()` in una singola query. Il conteggio totale e' restituito su ogni riga tramite window function.

* **Hard cap 10.000**: una CTE iniziale limita i risultati filtrati a 10.000 righe per proteggere le performance.

* **Utility aggregate**: per i soggetti con ruolo CLIENTE, aggrega i codici utility (`string_agg(DISTINCT u.codice_interno)`). Per altri ruoli la colonna `utility_list` e' `NULL`.

---

### Parametri di Input

| Nome              | Tipo       | Obbligatorio | Default | Descrizione                                            |
| ----------------- | ---------- | ------------ | ------- | ------------------------------------------------------ |
| `p_search_term`   | `TEXT`     | Si           | —       | Testo di ricerca (minimo 3 caratteri)                  |
| `p_tipo_ruolo_id` | `INTEGER`  | Si           | —       | ID tipo ruolo da `config.tipi_ruoli` (> 0)             |
| `p_emittente_ids` | `BIGINT[]` | No           | `NULL`  | Scope emittente: soggetto_ruolo_id emittenti (solo CL) |
| `p_limit`         | `INTEGER`  | No           | `50`    | Righe per pagina (max 200, cap automatico)             |
| `p_offset`        | `INTEGER`  | No           | `0`     | Offset paginazione                                     |
| `p_order_by`      | `TEXT`     | No           | `NULL`  | Colonna di ordinamento (whitelist, vedi sotto)         |
| `p_order_dir`     | `TEXT`     | No           | `'ASC'` | Direzione ordinamento: `ASC` o `DESC`                  |

**Guard**: `p_tipo_ruolo_id` e `p_search_term` sono validati tramite `script.fn_log_and_raise_error` con codice `E_PARAMETRO_INVALIDO`. Anche `p_order_by` e' validato: se fornito e non nella whitelist, lancia `E_PARAMETRO_INVALIDO`.

---

### Valore di Ritorno

La funzione restituisce una tabella (`RETURNS TABLE`) con le seguenti colonne:

| Colonna                    | Tipo      | Fonte / Note                                       |
| -------------------------- | --------- | -------------------------------------------------- |
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

### Strategia Query (3 CTE + SQL Dinamico)

```text
-- Risoluzione dinamica (una volta sola, prima della query):
SELECT entita_tabella, entita_colonna_codice
FROM config.tipi_ruoli WHERE id = p_tipo_ruolo_id

-- Se entita_tabella IS NOT NULL, costruisce:
v_exists_clause = 'OR EXISTS (SELECT 1 FROM <tabella> e
                    WHERE e.soggetto_ruolo_id = sr.id
                    AND e.<colonna> ILIKE $2)'

-- Query principale via RETURN QUERY EXECUTE:
filtered (CTE 1)
  soggetti_ruoli sr
    INNER JOIN soggetti s       ON s.id = sr.soggetto_id
  WHERE tipo_ruolo_id = $1
    AND s.attivo = true
    AND (ragione_sociale ILIKE $2
         OR id_fiscale ILIKE $2
         OR codice ILIKE $2
         <v_exists_clause>)       -- dinamico
  LIMIT 10.000  (hard cap)

with_utility (CTE 2)
  filtered f
    LEFT JOIN clienti cl        ON cl.soggetto_ruolo_id = f.soggetto_ruolo_id
    LEFT JOIN utilities u       ON u.id = cl.utility_id
  GROUP BY (tutti i campi filtered)

paged (CTE 3)
  COUNT(*) OVER() + ORDER BY dinamico + LIMIT/OFFSET
  -- ORDER BY costruito da p_order_by/p_order_dir
  -- con tie-breaker su soggetto_ruolo_id
```

---

### Ricerca Codice Entita' Dinamica

La mappatura tra tipo ruolo e tabella codice e' configurata in `config.tipi_ruoli`:

| codice_interno | entita_tabella                     | entita_colonna_codice | Note                                |
| -------------- | ---------------------------------- | --------------------- | ----------------------------------- |
| CL             | `anagrafiche.vw_clienti_codice_ba` | NULL (default codice) | Codice da billing_account via vista |
| FO             | `anagrafiche.fornitori`            | NULL (default codice) | Codice fornitore                    |
| EF             | `anagrafiche.emittenti_fiscali`    | NULL (default codice) | Codice emittente                    |
| VT             | `anagrafiche.vettori`              | NULL (default codice) | Codice vettore                      |
| BANK_B         | `anagrafiche.bank_branches`        | `bank_code`           | Codice banca                        |
| GE             | NULL                               | NULL                  | Nessuna ricerca codice              |
| RIS_UMANA      | NULL                               | NULL                  | Nessuna ricerca codice              |

La validazione e' garantita dal trigger `trg_tipi_ruoli_a10_guard_entita_ref_ins_upd` che verifica: regclass valido, colonna `soggetto_ruolo_id` presente, colonna codice presente.

Per aggiungere un nuovo tipo ruolo con ricerca codice: INSERT/UPDATE su `tipi_ruoli` con `entita_tabella` e opzionalmente `entita_colonna_codice`. Nessuna modifica al codice SQL.

---

### Filtro Scope Emittente

Il parametro `p_emittente_ids` filtra i risultati in base agli emittenti fiscali autorizzati. Si applica **solo per tipo ruolo CL** (clienti).

* **`NULL`** = nessuna restrizione (ADMIN o utente senza scope)
* **Array valorizzato** = mostra solo clienti il cui billing_account e' collegato a uno degli emittenti autorizzati
* **`'{}'::bigint[]`** = nessun accesso (zero risultati)

I valori sono `soggetto_ruolo_id` degli emittenti fiscali, come ritornati da `script.fn_get_emittenti_scope_sr_ids(auth_user_id)`.

La catena di join per il filtro:

```text
soggetti_ruoli.id
  → clienti.soggetto_ruolo_id
  → clienti.billing_account_id
  → emittenti_fiscali_billing_account.billing_account_id
  → emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id = ANY(p_emittente_ids)
```

Per ruoli non-CL (FO, EF, VT, ...) il parametro viene ignorato.

---

### Ordinamento Dinamico

L'ordinamento e' controllato dai parametri `p_order_by` e `p_order_dir`:

* **`p_order_by`**: nome colonna dalla whitelist. Se NULL, default `ragione_sociale_completa`.
* **`p_order_dir`**: `ASC` (default) o `DESC`. Qualsiasi altro valore viene normalizzato a `ASC`.

Colonne ordinabili (whitelist):

| Colonna                    | Descrizione                        |
| -------------------------- | ---------------------------------- |
| `ragione_sociale_completa` | Nome/ragione sociale (default)     |
| `soggetto_codice`          | Codice univoco soggetto            |
| `id_fiscale_univoco`       | Codice fiscale / P.IVA             |
| `utility_list`             | Codici utility aggregati (solo CL) |

L'ordinamento usa `format('%I %s')` per quotare il nome colonna e previene SQL injection. Tie-breaker su `soggetto_ruolo_id ASC` per ordinamento stabile.

---

### Indici Utilizzati

| Indice                                      | Tabella                         | Tipo     | Scopo                     |
| ------------------------------------------- | ------------------------------- | -------- | ------------------------- |
| `ix_soggetti_ragione_sociale_completa_trgm` | `anagrafiche.soggetti`          | GIN trgm | ILIKE su ragione_sociale  |
| `ix_soggetti_id_fiscale_univoco_trgm`       | `anagrafiche.soggetti`          | GIN trgm | ILIKE su id_fiscale       |
| `ix_soggetti_codice_trgm`                   | `anagrafiche.soggetti`          | GIN trgm | ILIKE su codice soggetto  |
| `ix_billing_account_codice_trgm`            | `anagrafiche.billing_account`   | GIN trgm | ILIKE su codice BA (CL)   |
| `ix_fornitori_codice_trgm`                  | `anagrafiche.fornitori`         | GIN trgm | ILIKE su codice fornitore |
| `ix_emittenti_fiscali_codice_trgm`          | `anagrafiche.emittenti_fiscali` | GIN trgm | ILIKE su codice EF        |
| `ix_vettori_codice_trgm`                    | `anagrafiche.vettori`           | GIN trgm | ILIKE su codice vettore   |
| `ix_bank_branches_bank_code_trgm`           | `anagrafiche.bank_branches`     | GIN trgm | ILIKE su bank_code        |

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

-- 3) Ricerca clienti per codice billing_account
SELECT * FROM script.fn_search_soggetti_universale(
  'BA-001', 1, NULL, 50, 0
);

-- 4) Ricerca banche per bank_code
SELECT * FROM script.fn_search_soggetti_universale(
  '03069', 9, NULL, 50, 0
);

-- 5) Seconda pagina (offset 50)
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, NULL, 50, 50
);

-- 6) Ordinamento per codice soggetto, discendente
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, NULL, 50, 0, 'soggetto_codice', 'DESC'
);

-- 7) Ordinamento per id_fiscale_univoco, ascendente
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, NULL, 50, 0, 'id_fiscale_univoco', 'ASC'
);
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati, puo' essere parallelizzata.
* **Linguaggio**: PL/pgSQL
* **SQL dinamico**: `RETURN QUERY EXECUTE` con `format()` per il frammento EXISTS. La tabella e' validata come `regclass` dal trigger guard su `tipi_ruoli`.
* **Tipi colonne**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Ampliabilita'**: per aggiungere ricerca codice a un nuovo tipo ruolo, basta un UPDATE su `tipi_ruoli.entita_tabella` — zero modifiche SQL.

---
