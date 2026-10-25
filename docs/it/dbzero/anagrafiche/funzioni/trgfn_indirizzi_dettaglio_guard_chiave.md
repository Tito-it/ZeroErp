{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_guard_chiave.md" %}
# ⚙️ Funzione `trgfn_indirizzi_dettaglio_guard_chiave`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_guard_chiave()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi       text := 'anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave';
    v_campo     text;   -- la colonna che si rifiuta
    v_cosa      text;   -- la stessa, come la legge una persona
    v_valore    text;   -- il valore rifiutato, come si salverebbe
    v_altro_id  anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_altro     anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La chiave dell'indirizzo dettaglio: civico > 0, valori
    --   con almeno una lettera o una cifra, e (in UPDATE) nessun
    --   doppione di un'altra riga. Rifiuta col codice e col campo.
    --
    -- Regole:
    --   - UPDATE che non tocca la chiave: niente da giudicare;
    --   - giudica i valori DOPO il normalize (z10);
    --   - il doppione solo in UPDATE: in INSERT lo cerca il BB,
    --     e la corsa la chiude l'indice (23505, che il BB rilegge).
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND (OLD.stradario_id, OLD.civico, OLD.estensione_civico,
            OLD.palazzina, OLD.scala, OLD.piano, OLD.interno)
           IS NOT DISTINCT FROM
           (NEW.stradario_id, NEW.civico, NEW.estensione_civico,
            NEW.palazzina, NEW.scala, NEW.piano, NEW.interno)
    THEN
        RETURN NEW;
    END IF;

    -- 1) D2-a: il civico, se c'e', e' un numero vero.
    IF NEW.civico <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_CIVICO_NON_POSITIVO',
            jsonb_build_object('campo', 'civico',
                               'civico', NEW.civico,
                               'stradario_id', NEW.stradario_id),
            NULL::uuid,
            NEW.civico::text);
    END IF;

    -- 2) D8: almeno una lettera o una cifra. Un NULL non e'
    --    rifiutato (!~ su NULL e' NULL, l'IF non scatta).
    IF NEW.estensione_civico !~ '[[:alnum:]]' THEN
        v_campo  := 'estensione_civico';
        v_cosa   := 'l''estensione del civico';
        v_valore := NEW.estensione_civico;
    ELSIF NEW.palazzina !~ '[[:alnum:]]' THEN
        v_campo  := 'palazzina';
        v_cosa   := 'la palazzina';
        v_valore := NEW.palazzina;
    ELSIF NEW.scala !~ '[[:alnum:]]' THEN
        v_campo  := 'scala';
        v_cosa   := 'la scala';
        v_valore := NEW.scala;
    ELSIF NEW.piano !~ '[[:alnum:]]' THEN
        v_campo  := 'piano';
        v_cosa   := 'il piano';
        v_valore := NEW.piano;
    ELSIF NEW.interno !~ '[[:alnum:]]' THEN
        v_campo  := 'interno';
        v_cosa   := 'l''interno';
        v_valore := NEW.interno;
    END IF;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE',
            jsonb_build_object('campo', v_campo,
                               'valore', v_valore,
                               'stradario_id', NEW.stradario_id),
            NULL::uuid,
            v_cosa, v_valore);
    END IF;

    -- 3) D6: in UPDATE, la chiave nuova non e' di un'altra riga.
    IF TG_OP = 'UPDATE' THEN
        SELECT d.id, d.indirizzo_normalizzato
          INTO v_altro_id, v_altro
          FROM anagrafiche.indirizzi_dettaglio d
         WHERE d.stradario_id = NEW.stradario_id
           AND d.id <> NEW.id
           AND d.civico            IS NOT DISTINCT FROM NEW.civico
           AND d.estensione_civico IS NOT DISTINCT FROM NEW.estensione_civico
           AND d.palazzina         IS NOT DISTINCT FROM NEW.palazzina
           AND d.scala             IS NOT DISTINCT FROM NEW.scala
           AND d.piano             IS NOT DISTINCT FROM NEW.piano
           AND d.interno           IS NOT DISTINCT FROM NEW.interno;

        IF v_altro_id IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', v_chi, 'E_INDIRIZZO_DETTAGLIO_DUPLICATO',
                jsonb_build_object('indirizzo_dettaglio_id', NEW.id,
                                   'indirizzo_dettaglio_id_esistente', v_altro_id),
                NULL::uuid,
                v_altro);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()
IS 'Guard (2026-10-25) della chiave di anagrafiche.indirizzi_dettaglio, in fascia z10: dopo il normalize, che scrive i valori come si salvano. E_INDIRIZZO_CIVICO_NON_POSITIVO: civico <= 0 (SNC = civico NULL, D2-a). E_INDIRIZZO_DETTAGLIO_SENZA_LETTERE: estensione, palazzina, scala, piano o interno senza una lettera o una cifra (D8). E_INDIRIZZO_DETTAGLIO_DUPLICATO, solo in UPDATE: la riga andrebbe sulla chiave di un''altra, che la frase nomina (D6; in INSERT il doppione lo cerca il BB fn_get_or_create_indirizzo_dettaglio e la corsa la chiude l''indice). UPDATE che non tocca la chiave: esce. Reti: i CHECK chk_indirizzi_dettaglio_civico_positivo e chk_indirizzi_dettaglio_dettaglio_leggibile, l''indice uq_indirizzi_dettaglio_norm_v2. Brief: brief-db-unicita-civico-indirizzi-dettaglio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
