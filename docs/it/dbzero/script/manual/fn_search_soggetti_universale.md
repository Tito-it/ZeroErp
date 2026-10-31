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
Regola unica di chi si vede (con il dettaglio):
>
[script.fn_predicato_soggetto_ruolo_visibile](/dbzero/script/funzioni/fn_predicato_soggetto_ruolo_visibile)
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

* **Ricerca multi-campo**: la ricerca opera fino a 4 campi con pattern `%termine%` (ILIKE + GIN trgm), quelli accesi da `p_campi_ricerca`:
  1. `ragione_sociale_completa` — nome/ragione sociale del soggetto
  2. `id_fiscale_univoco_cf_piva` — codice fiscale o P.IVA
  3. `codice` soggetto — codice univoco generato
  4. **codice entita' dinamico** — codice specifico del tipo ruolo (es. billing_account per CL, codice fornitore per FO), configurato in `tipi_ruoli.entita_tabella`

* **I campi li dice il catalogo** *(dal 2026-10-31)*: `p_campi_ricerca` elenca i campi su cui
  cercare, cioè i `campo_sorgente` accesi nel catalogo della lista
  `anagrafiche.ricerca_soggetti` (113). Il backend li legge da
  [ui.fn_lista_colonne_ricerca_full](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full), come per
  le altre liste: conta l'interruttore `ricercabile_full`, e una colonna a livello `BLOCCATO` per
  l'utente non si cerca, così non si può sondarla. La funzione resta cieca sullo schema `ui`.
  Campi ammessi: `soggetto_codice` (codice del soggetto **e** codice dell'entità),
  `ragione_sociale_completa` e `id_fiscale_univoco`. Un elenco vuoto non trova niente; `NULL`
  vuol dire tutti e tre. Un campo fuori elenco, o un elemento `NULL`, è un errore del chiamante
  (`E_SCRIPT_CHIAMATA_NON_VALIDA`).

* **Ricerca codice entita' dinamica**: la tabella e la colonna del codice entita' sono letti da `config.tipi_ruoli.entita_tabella` e `entita_colonna_codice`. Se `entita_tabella` e' NULL per un tipo ruolo, la ricerca per codice entita' non viene eseguita. La query usa `RETURN QUERY EXECUTE` con `format()` per costruire dinamicamente il frammento `EXISTS`.

* **Paginazione integrata**: `LIMIT/OFFSET` + `COUNT(*) OVER()` in una singola query. Il conteggio totale e' restituito su ogni riga tramite window function, ed è il totale **vero** di tutte le corrispondenze.

* **Prima la pagina, poi gli aggregati** *(dal 2026-10-10)*: conteggio, ordine e pagina si fanno sulle colonne semplici del soggetto, su tutte le corrispondenze; utility ed emittenti si calcolano solo per le righe della pagina. Non c'è più un tetto: fino al 2026-10-10 la funzione teneva al massimo 10.000 corrispondenze, scelte senza un ordine, e oltre quel numero il totale e le pagine non dicevano il vero.

* **Utility aggregate**: per i soggetti con ruolo CLIENTE, aggrega i codici utility (`string_agg(DISTINCT u.codice_interno)`). Per altri ruoli la colonna `utility_list` e' `NULL`.

---

### Parametri di Input

| Nome              | Tipo       | Obbligatorio | Default | Descrizione                                            |
| ----------------- | ---------- | ------------ | ------- | ------------------------------------------------------ |
| `p_search_term`   | `TEXT`     | Si           | —       | Testo di ricerca (minimo 3 caratteri)                  |
| `p_tipo_ruolo_id` | `INTEGER`  | Si           | —       | ID tipo ruolo da `config.tipi_ruoli` (> 0)             |
| `p_limit`         | `INTEGER`  | No           | `50`    | Righe per pagina (max 200, cap automatico)             |
| `p_offset`        | `INTEGER`  | No           | `0`     | Offset paginazione                                     |
| `p_order_by`      | `TEXT`     | No           | `NULL`  | Colonna di ordinamento (whitelist, vedi sotto)         |
| `p_order_dir`     | `TEXT`     | No           | `'ASC'` | Direzione ordinamento: `ASC` o `DESC`                  |
| `p_campi_ricerca` | `TEXT[]`   | No           | `NULL`  | Campi su cui cercare (whitelist, vedi sopra); `NULL` = tutti e tre, vuoto = nessuna riga |

**Guard**: il tipo ruolo lo valida la regola unica, la stessa del dettaglio: NULL o
`<= 0` → `E_PARAMETRO_INVALIDO`, inesistente → `E_TIPO_RUOLO_NON_TROVATO`, **non
ricercabile** (`config.tipi_ruoli.ricerca_visibile = false`) →
`E_TIPO_RUOLO_NON_RICERCABILE`. Prima del 2026-10-10 un ruolo inesistente dava zero
righe, e la ricercabilità la controllava solo il backend. `p_search_term` (minimo 3
caratteri) e `p_order_by` (whitelist) → `E_PARAMETRO_INVALIDO`.

Fino al 2026-10-10 c'era un terzo parametro, `p_emittente_ids`: dal 2026-10-08 non
si leggeva più, e il 2026-10-10 è uscito dalla firma. ⚠️ Chi chiama per posizione
deve saperlo: il terzo argomento oggi è `p_limit`.

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

### Strategia Query (2 CTE + aggregati per la pagina + SQL Dinamico)

```text
-- Risoluzione dinamica (una volta sola, prima della query):
v_predicato = fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id, 'sr')
SELECT entita_tabella, entita_colonna_codice
FROM config.tipi_ruoli WHERE id = p_tipo_ruolo_id

-- Se entita_tabella IS NOT NULL, costruisce:
v_exists_clause = 'OR EXISTS (SELECT 1 FROM <tabella> e
                    WHERE e.soggetto_ruolo_id = sr.id
                    AND e.<colonna> ILIKE $2)'

-- Query principale via RETURN QUERY EXECUTE:
r (CTE 1) -- solo colonne semplici, TUTTE le corrispondenze, nessun tetto
  soggetti_ruoli sr
    INNER JOIN soggetti s       ON s.id = sr.soggetto_id
  WHERE tipo_ruolo_id = $1
    AND (ragione_sociale ILIKE $2
         OR id_fiscale ILIKE $2
         OR codice ILIKE $2
         <v_exists_clause>)       -- dinamico
    AND <predicato della regola unica>    -- chi si vede (2026-10-10)

paged (CTE 2)
  COUNT(*) OVER()                 -- prima del LIMIT: il totale vero
  + ORDER BY dinamico             -- p_order_by/p_order_dir, tie-breaker soggetto_ruolo_id
  + LIMIT/OFFSET                  -- la pagina

risultato -- gli aggregati SOLO per le righe della pagina
  paged r
    LEFT JOIN LATERAL (
      clienti cl                  -- sotto RLS
        LEFT JOIN utilities u
        LEFT JOIN soggetti_ruoli sr_ef ON sr_ef.id = fn_get_ba_emittente_sr_id(cl.billing_account_id)
        LEFT JOIN soggetti s_ef
      WHERE cl.soggetto_ruolo_id = r.soggetto_ruolo_id
      -- string_agg su utility_list E su emittente_ragione_sociale
    ) agg ON true
  ORDER BY <lo stesso della pagina>
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

⚠️ `entita_tabella` serve **solo** a cercare il codice. Quale tabella fa esistere il
soggetto-ruolo (chi si vede) lo dice un'altra colonna, `entita_esistenza`: vedi la
sezione sotto.

Per aggiungere un nuovo tipo ruolo con ricerca codice: INSERT/UPDATE su `tipi_ruoli` con `entita_tabella` e opzionalmente `entita_colonna_codice`. Nessuna modifica al codice SQL.

---

### Chi si vede: la regola unica *(dal 2026-10-10)*

Il filtro di riga è il predicato di
[`script.fn_predicato_soggetto_ruolo_visibile`](/dbzero/script/funzioni/fn_predicato_soggetto_ruolo_visibile),
la **stessa** regola con cui il dettaglio ([`fn_get_search_detail`](/dbzero/script/funzioni/fn_get_search_detail))
decide se un soggetto c'è. Lista e dettaglio non possono dissentire su chi si vede.

La regola legge il catalogo dei ruoli e non nomina nessun ruolo:

* il ruolo ha `config.tipi_ruoli.entita_esistenza` (cliente → `clienti`, fornitore →
  `fornitori`, vettore → `vettori`, banca → `bank_branches`): il soggetto-ruolo si
  mostra se ha **almeno una riga di quella tabella** che chi guarda vede;
* il ruolo non ce l'ha (reseller, distributore, venditore): si mostra se il
  soggetto-ruolo esiste.

Il ruolo è uno per chiamata, quindi la regola si risolve **una volta** e il predicato
entra nell'SQL dinamico della query: non c'è una verifica per ogni riga.

**Lo stato dell'entità non conta**: un cliente chiuso o un fornitore disattivato si
trovano. Nemmeno `soggetti.attivo`: il modello non ammette un soggetto-ruolo con il
soggetto disattivato (non si spegne un soggetto che ha ruoli, non si dà un ruolo a un
soggetto spento), e il filtro che c'era non poteva scattare.

**Il perimetro dei clienti lo fa la RLS** di `anagrafiche.clienti`. La policy
dell'operatore (`rls_clienti_ef_whitelist`) risale dal billing account con la stessa
regola della testata: mapping specifico, poi riserva — vedi
[`script.fn_check_ba_visible_for_emittenti`](/dbzero/script/funzioni/fn_check_ba_visible_for_emittenti).
Il super admin vede tutti gli emittenti; l'emittente attivo restringe. Fornitori,
vettori e banche non hanno RLS: per loro «visibile» vuol dire «esiste».

⚠️ Un cliente senza **nessun** cliente, o un fornitore senza la sua riga in
`fornitori`, non compare a nessuno, nemmeno al super admin: il dettaglio lo direbbe
«non trovato».

**Com'era prima.** Dal 2026-08-18 al 2026-10-08 la funzione risolveva lo scope
emittente da sé e filtrava i clienti a mano, con un parametro `p_emittente_ids` che
poteva solo restringere: era nato quando `clienti` non aveva RLS, e con la RLS armata
(2026-09-10) era diventato una seconda copia della regola della policy. Dal
2026-10-08 al 2026-10-10 la regola di chi si vede nominava il ruolo cliente per nome,
e un fornitore senza la sua riga compariva.

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

#### ⚠️ La colonna è filtrata dal perimetro, non solo la riga

È il punto meno ovvio. Non basta che la **riga** sia visibile: se un soggetto è
cliente di A e di B, e chi guarda ha in whitelist il solo A, la riga si vede (via
A) ma la colonna deve dire **«A»**, non «A, B». Altrimenti una colonna nata per
disambiguare finirebbe per rivelare l'esistenza di un emittente **fuori
perimetro**.

Dal 2026-10-08 lo fa la RLS di `anagrafiche.clienti` sulla `LEFT JOIN`: un
cliente fuori perimetro non entra nella join, e quindi nemmeno il suo emittente
entra nell'aggregato. Il super admin vede tutti gli emittenti: è esattamente il
caso per cui la colonna è stata chiesta.

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

⚠️ **`utility_list` non è ordinabile dal 2026-10-10** (decisione di Tid): è un
aggregato, e ordinare per un aggregato vorrebbe calcolarlo su tutte le
corrispondenze, cioè proprio il lavoro che ora si fa solo per la pagina. Chiederlo
dà `E_PARAMETRO_INVALIDO`. L'ordine di una lista di forniture concatenate dice poco,
e la fornitura si filtra nel dettaglio. Per la stessa ragione non è ordinabile
`emittente_ragione_sociale`.

L'ordinamento usa `format('%I %s')` per quotare il nome colonna e previene SQL injection. Tie-breaker su `soggetto_ruolo_id ASC` per ordinamento stabile: è ciò che rende le pagine contigue, senza soggetti ripetuti o saltati.

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
  'Rossi', 1, 50, 0
);

-- 2) Ricerca fornitori per P.IVA parziale
SELECT * FROM script.fn_search_soggetti_universale(
  '0123456', 2, 25, 0
);

-- 3) Ricerca clienti per codice billing_account
SELECT * FROM script.fn_search_soggetti_universale(
  'BA-001', 1, 50, 0
);

-- 4) Ricerca banche per bank_code
SELECT * FROM script.fn_search_soggetti_universale(
  '03069', 11, 50, 0
);

-- 5) Seconda pagina (offset 50)
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, 50, 50
);

-- 6) Ordinamento per codice soggetto, discendente
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, 50, 0, 'soggetto_codice', 'DESC'
);

-- 7) Ordinamento per id_fiscale_univoco, ascendente
SELECT * FROM script.fn_search_soggetti_universale(
  'Rossi', 1, 50, 0, 'id_fiscale_univoco', 'ASC'
);
```

---

### Caratteristiche Tecniche

* **Volatilita'**: `STABLE`, non `PARALLEL SAFE` (tolto il 18-08-2026: la catena
  dello scope non lo è).
* **Sicurezza**: `SECURITY INVOKER`, così la RLS di `clienti` vale con l'identità di
  chi chiama.
* **Linguaggio**: PL/pgSQL
* **SQL dinamico**: `RETURN QUERY EXECUTE` con `format()` per il frammento EXISTS della ricerca per codice e per il predicato della regola unica. Le tabelle sono validate dal trigger guard su `tipi_ruoli`.
* **Tipi colonne**: `%TYPE` per allineamento automatico ai tipi delle tabelle sorgente.
* **Error handling**: guard tramite `script.fn_log_and_raise_error` (log persistente + raise).
* **Ampliabilita'**: per aggiungere ricerca codice a un nuovo tipo ruolo, basta un UPDATE su `tipi_ruoli.entita_tabella` — zero modifiche SQL.

---
