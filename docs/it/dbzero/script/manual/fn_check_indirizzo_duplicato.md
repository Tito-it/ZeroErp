# fn_check_indirizzo_duplicato
### 🎯 Scopo Principale
Verifica l'esistenza di un indirizzo duplicato o simile in `anagrafiche.indirizzi_dettaglio`.
Costruisce la stringa normalizzata tramite `fn_build_indirizzo_normalizzato` (unica source of truth),
poi cerca match prefix sulla vista `vw_indirizzi_dettaglio`.

## Schema

`script` (funzione di lettura cross-dominio)

## Firma

```sql
script.fn_check_indirizzo_duplicato(
    p_stradario_id       config.stradario.id%TYPE,
    p_civico             anagrafiche.indirizzi_dettaglio.civico%TYPE           DEFAULT NULL,
    p_estensione_civico  anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE DEFAULT NULL,
    p_palazzina          anagrafiche.indirizzi_dettaglio.palazzina%TYPE        DEFAULT NULL,
    p_scala              anagrafiche.indirizzi_dettaglio.scala%TYPE            DEFAULT NULL,
    p_piano              anagrafiche.indirizzi_dettaglio.piano%TYPE            DEFAULT NULL,
    p_interno            anagrafiche.indirizzi_dettaglio.interno%TYPE          DEFAULT NULL
) RETURNS TABLE (
    indirizzo_dettaglio_id   anagrafiche.indirizzi_dettaglio.id%TYPE,
    indirizzo_normalizzato   anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato%TYPE,
    descrizione_comune       text,
    exact_match              boolean
)
```

## Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_stradario_id` | integer | - | Stradario di riferimento (obbligatorio) |
| `p_civico` | integer | NULL | Numero civico |
| `p_estensione_civico` | varchar | NULL | Estensione civico (es. /A) |
| `p_palazzina` | varchar | NULL | Palazzina |
| `p_scala` | varchar | NULL | Scala |
| `p_piano` | varchar | NULL | Piano |
| `p_interno` | varchar | NULL | Interno |

## Colonne ritornate

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `indirizzo_dettaglio_id` | bigint | ID del match trovato |
| `indirizzo_normalizzato` | text | Stringa normalizzata del match |
| `descrizione_comune` | text | Comune del match |
| `exact_match` | boolean | true = match esatto, false = solo prefix |

## Caratteristiche

- **STABLE**: solo lettura
- **PARALLEL SAFE**: nessun side-effect
- Guard: `p_stradario_id` obbligatorio e > 0
- Guard: ritorna vuoto se stradario non trovato in `vw_indirizzo_completo`
- Max 5 righe ritornate, ordinate per exact_match DESC

## Logica

1. Guard: `p_stradario_id` non NULL e > 0
2. Chiama `fn_build_indirizzo_normalizzato` per costruire `v_via_norm` e `v_norm`
3. Guard: se `v_via_norm` NULL (stradario inesistente), ritorna vuoto
4. Cerca su `vw_indirizzi_dettaglio` WHERE `stradario_id` = parametro:
   - Se civico fornito: `LIKE v_norm%` (match civico specifico)
   - Se civico NULL: `LIKE v_via_norm%` (qualsiasi civico sulla via)
5. Ordina: exact_match DESC (esatti prima), poi ID
6. LIMIT 5

## Dipendenze

- `anagrafiche.fn_build_indirizzo_normalizzato` — normalizzazione centralizzata
- `anagrafiche.vw_indirizzi_dettaglio` — vista per ricerca

## Esempi

```sql
-- Check duplicato con civico
SELECT * FROM script.fn_check_indirizzo_duplicato(123, 45, '/A');

-- Check solo via (senza civico): ritorna tutti i civici sulla via
SELECT * FROM script.fn_check_indirizzo_duplicato(123);

-- Uso nel backend Python (check-duplicato endpoint)
SELECT *
  FROM script.fn_check_indirizzo_duplicato(
    p_stradario_id := %(stradario_id)s,
    p_civico := %(civico)s,
    p_estensione_civico := %(estensione_civico)s,
    p_palazzina := %(palazzina)s,
    p_scala := %(scala)s,
    p_piano := %(piano)s,
    p_interno := %(interno)s
  );
```
