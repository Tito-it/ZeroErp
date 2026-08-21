{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_righe_set_natura_vendita.md" %}
# ⚙️ Funzione `trgfn_preventivi_righe_set_natura_vendita`

```sql
CREATE FUNCTION trgfn_preventivi_righe_set_natura_vendita()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_righe_set_natura_vendita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_destinazione    config.nature_vendita.destinazione_tipo%TYPE;
    v_articolo_codice catalogo.articoli.codice%TYPE;
BEGIN
    -- Natura ereditata e CONGELATA dall'articolo: la riga non puo'
    -- discostarsi dalla classificazione dell'articolo. Qualunque
    -- valore fornito dal chiamante in NEW.natura_vendita_id viene
    -- sovrascritto (NO override operatore). Se l'articolo non e'
    -- ancora classificato (natura_vendita_id NULL, transitorio
    -- pre-backfill) la riga resta NULL e non e' smistabile finche'
    -- non si classifica.
    -- Stessa lettura recupera la destinazione_tipo della natura per
    -- il guard MODALITA' A: un solo lookup articolo->natura.
    SELECT a.natura_vendita_id, a.codice, nv.destinazione_tipo
      INTO NEW.natura_vendita_id, v_articolo_codice, v_destinazione
      FROM catalogo.articoli a
      LEFT JOIN config.nature_vendita nv
             ON nv.id = a.natura_vendita_id
     WHERE a.id = NEW.articolo_id;

    -- GUARD MODALITA' A (brief-preventivi-ordini.md D9): la
    -- ricorrenza (destinazione_tipo = 'CONTRATTO') non puo' stare
    -- su un preventivo. Blocco fail-fast all'inserimento riga.
    -- Data-driven: qualunque natura mappata a CONTRATTO e' bloccata,
    -- senza hardcodare il codice della natura.
    IF v_destinazione = 'CONTRATTO' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA',
            jsonb_build_object(
                'articolo_id',       NEW.articolo_id,
                'articolo_codice',   v_articolo_codice,
                'natura_vendita_id', NEW.natura_vendita_id,
                'destinazione_tipo', v_destinazione
            ),
            NEW.tx_id,
            coalesce(v_articolo_codice, NEW.articolo_id::text)
        );
    END IF;

    RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
