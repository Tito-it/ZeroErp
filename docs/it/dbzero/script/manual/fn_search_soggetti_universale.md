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
[Contesto Globale Ricerca Universale](/dev/work-done/frontend/contesto-globale-ricerca-universale)

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
| `emittente_ragione_sociale`| `TEXT`    | **Dal 18-08-2026 (R-5)** — emittenti presso cui il soggetto è cliente, **aggregati**; `NULL` sui ruoli non-CL |

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
    LEFT JOIN soggetti_ruoli sr_ef                       -- R-5 (18-08-2026)
           ON sr_ef.id = fn_get_ba_emittente_sr_id(cl.billing_account_id)
          AND ($5 IS NULL OR sr_ef.id = ANY($5))         -- <- filtrata dallo scope
    LEFT JOIN soggetti s_ef     ON s_ef.id = sr_ef.soggetto_id
  GROUP BY (tutti i campi filtered)
  -- string_agg su utility_list E su emittente_ragione_sociale

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

⚠️ **Dal 2026-08-18 il parametro NON decide piu' da solo.** La funzione risolve
lo scope **da se'**, dalla GUC `app.current_user_id` via
`script.fn_get_emittenti_scope_sr_effettivo`, e `p_emittente_ids` puo' solo
**RESTRINGERE**: nessun valore passato dal chiamante puo' allargare cio' che la
funzione mostra. Prima il filtro si accendeva su `p_emittente_ids IS NOT NULL`,
quindi `NULL` valeva «nessuna restrizione» — ed e' cio' in cui Python appiattisce
la lista vuota, che significa l'opposto.

* **`NULL`** = nessuna restrizione **richiesta dal chiamante** (vale lo scope di
  diritto: universo per il super admin, la sua whitelist per l'operatore)
* **Array valorizzato** = mostra solo clienti il cui billing_account e' collegato a uno degli emittenti autorizzati
* **`'{}'::bigint[]`** = nessun accesso (zero risultati)

I valori sono `soggetto_ruolo_id` degli emittenti fiscali, come ritornati da `script.fn_get_emittenti_scope_sr_ids(auth_user_id)`.

La catena di join per il filtro:

```text
soggetti_ruoli.id
  → clienti.soggetto_ruolo_id
  → clienti.billing_account_id
  → script.fn_check_ba_visible_for_emittenti(ba_id, p_emittente_ids)
```

> **Logica a 3 livelli (fix 2026-04-10)**: il filtro scope emittente e' delegato a [`script.fn_check_ba_visible_for_emittenti`](/dbzero/script/funzioni/fn_check_ba_visible_for_emittenti) che opera con precedenza:
>
> 1. **Mapping specifico**: il BA ha una riga in `emittenti_fiscali_billing_account` collegata a uno degli emittenti autorizzati → visibile.
> 2. **Fallback default**: un emittente autorizzato ha `is_default = true` (gestore globale) **E** il BA non ha alcun mapping specifico → visibile.
> 3. Altrimenti non visibile.
>
> Stessa funzione usata anche da `fn_get_search_detail`. Allineamento a `clienti_repository.list_clienti` lato Python.

Per ruoli non-CL (FO, EF, VT, ...) il parametro viene ignorato.

---

### L'emittente nella riga *(R-5, dal 18-08-2026)*

La colonna `emittente_ragione_sociale` esiste per un caso concreto:

> Due clienti **omonimi**, di due emittenti diversi, sono a video **due righe
> identiche**. Chi cerca ne sceglie una e non ha modo di sapere quale.

L'etichetta di perimetro che il frontend mostra sopra i risultati (*«stai
cercando in tutti gli emittenti»*) dichiara **dove** si sta cercando, ma non
distingue le due righe. Serve il dato **nella** riga.

#### ⚠️ È aggregata, e non è una scelta di comodo

Un soggetto può avere billing account sotto **più** emittenti — sull'istanza di
sviluppo era già vero per 1 cliente su 7. L'alternativa (una riga per emittente)
è stata scartata perché sarebbe **concettualmente sbagliata**:

> **La riga della ricerca è un soggetto, e un soggetto NON ha un emittente.**
> Il legame è solo transitivo, via billing account — vedi
> [soggetti-e-ruoli-anagrafici §5a-bis](/guide/soggetti-e-ruoli-anagrafici).

Moltiplicare i soggetti per una proprietà che non è loro romperebbe anche
`total_count`, che oggi conta soggetti.

#### ⚠️ Ne segue che l'etichetta a video non può essere «Emittente»

Su una riga-soggetto quella colonna mostra una **relazione**, non un attributo.
Chiamarla «Emittente» insegnerebbe un modello falso: *«Emittenti presso cui è
cliente»*, o simile. È una scelta di frontend, ma nasce da un vincolo di dominio.

#### ⚠️ La colonna è filtrata dallo scope, non solo la riga

È il punto meno ovvio. Non basta che la **riga** sia visibile: se un soggetto è
cliente di A e di B, e chi guarda ha in whitelist il solo A, la riga si vede (via
A) ma la colonna deve dire **«A»**, non «A, B». Altrimenti una colonna nata per
disambiguare finirebbe per rivelare l'esistenza di un emittente **fuori
perimetro**.

Con scope `NULL` (super admin) il filtro non morde e si vedono tutti: è
esattamente il caso per cui la colonna è stata chiesta.

#### `NULL` sui rami non-CL è la risposta giusta

Un fornitore non ha billing account, quindi non ha emittente. La funzione non ne
inventa uno; il frontend mostra l'etichetta solo dove il valore c'è.

#### Non è ordinabile

`emittente_ragione_sociale` **non** è nella whitelist di `p_order_by`, ed è
voluto: è un aggregato, quindi ordinarci sopra ordinerebbe per la *stringa
concatenata* — non per emittente. Se un giorno servirà, sarà una decisione di
merito, non un'aggiunta meccanica alla lista.

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

* **Volatilita'**: `STABLE`. ⚠️ `PARALLEL SAFE` è stato **tolto il 18-08-2026**: la
  funzione chiama `fn_get_emittenti_scope_sr_effettivo`, che è `STABLE` e basta —
  tenerla `SAFE` sarebbe stata una dichiarazione falsa al planner. Il costo reale è
  ~zero: la query dinamica interna resta parallelizzabile, perché lo scope si
  risolve **prima**, in una variabile, e non dentro la query.
* **Linguaggio**: PL/pgSQL
* **SQL dinamico**: `RETURN QUERY EXECUTE` con `format()` per il frammento EXISTS. La tabella e' validata come `regclass` dal trigger guard su `tipi_ruoli`.
* **Tipi colonne**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Ampliabilita'**: per aggiungere ricerca codice a un nuovo tipo ruolo, basta un UPDATE su `tipi_ruoli.entita_tabella` — zero modifiche SQL.

---
