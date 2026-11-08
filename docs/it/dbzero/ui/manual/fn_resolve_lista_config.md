# fn_resolve_lista_config

> **Ultimo aggiornamento**: 8 novembre 2026

### 🎯 Scopo Principale

Punto centrale di risoluzione della configurazione di una lista per un utente. Applica la cascata di preset, il merge automatico delle colonne nuove, la normalizzazione delle colonne obbligatorie e il filtro autorizzativo a livello colonna. Restituisce un JSONB pronto per il frontend, senza logica di business lato applicazione.

## Schema

`ui`

## Firma

```sql
ui.fn_resolve_lista_config(
  p_lista_codice         ui.lista_definizione.codice%TYPE,
  p_auth_user_id         ui.lista_preferenza_utente.auth_user_id%TYPE,
  p_emittente_fiscale_id ui.lista_preset.emittente_fiscale_id%TYPE
) RETURNS JSONB
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_lista_codice` | `VARCHAR` | Sì | Codice lista (es. `anagrafiche.clienti`) |
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`) |
| `p_emittente_fiscale_id` | `BIGINT` | No | ID emittente fiscale del contesto. NULL se non rilevante. |

## Algoritmo (6 passi)

**0. La riga della lista** — letta una volta dal building block [`ui.fn_lista_da_codice`](/dbzero/ui/funzioni/fn_lista_da_codice), che solleva `E_UI_LISTA_NON_TROVATA` se la lista non c'è o è spenta. Da questa riga vengono `multi_emittente`, `perimetro_emittente` e `ricerca_min_caratteri`.

**1. Profili applicabili** — chiama `script.fn_get_profili_accesso_applicabili(p_auth_user_id)` e costruisce `v_profili_ids[]`.

**2. Cascata per chiave** (dal 1-11-2026) — le quattro chiavi `colonne`, `ordinamento`, `filtri` e `pagina_dimensione` si risolvono **ognuna per conto suo**: ciascuna viene dal primo livello che la contiene.

  1. Preferenza personale utente (`ui.lista_preferenza_utente`): una chiave **presente** è una scelta dell'utente; una chiave **assente** (o `null`) vuol dire «come lo standard». Si legge anche `preset_base_id`, `preset_base_contenuto_aggiornato_il`, `preset_aggiornato_ignored_at` per lo step 2.5
  2. Il **preset di base**: il primo, in quest'ordine, che ha almeno una colonna attiva — preset di ruolo (`ambito='ruolo'`, `profilo_accesso_id = ANY(v_profili_ids)`, il più prioritario), preset di emittente fiscale (`ambito='emittente_fiscale'`), preset di sistema (`ambito='sistema'`); sempre `is_default=TRUE` e `attivo=TRUE`. Si cerca **sempre**, anche quando c'è una preferenza: dà lo standard delle chiavi che la preferenza non ha. Un preset è completo, colonne comprese
  3. Catalogo grezzo: per le colonne, tutte quelle attive (`visibile=TRUE`, `fissata` se identificatore); `ordinamento` vuoto, `filtri` vuoti, la misura di default `PAGINA`

Per `pagina_dimensione` lo **standard** è la misura del preset di base se è nel catalogo [`ui.misure_pagina`](/dbzero/ui/tabelle/misure_pagina), altrimenti il default `PAGINA`. La misura della preferenza vale se è nel catalogo; altrimenti risponde lo standard.

> ⚠️ Fino al 31-10-2026 la cascata sceglieva **un** livello, il primo con le colonne, e da lì prendeva tutte e quattro le chiavi: una preferenza di sole colonne rispondeva ordinamento e filtri vuoti e la misura di default, scavalcando il preset. E il frontend, che salvava la configurazione risolta, congelava nella preferenza ordinamento, filtri e misura del preset di quel momento. Le preferenze esistenti sono state ripulite (changeSet `20261101-28`).

**2.5 DEF-2: calcolo flag `preset_aggiornato`** — eseguito dopo la cascata. Se la preferenza utente ha `preset_base_id IS NOT NULL` e `preset_base_contenuto_aggiornato_il IS NOT NULL`, legge `lista_preset.contenuto_aggiornato_il` corrente del preset di base e calcola:

```text
preset_aggiornato = TRUE sse:
  (a) preset_base_contenuto_aggiornato_il IS NOT NULL
  (b) lista_preset.contenuto_aggiornato_il IS NOT NULL
  (c) lista_preset.contenuto_aggiornato_il > preset_base_contenuto_aggiornato_il   ← il preset è più recente dello snapshot
  (d) preset_aggiornato_ignored_at IS NULL                 ← mai ignorato
      OPPURE preset_aggiornato_ignored_at < lista_preset.contenuto_aggiornato_il  ← preset cambiato dopo l'ultimo ignore
```

In tutti gli altri casi (no preferenza, `preset_base_id IS NULL`, snapshot allineato, ignore attivo) il flag è `FALSE`.

**3. Merge colonne nuove** — sulle colonne risolte, da qualunque livello vengano: colonne presenti nel catalogo ma assenti vengono aggiunte in coda con `visibile=FALSE` e `ordine = ordine_default + 10000`. Il contatore `colonne_nuove` nel risultato indica quante colonne sono state aggiunte.

**4. Permessi effettivi** — il livello di ogni colonna (`TUTTO`, `LETTURA`, `BLOCCATO`) non si calcola qui: lo dà [`ui.fn_lista_colonne_livello`](/dbzero/ui/funzioni/fn_lista_colonne_livello), letto nel passo 5. È lo stesso calcolo che usa la ricerca libera ([`ui.fn_lista_colonne_ricerca_full`](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full)): una sede sola, così la ricerca non trova righe per una colonna che la lista non mostra.

**5. Normalizzazione e filtro** — per ogni colonna:
  - `identificatore` e `azione` → `visibile = TRUE` forzato
  - `identificatore` → `fissata = TRUE` forzato
  - `BLOCCATO` → colonna rimossa dall'output
  - `LETTURA` → `esportabile = FALSE`
  - `priorita` letta **fresca** da `ui.lista_colonna` (attributo globale di catalogo: non dal candidato preset/preferenza) e aggiunta al JSONB colonna

**6. Output JSONB** — restituisce la struttura pronta per il frontend.

## Caratteristiche

- **STABLE**: non modifica dati.
- Errori sollevati via `script.fn_log_and_raise_error` con codici `E_UI_LISTA_NON_TROVATA`.

## Risultato

JSONB con le chiavi:

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `colonne` | `jsonb[]` | Array di colonne con `codice`, `ordine`, `larghezza`, `visibile`, `fissata`, `esportabile`, `tipo_colonna`, `etichetta_i18n_key`, `priorita` |
| `ordinamento` | `jsonb[]` | Array `[{"col": "...", "dir": "asc/desc"}]` |
| `filtri` | `jsonb` | Filtri preimpostati |
| `pagina_dimensione` | `integer` | Righe per pagina: sempre una misura del catalogo [`ui.misure_pagina`](/dbzero/ui/tabelle/misure_pagina) — quella scelta (preferenza o preset) se è ammessa, altrimenti il default `PAGINA` del catalogo. Mai vuota (dal 30-09-2026; prima ripiegava su un 25 scritto nella funzione, e senza preferenza né preset poteva uscire vuota) |
| `pagina_dimensione_standard` | `integer` | La misura che la cascata darebbe **senza** la preferenza: quella del preset di base se è nel catalogo, altrimenti il default `PAGINA`. Il drawer la mostra come «Come lo standard (N)» (dal 1-11-2026) |
| `origine` | `jsonb` | Per ognuna delle quattro chiavi, il livello da cui viene: `preferenza`, `ruolo`, `emittente_fiscale`, `sistema` (i valori di `ui.ambito_preset`) o `catalogo`. Esempio: `{"colonne": "preferenza", "ordinamento": "sistema", "filtri": "sistema", "pagina_dimensione": "sistema"}`. Il frontend rimanda al salvataggio **solo** le chiavi `preferenza`, più quella toccata: rimandare tutto congelerebbe di nuovo le altre (dal 1-11-2026) |
| `ricerca_min_caratteri` | `integer` | La soglia della ricerca libera della lista (`ui.lista_definizione.ricerca_min_caratteri`): sotto questo numero di caratteri il frontend non manda il termine. È la stessa colonna che legge la ricerca del backend |
| `colonne_nuove` | `integer` | Numero di colonne aggiunte dal merge automatico (>0 = badge "aggiornato" nel frontend) |
| `preset_aggiornato` | `boolean` | DEF-2: `TRUE` se il preset di base (`preset_base_id` della preferenza, il preset che sta sotto la preferenza) è stato modificato dopo lo snapshot della preferenza utente E l'utente non ha ancora ignorato l'aggiornamento (o il preset è cambiato di nuovo dopo l'ultimo ignore). `FALSE` in tutti gli altri casi: nessuna preferenza, `preset_base_id IS NULL`, snapshot allineato, ignore attivo. |

> **Campo per colonna `priorita`** (in ogni elemento di `colonne`): `SMALLINT`, peso di permanenza per il **ritiro dinamico** lato FE (packing a somma; più alto = si ritira per ultima). Letto **fresco** da `ui.lista_colonna` ad ogni risoluzione — non dal candidato preset/preferenza, quindi non snapshottato. Vedi [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) per l'algoritmo di ritiro.

## Dipendenze

- [`ui.fn_lista_da_codice`](/dbzero/ui/funzioni/fn_lista_da_codice) — la riga della lista dal codice (passo 0)
- `ui.lista_colonna` — catalogo colonne e flag sensibile/esportabile
- `ui.lista_preset` + `ui.lista_preset_colonna` — configurazioni predefinite; il loro `contenuto_aggiornato_il` è la data dell'ultimo cambio del contenuto (vedi [ui.lista_preset](/dbzero/ui/tabelle/lista_preset))
- `ui.lista_preferenza_utente` — preferenza personale
- `ui.lista_colonna_permesso` — permessi a livello colonna
- `script.fn_get_profili_accesso_applicabili` — risoluzione profili (passo 1 e preset di ruolo)
- [`ui.fn_veste_corrente`](/dbzero/ui/funzioni/fn_veste_corrente) — la veste dalla GUC `app.ruolo_applicativo`
- [`ui.fn_lista_colonne_livello`](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello effettivo di ogni colonna (passo 5)

## Esempio

```sql
-- Lista clienti per l'utente 42, emittente fiscale 1
SELECT ui.fn_resolve_lista_config('anagrafiche.clienti', 42, 1);

-- Variante senza contesto emittente (admin globale)
SELECT ui.fn_resolve_lista_config('vendite.fatture', 42, NULL);
```

---

### Note di migrazione

* 2026-11-08 — il flag `preset_aggiornato` legge `lista_preset.contenuto_aggiornato_il` e lo snapshot rinominato (`brief-db-revisione-dbops`, giro 7-bis blocco c). Il JSON in uscita non cambia.
