# fn_build_indirizzo_normalizzato
### 🎯 Scopo Principale
Centralizza **tutta** la logica di normalizzazione degli indirizzi fisici.
E' la **unica source of truth**: il trigger `trgfn_indirizzi_dettaglio_normalize`
la chiama e assegna i risultati (zero logica nel trigger). La usano anche il
«trova o crea» `fn_get_or_create_indirizzo_dettaglio` (cerca coi valori come li
salva il trigger) e `script.fn_check_indirizzo_duplicato`.
(ultima revisione 25-10-2026: vuoto → NULL, SNC solo col civico NULL)

## Schema

`anagrafiche`

## Firma

```sql
anagrafiche.fn_build_indirizzo_normalizzato(
  p_stradario_id  config.stradario.id%TYPE,
  p_civico        anagrafiche.indirizzi_dettaglio.civico%TYPE           DEFAULT NULL,
  p_estensione    anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE DEFAULT NULL,
  p_palazzina     anagrafiche.indirizzi_dettaglio.palazzina%TYPE        DEFAULT NULL,
  p_scala         anagrafiche.indirizzi_dettaglio.scala%TYPE            DEFAULT NULL,
  p_piano         anagrafiche.indirizzi_dettaglio.piano%TYPE            DEFAULT NULL,
  p_interno       anagrafiche.indirizzi_dettaglio.interno%TYPE          DEFAULT NULL,
  -- OUT params
  OUT o_estensione_civico       anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE,
  OUT o_palazzina               anagrafiche.indirizzi_dettaglio.palazzina%TYPE,
  OUT o_scala                   anagrafiche.indirizzi_dettaglio.scala%TYPE,
  OUT o_piano                   anagrafiche.indirizzi_dettaglio.piano%TYPE,
  OUT o_interno                 anagrafiche.indirizzi_dettaglio.interno%TYPE,
  OUT o_via_norm                anagrafiche.indirizzi_dettaglio.via_norm%TYPE,
  OUT o_civico_norm             anagrafiche.indirizzi_dettaglio.civico_norm%TYPE,
  OUT o_indirizzo_normalizzato  anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato%TYPE
) RETURNS record
```

## Parametri IN

| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `p_stradario_id` | integer | — | FK a `config.stradario` (obbligatorio) |
| `p_civico` | integer | NULL | Numero civico (NULL = SNC) |
| `p_estensione` | varchar | NULL | Estensione civico (es. `a`, `/B`) |
| `p_palazzina` | varchar | NULL | Palazzina |
| `p_scala` | varchar | NULL | Scala |
| `p_piano` | varchar | NULL | Piano |
| `p_interno` | varchar | NULL | Interno |

## Parametri OUT

| Parametro | Descrizione |
|-----------|-------------|
| `o_estensione_civico` | Normalizzata: UPPER+BTRIM, prefisso `/` |
| `o_palazzina` | Normalizzata: UPPER+BTRIM |
| `o_scala` | Normalizzata: UPPER+BTRIM |
| `o_piano` | Normalizzato: UPPER+BTRIM |
| `o_interno` | Normalizzato: UPPER+BTRIM |
| `o_via_norm` | `UPPER(tipo_toponimo + nome_strada)` da lookup |
| `o_civico_norm` | `civico + estensione` oppure `SNC` |
| `o_indirizzo_normalizzato` | Stringa completa concatenata |

## Caratteristiche

- **STABLE**: esegue un SELECT su `script.vw_indirizzo_completo`
- **PARALLEL SAFE**: nessun side-effect
- Normalizza internamente tutti gli input (UPPER + BTRIM, vuoto → NULL, prefisso `/`)
- Ritorna record con tutti gli OUT a NULL se `p_stradario_id` non valido o la via non si risolve nella vista: anche le colonne strutturali. Chi cerca con questi valori si ferma su `o_via_norm` NULL (lo fa `fn_get_or_create_indirizzo_dettaglio`)

## Logica

1. **Guard**: `p_stradario_id` IS NULL o <= 0 → RETURN (tutti OUT a NULL)
2. **Lookup via_norm**: `UPPER(TRIM(tipo_toponimo || ' ' || nome_strada))` da `script.vw_indirizzo_completo`
3. **Normalizza input**: UPPER + BTRIM su estensione, palazzina, scala, piano, interno; un testo vuoto diventa NULL (una forma sola per «non c'è», come vuole l'indice `NULLS NOT DISTINCT`)
4. **Prefisso '/'**: aggiunge `'/'` a estensione se mancante
5. **Civico norm**: `civico::text || estensione` oppure `'SNC'` se civico NULL
6. **Concatena**: `via_norm, civico_norm[, Pal.X][, Scala X][, Piano X][, Int.X]`

## Formato output

```
VIA ROMA, 12/A, Pal.B, Scala C, Piano 2, Int.3
```

- Separatore: `, ` tra ogni componente
- Prefissi fissi: `Pal.`, `Scala `, `Piano `, `Int.`
- Componenti opzionali omessi se NULL o vuoti

## Indici utilizzati

La stringa `o_indirizzo_normalizzato` matcha `anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato`.
L'indice GIN trigram `ix_indirizzi_dettaglio_indirizzo_norm_gin` permette ricerche ILIKE performanti.
Per match esatto nel check duplicato si usa `=` (btree implicito).

## Uso da trigger

```sql
-- trgfn_indirizzi_dettaglio_normalize: zero logica, solo assegnazioni
DECLARE
  v_result record;
BEGIN
  SELECT * INTO v_result
    FROM anagrafiche.fn_build_indirizzo_normalizzato(
      NEW.stradario_id, NEW.civico, NEW.estensione_civico,
      NEW.palazzina, NEW.scala, NEW.piano, NEW.interno);

  NEW.estensione_civico      := v_result.o_estensione_civico;
  NEW.palazzina              := v_result.o_palazzina;
  NEW.scala                  := v_result.o_scala;
  NEW.piano                  := v_result.o_piano;
  NEW.interno                := v_result.o_interno;
  NEW.via_norm               := v_result.o_via_norm;
  NEW.civico_norm            := v_result.o_civico_norm;
  NEW.indirizzo_normalizzato := v_result.o_indirizzo_normalizzato;
  RETURN NEW;
END;
```

## Uso da Python (check duplicato)

```sql
SELECT * FROM anagrafiche.vw_indirizzi_dettaglio
 WHERE stradario_id = %s
   AND indirizzo_normalizzato = (
         anagrafiche.fn_build_indirizzo_normalizzato(
           %s, %s, %s, %s, %s, %s, %s)
       ).o_indirizzo_normalizzato
 LIMIT 1
```

## Esempi

```sql
-- Civico con estensione
SELECT * FROM anagrafiche.fn_build_indirizzo_normalizzato(42, 12, 'a');
-- o_estensione_civico = '/A'
-- o_via_norm = 'VIA ROMA'
-- o_civico_norm = '12/A'
-- o_indirizzo_normalizzato = 'VIA ROMA, 12/A'

-- Senza numero civico
SELECT (anagrafiche.fn_build_indirizzo_normalizzato(42)).o_indirizzo_normalizzato;
-- → 'VIA ROMA, SNC'

-- Completo
SELECT * FROM anagrafiche.fn_build_indirizzo_normalizzato(42, 5, '/B', 'C', 'A', '2', '3');
-- → 'VIA ROMA, 5/B, Pal.C, Scala A, Piano 2, Int.3'
```
