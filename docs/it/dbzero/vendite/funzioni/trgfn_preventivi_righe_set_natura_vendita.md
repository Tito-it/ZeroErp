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
    -- La natura della riga la scrive script.trgfn_righe_natura_vendita
    -- (trigger _a10_natura_vendita_ins_upd, che viene PRIMA di questo):
    -- qui si legge soltanto. Rev 20261013-10.
    SELECT nv.destinazione_tipo
      INTO v_destinazione
      FROM config.nature_vendita nv
     WHERE nv.id = NEW.natura_vendita_id;

    -- GUARD MODALITA' A (brief-preventivi-ordini.md D9): la
    -- ricorrenza (destinazione_tipo = 'CONTRATTO') non puo' stare
    -- su un preventivo. Blocco fail-fast all'inserimento riga.
    -- Data-driven: qualunque natura mappata a CONTRATTO e' bloccata,
    -- senza hardcodare il codice della natura.
    IF v_destinazione = 'CONTRATTO' THEN
        SELECT a.codice INTO v_articolo_codice
          FROM catalogo.articoli a
         WHERE a.id = NEW.articolo_id;

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

COMMENT ON FUNCTION vendite.trgfn_preventivi_righe_set_natura_vendita()
IS 'Guard BEFORE INSERT OR UPDATE OF articolo_id su vendite.preventivi_righe (MODALITA'' A, brief-preventivi-ordini D9): una riga con natura che va in contratto (destinazione_tipo CONTRATTO) non sta su un preventivo, E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA. ⚠️ Rev 20261013-10 (brief-db-articoli-ammessi-per-documento A-4): non scrive piu'' la natura, nonostante il nome; la scrive script.trgfn_righe_natura_vendita (_a10_natura_vendita_ins_upd), che viene prima nell''ordine dei nomi, e questo guard ne legge la destinazione. Il Lotto 3 lo ritira nella check delle righe di preventivo.';
```

---
{% include-markdown "signature-core.md" %}
