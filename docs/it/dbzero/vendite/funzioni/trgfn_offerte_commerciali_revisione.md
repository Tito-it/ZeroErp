{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_revisione.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_revisione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_revisione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_revisione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: al momento dell'INSERT di una rev.N+1 (revisione_padre_id NOT NULL),
-- porta la rev.N precedente nello stato di superamento tramite UPDATE diretto.
-- L'UPDATE riattiva il guard _a10_ sulla stessa tabella: la transizione
-- EMESSA->SUPERATA e' ammessa in config.stati_doc_offerte_transizioni (Step 4).
-- Nota O4: l'UPDATE riguarda una riga diversa da quella inserita, nessuna
-- autoricorsione ne' conflitto intra-transazione.
-- rev 2026-08-28: lookup dal catalogo (is_superato) + guard sull'arita'.
DECLARE
    v_stato_superata_id config.stati_doc_offerte.id%TYPE;
    v_n_stati           integer;
BEGIN
    -- Se non e' una revisione (prima rev.), niente da fare.
    IF NEW.revisione_padre_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Risolve lo stato di superamento dalla DICHIARAZIONE di catalogo
    -- (config.stati_doc_offerte.is_superato), non da un letterale: e' la
    -- stessa colonna che vw_offerte_commerciali_lista legge per is_superata.
    SELECT count(*), min(s.id)
      INTO v_n_stati, v_stato_superata_id
      FROM config.stati_doc_offerte s
     WHERE s.is_superato IS TRUE
       AND s.attivo      IS TRUE;

    -- ⛔ Guard sull'ARITA', non sulla sola assenza. Senza, con zero righe la
    -- variabile resta NULL e l'UPDATE fallisce con un 23502 che nomina la
    -- colonna invece della configurazione; con due righe un SELECT INTO senza
    -- STRICT ne sceglierebbe una a caso, in silenzio. Il catalogo deve dire
    -- esattamente uno stato di superamento, o non sta dicendo niente.
    IF v_n_stati <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'tabella',  'config.stati_doc_offerte',
                'colonna',  'is_superato',
                'attesi',   1,
                'trovati',  v_n_stati
            ),
            NEW.tx_id,
            'config.stati_doc_offerte: atteso esattamente uno stato attivo '
            || 'con is_superato = true, trovati ' || v_n_stati::text
        );
    END IF;

    -- Porta la revisione padre nello stato di superamento.
    -- Il guard _a10_ verifica che EMESSA->SUPERATA sia transizione ammessa.
    UPDATE vendite.offerte_commerciali
       SET stato_doc_offerta_id = v_stato_superata_id
     WHERE id = NEW.revisione_padre_id;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_revisione()
IS 'AFTER INSERT su offerte_commerciali: se revisione_padre_id IS NOT NULL, porta la revisione padre nello stato di superamento. Lo stato si risolve dalla dichiarazione di catalogo config.stati_doc_offerte.is_superato (rev 2026-08-28) — la stessa che la vista di lista legge — e non piu'' da un letterale. Guard sull''ARITA'': se gli stati marcati non sono esattamente uno, E_CONFIG_MANCANTE; prima zero righe lasciavano la variabile NULL e l''errore era un 23502 che nominava la colonna invece della riga di catalogo. Innesca il guard _a10_ (EMESSA->SUPERATA ammessa in stati_doc_offerte_transizioni). Nota O4: agisce su riga diversa dall''INSERT scatenante, nessun conflitto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
