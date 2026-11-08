# fn_check_indirizzo_duplicato

### Scopo

Verifica l'esistenza di un indirizzo duplicato o simile in `anagrafiche.indirizzi_dettaglio`.
Costruisce la stringa normalizzata tramite `fn_build_indirizzo_normalizzato` (unica source of truth),
poi cerca match prefix sulla vista `vw_indirizzi_dettaglio`.

Supporta due flussi di ingresso:

- **Flusso A**: `p_stradario_id` fornito direttamente (indirizzo gia' noto)
- **Flusso B**: `p_stradario_id` NULL + `p_stradario_generale_id` + `p_comune_id`
  (+ opz. `p_codice_postale_id`): risolve lo stradario dalla combinazione in `config.stradario`

## Schema

`script` (funzione di lettura cross-dominio)

## Firma

```sql
script.fn_check_indirizzo_duplicato(
    -- Stradario diretto (flusso A)
    p_stradario_id               config.stradario.id%TYPE                          DEFAULT NULL,
    -- Campi civico (entrambi i flussi)
    p_civico                     anagrafiche.indirizzi_dettaglio.civico%TYPE           DEFAULT NULL,
    p_estensione_civico          anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE DEFAULT NULL,
    p_palazzina                  anagrafiche.indirizzi_dettaglio.palazzina%TYPE        DEFAULT NULL,
    p_scala                      anagrafiche.indirizzi_dettaglio.scala%TYPE            DEFAULT NULL,
    p_piano                      anagrafiche.indirizzi_dettaglio.piano%TYPE            DEFAULT NULL,
    p_interno                    anagrafiche.indirizzi_dettaglio.interno%TYPE          DEFAULT NULL,
    -- Risoluzione stradario (flusso B)
    p_stradario_generale_id      config.stradario_generale.id%TYPE                 DEFAULT NULL,
    p_comune_id                  config.comuni.id%TYPE                             DEFAULT NULL,
    p_codice_postale_id          config.codici_postali.id%TYPE                     DEFAULT NULL
) RETURNS TABLE (
    indirizzo_dettaglio_id   anagrafiche.indirizzi_dettaglio.id%TYPE,
    indirizzo_normalizzato   anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato%TYPE,
    descrizione_comune       config.comuni.descrizione%TYPE,
    exact_match              boolean
)
```

## Parametri

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_stradario_id` | `stradario.id%TYPE` | NULL | Stradario diretto (flusso A) |
| `p_civico` | `indirizzi_dettaglio.civico%TYPE` | NULL | Numero civico |
| `p_estensione_civico` | `indirizzi_dettaglio.estensione_civico%TYPE` | NULL | Estensione civico (es. /A) |
| `p_palazzina` | `indirizzi_dettaglio.palazzina%TYPE` | NULL | Palazzina |
| `p_scala` | `indirizzi_dettaglio.scala%TYPE` | NULL | Scala |
| `p_piano` | `indirizzi_dettaglio.piano%TYPE` | NULL | Piano |
| `p_interno` | `indirizzi_dettaglio.interno%TYPE` | NULL | Interno |
| `p_stradario_generale_id` | `stradario_generale.id%TYPE` | NULL | Flusso B: stradario_generale |
| `p_comune_id` | `comuni.id%TYPE` | NULL | Flusso B: comune |
| `p_codice_postale_id` | `codici_postali.id%TYPE` | NULL | Flusso B: CAP (opzionale) |

## Colonne ritornate

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `indirizzo_dettaglio_id` | bigint | ID del match trovato |
| `indirizzo_normalizzato` | text | Stringa normalizzata del match |
| `descrizione_comune` | `comuni.descrizione%TYPE` | Comune del match |
| `exact_match` | boolean | true = match esatto, false = solo prefix |

## Caratteristiche

- **STABLE**: solo lettura
- **PARALLEL SAFE**: nessun side-effect
- Guard: serve `p_stradario_id` OPPURE `p_stradario_generale_id + p_comune_id`
- Guard: ritorna vuoto se stradario non trovato
- Max 5 righe ritornate, ordinate per exact_match DESC

## Logica

1. **Risoluzione stradario_id**:
   - Flusso A: `p_stradario_id` fornito → usa direttamente
   - Flusso B: cerca in `config.stradario` con `(stradario_generale_id, comune_id, codice_postale_id)`,
     fra le vie **vive**: una via soppressa ha la stessa terna della via viva che ne ha preso il posto
   - Se non trovato nel flusso B → ritorna vuoto (la via non esiste come stradario locale)
   - Se nessun criterio sufficiente → errore `E_ADMIN_VALIDAZIONE`
2. Chiama `fn_build_indirizzo_normalizzato` per costruire `v_via_norm` e `v_norm`
3. Guard: se `v_via_norm` NULL (stradario inesistente), ritorna vuoto
4. Cerca su `vw_indirizzi_dettaglio` WHERE `stradario_id` = risolto:
   - Se civico fornito: `LIKE v_norm%` (match civico specifico)
   - Se civico NULL: `LIKE v_via_norm%` (qualsiasi civico sulla via)
5. Ordina: exact_match DESC (esatti prima), poi ID
6. LIMIT 5

## Dipendenze

- `anagrafiche.fn_build_indirizzo_normalizzato` — normalizzazione centralizzata
- `anagrafiche.vw_indirizzi_dettaglio` — vista per ricerca
- `config.stradario` — risoluzione stradario_id da combinazione (flusso B)

## Esempi

```sql
-- Flusso A: check duplicato con stradario_id diretto
SELECT * FROM script.fn_check_indirizzo_duplicato(
    p_stradario_id := 123,
    p_civico := 45,
    p_estensione_civico := '/A'
);

-- Flusso A: solo via (senza civico) — ritorna tutti i civici sulla via
SELECT * FROM script.fn_check_indirizzo_duplicato(p_stradario_id := 123);

-- Flusso B: risoluzione da stradario_generale + comune + CAP
SELECT * FROM script.fn_check_indirizzo_duplicato(
    p_stradario_generale_id := 456,
    p_comune_id := 789,
    p_codice_postale_id := 101,
    p_civico := 45,
    p_estensione_civico := '/A'
);

-- Flusso B: senza CAP (prende primo stradario per comune+via)
SELECT * FROM script.fn_check_indirizzo_duplicato(
    p_stradario_generale_id := 456,
    p_comune_id := 789,
    p_civico := 45
);
```
