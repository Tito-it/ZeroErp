# ⚙️ Funzione `trgfn_offerte_commerciali_rientro_padre`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_rientro_padre()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_rientro_padre()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: quando una revisione di offerta viene ANNULLATA e non resta
-- nessun'altra revisione viva dello stesso padre, riporta il padre fuori
-- dallo stato di superamento (SUPERATA -> EMESSA).
-- E' l'inverso di trgfn_offerte_commerciali_revisione, che al nascere della
-- revisione porta il padre a SUPERATA: la regola di dominio e' «una revisione
-- abortita non rimpiazza nessuno», ed e' la stessa che i preventivi hanno per
-- costruzione (li' il superamento e' una relazione, non uno stato).
DECLARE
    v_padre_superato   boolean;
    v_altre_vive       integer;
    v_stato_emessa_id  config.stati_doc_offerte.id%TYPE;
    v_n_emessa         integer;
BEGIN
    -- (1) Interessa solo il momento in cui lo stato DIVENTA di annullamento.
    --     Un UPDATE che lascia lo stato invariato, o che si muove fra due
    --     stati non abortiti, non ha niente a che vedere col rientro.
    IF NEW.stato_doc_offerta_id IS NOT DISTINCT FROM OLD.stato_doc_offerta_id THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM config.stati_doc_offerte s
         WHERE s.id = NEW.stato_doc_offerta_id
           AND s.is_abortito IS TRUE
    ) OR EXISTS (
        SELECT 1 FROM config.stati_doc_offerte s
         WHERE s.id = OLD.stato_doc_offerta_id
           AND s.is_abortito IS TRUE
    ) THEN
        RETURN NULL;
    END IF;

    -- (2) Deve essere una revisione: senza padre non c'e' niente da riportare.
    IF NEW.revisione_padre_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- (3) Il padre dev'essere effettivamente in uno stato di superamento.
    SELECT sp.is_superato
      INTO v_padre_superato
      FROM vendite.offerte_commerciali p
      JOIN config.stati_doc_offerte sp ON sp.id = p.stato_doc_offerta_id
     WHERE p.id = NEW.revisione_padre_id;

    IF NOT COALESCE(v_padre_superato, false) THEN
        RETURN NULL;
    END IF;

    -- (4) ⛔ Nessun'ALTRA figlia viva. Il modello non vieta due revisioni con
    --     lo stesso padre (revisione_padre_id ha un indice parziale, non uno
    --     UNIQUE): se ce ne fosse un'altra ancora viva, il padre resterebbe
    --     superato da quella e riportarlo indietro creerebbe due revisioni
    --     vive sullo stesso lineage.
    SELECT count(*)
      INTO v_altre_vive
      FROM vendite.offerte_commerciali f
      JOIN config.stati_doc_offerte sf ON sf.id = f.stato_doc_offerta_id
     WHERE f.revisione_padre_id = NEW.revisione_padre_id
       AND f.id <> NEW.id
       AND sf.is_abortito IS FALSE;

    IF v_altre_vive > 0 THEN
        RETURN NULL;
    END IF;

    -- Stato di ritorno: EMESSA. Non e' una scelta fra tante — e' l'unico
    -- stato da cui fn_crea_revisione_offerta ammette di partire, quindi
    -- un'offerta superata era EMESSA un attimo prima, per guard scritto.
    -- Guard sull'ARITA': zero o due righe sono lo stesso difetto, il
    -- catalogo non dice quale.
    SELECT count(*), min(s.id)
      INTO v_n_emessa, v_stato_emessa_id
      FROM config.stati_doc_offerte s
     WHERE s.codice_interno = 'EMESSA'
       AND s.attivo IS TRUE;

    IF v_n_emessa <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'tabella', 'config.stati_doc_offerte',
                'codice',  'EMESSA',
                'attesi',  1,
                'trovati', v_n_emessa
            ),
            NEW.tx_id,
            'config.stati_doc_offerte: atteso esattamente uno stato attivo '
            || 'EMESSA per il rientro del padre, trovati ' || v_n_emessa::text
        );
    END IF;

    -- Rientro. Passa dal guard _a10_ di transizione, che verifica sia
    -- l'ammissibilita' SUPERATA->EMESSA sia la regola «nessuna revisione
    -- figlia viva» (20260828-12). Qui la figlia risulta gia' annullata:
    -- siamo in un AFTER UPDATE, la riga e' scritta.
    -- ⚠️ Ricorsione: l'UPDATE riaccende questo trigger sul padre, che entra
    -- in EMESSA — non abortito — e si ferma alla condizione (1).
    UPDATE vendite.offerte_commerciali
       SET stato_doc_offerta_id = v_stato_emessa_id
     WHERE id = NEW.revisione_padre_id;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_rientro_padre()
IS 'AFTER UPDATE OF stato_doc_offerta_id su vendite.offerte_commerciali: quando una revisione viene annullata e non resta nessun''altra revisione viva dello stesso padre, riporta il padre da SUPERATA a EMESSA. Inverso di trgfn_offerte_commerciali_revisione. Chiude il limite «ultima revisione annullata senza successore -> nessuna offerta del lineage attiva» e allinea le offerte alla regola che i preventivi hanno per costruzione: una revisione abortita non rimpiazza nessuno. La META'' che VIETA il rientro fuori da questo caso sta nel guard di transizione, perche'' e'' una regola e non un automatismo. rev 2026-08-28.';
```

</div>

---
{% include-markdown "signature-core.md" %}
