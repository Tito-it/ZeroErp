# fn_search_stradario_generale
### 🎯 Scopo Principale
Ricerca vie su `config.stradario_generale` (senza comune/CAP).
Serve per autocomplete "via nuova": l'utente cerca una via in tutta Italia,
poi sceglie comune e CAP separatamente.

## Schema

`script` (funzione di lettura cross-dominio, come `fn_search_stradario`)

## Firma

```sql
script.fn_search_stradario_generale(
    p_search             text                             DEFAULT NULL,
    p_toponomastica_id   config.toponomastica.id%TYPE     DEFAULT NULL,
    p_limit              integer                          DEFAULT 30
) RETURNS TABLE (
    stradario_generale_id   config.stradario_generale.id%TYPE,
    toponomastica_id        config.toponomastica.id%TYPE,
    toponimo                config.toponomastica.descrizione%TYPE,
    denominazione           config.stradario_generale.descrizione%TYPE,
    indirizzo_normalizzato  config.stradario_generale.indirizzo_normalizzato%TYPE
)
```

## Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_search` | text | NULL | Testo di ricerca ILIKE (obbligatorio, min 2 char) |
| `p_toponomastica_id` | integer | NULL | Filtro opzionale per tipo strada (VIA, PIAZZA...) |
| `p_limit` | integer | 30 | Max righe ritornate |

## Caratteristiche

- **STABLE**: solo lettura
- **PARALLEL SAFE**: nessun side-effect
- Guard: `p_search` obbligatorio e minimo 2 caratteri
- Guard: `p_toponomastica_id` > 0 se fornito
- Filtro: `toponomastica.attivo = TRUE`

## Differenza con fn_search_stradario

| | fn_search_stradario | fn_search_stradario_generale |
|---|---|---|
| **Livello** | `stradario` (via + comune + CAP) | `stradario_generale` (via, senza localita') |
| **Caso d'uso** | Autocomplete indirizzo (comune gia' scelto) | Autocomplete via nuova (cerca in tutta Italia) |
| **JOIN** | stradario_generale + toponomastica + comuni + province + codici_postali | stradario_generale + toponomastica |
| **Filtro principale** | `p_comune_id` | `p_search` (obbligatorio) |
| **Ritorna** | stradario_id, toponimo, denominazione, comune, provincia, CAP | stradario_generale_id, toponomastica_id, toponimo, denominazione |

## Logica

1. Normalizza `p_search`: BTRIM, NULLIF
2. Guard: `p_search` obbligatorio e >= 2 char
3. Guard: `p_toponomastica_id` > 0 se fornito
4. Query: JOIN `stradario_generale` → `toponomastica`
5. WHERE: `toponomastica.attivo = TRUE` AND ILIKE su `indirizzo_normalizzato`
6. Filtro opzionale su `toponomastica_id`
7. ORDER BY `indirizzo_normalizzato`, LIMIT

## Indici utilizzati

- `ix_stradario_generale_norm_trgm` (GIN trigram) su `indirizzo_normalizzato`
- `ix_config_stradario_generale_toponomastica_id` (btree) su `toponomastica_id`

## Esempi

```sql
-- Cerca "roma" in tutte le vie
SELECT * FROM script.fn_search_stradario_generale('roma');

-- Cerca "roma" solo tra le VIA (toponomastica_id = 1)
SELECT * FROM script.fn_search_stradario_generale('roma', 1);

-- Cerca "garibaldi" con limite 10
SELECT * FROM script.fn_search_stradario_generale('garibaldi', p_limit := 10);
```

## Flusso frontend (via nuova)

1. Utente digita nel campo "cerca via" → autocomplete chiama `fn_search_stradario_generale`
2. Risultati: "VIA ROMA", "PIAZZA ROMA", etc.
3. Utente seleziona → form riceve `stradario_generale_id` e `toponomastica_id`
4. Utente sceglie comune e CAP → backend crea/trova `stradario` e poi `indirizzi_dettaglio`
