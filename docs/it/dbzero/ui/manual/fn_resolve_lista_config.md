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
  1. Preferenza personale utente (`ui.lista_preferenza_utente`)
  2. Preset di ruolo (`ambito='ruolo'`, `profilo_accesso_id = ANY(v_profili_ids)`, `is_default=TRUE`)
  3. Preset di emittente fiscale (`ambito='emittente_fiscale'`, `is_default=TRUE`)
  4. Preset di sistema (`ambito='sistema'`, `is_default=TRUE`)
  5. Catalogo grezzo (tutte le colonne attive, `visibile=TRUE`, `fissata` se identificatore)

**3. Merge colonne nuove** — colonne presenti nel catalogo ma assenti dalla configurazione candidata vengono aggiunte in coda con `visibile=FALSE` e `ordine = ordine_default + 10000`. Il contatore `colonne_nuove` nel risultato indica quante colonne sono state aggiunte.

**4. Permessi effettivi** — per ogni colonna, risolve il `livello_accesso` effettivo tramite `DISTINCT ON (codice)` ordinato per `(priorita ASC, restrittivita ASC)`. Costruisce un JSONB `{codice: livello}` usato nel passo 5.

**5. Normalizzazione e filtro** — per ogni colonna:
  - `identificatore` e `azione` → `visibile = TRUE` forzato
  - `identificatore` → `fissata = TRUE` forzato
  - `BLOCCATO` → colonna rimossa dall'output
  - `LETTURA` → `esportabile = FALSE`

**6. Output JSONB** — restituisce la struttura pronta per il frontend.

## Caratteristiche

- **STABLE**: non modifica dati.
- Errori sollevati via `script.fn_log_and_raise_error` con codici `E_UI_LISTA_NON_TROVATA`.

## Risultato

JSONB con le chiavi:

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `colonne` | `jsonb[]` | Array di colonne con `codice`, `ordine`, `larghezza`, `visibile`, `fissata`, `esportabile`, `tipo_colonna` |
| `ordinamento` | `jsonb[]` | Array `[{"col": "...", "dir": "asc/desc"}]` |
| `filtri` | `jsonb` | Filtri preimpostati |
| `pagina_dimensione` | `integer` | Righe per pagina |
| `colonne_nuove` | `integer` | Numero di colonne aggiunte dal merge automatico (>0 = badge "aggiornato" nel frontend) |

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
