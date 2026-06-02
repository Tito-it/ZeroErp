# fn_resolve_lista_config

### 🎯 Scopo Principale

Punto centrale di risoluzione della configurazione di una lista per un utente. Applica la cascata di preset, il merge automatico delle colonne nuove, la normalizzazione delle colonne obbligatorie e il filtro autorizzativo a livello colonna. Restituisce un JSONB pronto per il frontend, senza logica di business lato applicazione.

## Schema

`ui`

## Firma

```sql
ui.fn_resolve_lista_config(
  p_lista_codice         VARCHAR,
  p_auth_user_id         INTEGER,
  p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE
) RETURNS JSONB
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_lista_codice` | `VARCHAR` | Sì | Codice lista (es. `anagrafiche.clienti`) |
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`) |
| `p_emittente_fiscale_id` | `INTEGER` | No | ID emittente fiscale del contesto. NULL se non rilevante. |

## Algoritmo (6 passi)

**0. Risoluzione lista_id** — lookup `ui.lista_definizione` per codice. Errore `E_UI_LISTA_NON_TROVATA` se non trovata o non attiva.

**1. Profili applicabili** — chiama `script.fn_get_profili_accesso_applicabili(p_auth_user_id)` e costruisce `v_profili_ids[]`.

**2. Cascata configurazione** — scende in ordine fino al primo risultato non NULL:
  1. Preferenza personale utente (`ui.lista_preferenza_utente`) — legge anche `preset_base_id`, `preset_base_data_update`, `preset_aggiornato_ignored_at` per lo step 2.5
  2. Preset di ruolo (`ambito='ruolo'`, `profilo_accesso_id = ANY(v_profili_ids)`, `is_default=TRUE`)
  3. Preset di emittente fiscale (`ambito='emittente_fiscale'`, `is_default=TRUE`)
  4. Preset di sistema (`ambito='sistema'`, `is_default=TRUE`)
  5. Catalogo grezzo (tutte le colonne attive, `visibile=TRUE`, `fissata` se identificatore)

**2.5 DEF-2: calcolo flag `preset_aggiornato`** — eseguito dopo la cascata. Se la preferenza utente ha `preset_base_id IS NOT NULL` e `preset_base_data_update IS NOT NULL`, legge `lista_preset.data_update` corrente del preset di base e calcola:

```text
preset_aggiornato = TRUE sse:
  (a) preset_base_data_update IS NOT NULL
  (b) lista_preset.data_update IS NOT NULL
  (c) lista_preset.data_update > preset_base_data_update   ← il preset è più recente dello snapshot
  (d) preset_aggiornato_ignored_at IS NULL                 ← mai ignorato
      OPPURE preset_aggiornato_ignored_at < lista_preset.data_update  ← preset cambiato dopo l'ultimo ignore
```

In tutti gli altri casi (no preferenza, `preset_base_id IS NULL`, snapshot allineato, ignore attivo) il flag è `FALSE`.

**3. Merge colonne nuove** — colonne presenti nel catalogo ma assenti dalla configurazione candidata vengono aggiunte in coda con `visibile=FALSE` e `ordine = ordine_default + 10000`. Il contatore `colonne_nuove` nel risultato indica quante colonne sono state aggiunte.

**4. Permessi effettivi** — per ogni colonna, risolve il `livello_accesso` effettivo tramite `DISTINCT ON (codice)` ordinato per `(priorita ASC, restrittivita ASC)`. Costruisce un JSONB `{codice: livello}` usato nel passo 5.

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
| `pagina_dimensione` | `integer` | Righe per pagina |
| `colonne_nuove` | `integer` | Numero di colonne aggiunte dal merge automatico (>0 = badge "aggiornato" nel frontend) |
| `preset_aggiornato` | `boolean` | DEF-2: `TRUE` se il preset di base è stato modificato dopo lo snapshot della preferenza utente E l'utente non ha ancora ignorato l'aggiornamento (o il preset è cambiato di nuovo dopo l'ultimo ignore). `FALSE` in tutti gli altri casi: nessuna preferenza, `preset_base_id IS NULL`, snapshot allineato, ignore attivo. |

> **Campo per colonna `priorita`** (in ogni elemento di `colonne`): `SMALLINT`, peso di permanenza per il **ritiro dinamico** lato FE (packing a somma; più alto = si ritira per ultima). Letto **fresco** da `ui.lista_colonna` ad ogni risoluzione — non dal candidato preset/preferenza, quindi non snapshottato. Vedi [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) per l'algoritmo di ritiro.

## Dipendenze

- `ui.lista_definizione` — lookup lista per codice
- `ui.lista_colonna` — catalogo colonne e flag sensibile/esportabile
- `ui.lista_preset` + `ui.lista_preset_colonna` — configurazioni predefinite
- `ui.lista_preferenza_utente` — preferenza personale
- `ui.lista_colonna_permesso` — permessi a livello colonna
- `script.fn_get_profili_accesso_applicabili` — risoluzione profili (chiamata 2 volte: passo 1 per array IDs, passo 4 per priorità)

## Esempio

```sql
-- Lista clienti per l'utente 42, emittente fiscale 1
SELECT ui.fn_resolve_lista_config('anagrafiche.clienti', 42, 1);

-- Variante senza contesto emittente (admin globale)
SELECT ui.fn_resolve_lista_config('vendite.fatture', 42, NULL);
```
