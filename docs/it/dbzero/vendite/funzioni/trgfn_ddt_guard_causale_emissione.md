{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_causale_emissione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_causale_emissione`

```sql
CREATE FUNCTION trgfn_ddt_guard_causale_emissione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: gate all'emissione (EMESSO) di un DDT sul VALORE DELLA
--   RIGA, in tre facce (brief-db-fatturazione-ddt-resi §4a, DL-28):
--     1. la causale di trasporto e' dichiarata;
--     2. se e' fatturabile, ogni riga attiva ha un prezzo
--        risolvibile (proprio o ereditato dalla riga d'ordine);
--     3. ogni riga attiva CHE PORTA UN PREZZO ha anche l'aliquota.
--   rev 2026-07-19: valutazione delegata a
--   script.fn_check_ddt_emittibile — single source con la capability.
--   rev 2026-08-28 (brief-db-ddt-riconsegna-eredita-testata, Fase C):
--   + E_DDT_RIGA_IVA_MANCANTE.
--   rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-2):
--   + E_DDT_CLIENTE_OBBLIGATORIO (la causale vuole un cliente e il
--   billing account manca).
--   rev 2026-11-03 (20261103-42, brief-db-addebito-trasporto-ordine §8.3):
--   + E_DDT_EMISSIONE_SOLO_ONERI (righe, ma nessuna di merce: K-2) e
--   + E_DDT_ONERE_NON_FATTURABILE (un onere che non verrebbe mai
--   fatturato: causale non fatturabile, o onere senza legame su una bolla
--   di un ordine che fattura alla conferma).
--
-- ⚠️ IL NOME NOMINA LA SOLA CAUSALE, ed e' rimasto quello di quando
--   il motivo era uno. Non si rinomina — costerebbe il trigger, ogni
--   doc auto-gen e ogni pgTAP che la citano, per sola leggibilita' —
--   ma chi legge non deve dedurlo: e' scritto qui.
--
-- ⚠️ Il LOOP non ha un ELSE: i motivi che questa funzione non
--   riconosce li solleva un altro dei quattro guard di emissione. Un
--   catch-all qui farebbe sollevare a QUESTO trigger anche gli
--   indirizzi mancanti, con l'area e il nome sbagliati nel log.
DECLARE
    -- La bolla e' nello stato di emissione? Dal vocabolario.
    v_emissione    config.stati_doc_ddt.emissione%TYPE;
    v_motivo        jsonb;
BEGIN
    SELECT sdd.emissione INTO v_emissione
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    -- rev 2026-11-14 (giro 6d): lo stato di emissione, la colonna del
    -- vocabolario. Uno stato che non si legge non e' l'emissione.
    IF v_emissione IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    FOR v_motivo IN
        SELECT jsonb_array_elements(script.fn_check_ddt_emittibile(NEW))
    LOOP
        IF v_motivo->>'codice' = 'E_DDT_CAUSALE_OBBLIGATORIA' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_CAUSALE_OBBLIGATORIA',
                jsonb_build_object(
                    'ddt_id', NEW.id,
                    'numero', NEW.numero),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text)
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_CLIENTE_OBBLIGATORIO' THEN
            -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-2): la
            --   causale manda merce a un cliente e il billing account
            --   manca. Nel VARIADIC il documento e il CODICE della causale
            --   (la cosa che l'operatore ha scelto e riconosce); il campo
            --   da accendere e' il billing account — ma il codice e'
            --   CONFLITTO_STATO come i fratelli: la richiesta e' «emetti».
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_CLIENTE_OBBLIGATORIO',
                jsonb_build_object(
                    'ddt_id',  NEW.id,
                    'numero',  NEW.numero,
                    'causale', v_motivo->'dettaglio'->>'causale'),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'causale', '?')
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_PREZZO_NON_RISOLVIBILE' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_PREZZO_NON_RISOLVIBILE',
                jsonb_build_object(
                    'ddt_id',   NEW.id,
                    'numero',   NEW.numero,
                    'riga_id',  (v_motivo->'dettaglio'->>'riga_id')::bigint),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'riga_id', 'NULL')
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_RIGA_IVA_MANCANTE' THEN
            -- ⚠️ Nel VARIADIC va il NUMERO di riga, non l'id: quel
            --   valore riempie i %s, cioe' compone la frase che una
            --   persona legge, e un id tecnico non si cerca a mano
            --   sul documento. L'id viaggia nel context, che e' il
            --   canale di chi diagnostica.
            -- ⛔ E nessuna chiave `campo`: il codice e'
            --   CONFLITTO_STATO, non DATO_ERRATO — la richiesta e'
            --   «porta il DDT a EMESSO», e non c'e' un campo di
            --   QUELLA richiesta da accendere.
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_RIGA_IVA_MANCANTE',
                jsonb_build_object(
                    'ddt_id',   NEW.id,
                    'numero',   NEW.numero,
                    'riga_id',  (v_motivo->'dettaglio'->>'riga_id')::bigint,
                    'riga_nr',  (v_motivo->'dettaglio'->>'riga_nr')::integer),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'riga_nr', '?')
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_EMISSIONE_SOLO_ONERI' THEN
            -- rev 2026-11-03 (K-2): la bolla ha righe, ma nessuna di merce.
            --   VARIADIC: il documento. CONFLITTO_STATO come i fratelli: la
            --   richiesta e' «emetti», nessun campo da accendere.
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_EMISSIONE_SOLO_ONERI',
                jsonb_build_object(
                    'ddt_id', NEW.id,
                    'numero', NEW.numero),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text)
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_ONERE_NON_FATTURABILE' THEN
            -- rev 2026-11-03 (§8.3, K-7/K-8): la riga-onere che non verrebbe
            --   mai fatturata. VARIADIC: documento e NUMERO di riga (la frase
            --   la legge una persona); l'id resta nel context.
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_ONERE_NON_FATTURABILE',
                jsonb_build_object(
                    'ddt_id',   NEW.id,
                    'numero',   NEW.numero,
                    'riga_id',  (v_motivo->'dettaglio'->>'riga_id')::bigint,
                    'riga_nr',  (v_motivo->'dettaglio'->>'riga_nr')::integer),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'riga_nr', '?')
            );
        ELSIF v_motivo->>'codice' = 'E_DDT_TRASPORTO_NON_DOVUTO' THEN
            -- rev 2026-11-03 (20261103-48, T-3 bis): l'onere di trasporto su
            --   una bolla in porto assegnato o con addebito a terzi. VARIADIC:
            --   documento, NUMERO di riga, modalita' leggibile; l'id resta nel
            --   context. CONFLITTO_STATO come i fratelli.
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME, 'E_DDT_TRASPORTO_NON_DOVUTO',
                jsonb_build_object(
                    'ddt_id',   NEW.id,
                    'numero',   NEW.numero,
                    'riga_id',  (v_motivo->'dettaglio'->>'riga_id')::bigint,
                    'riga_nr',  (v_motivo->'dettaglio'->>'riga_nr')::integer,
                    'modalita', v_motivo->'dettaglio'->>'modalita'),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text),
                COALESCE(v_motivo->'dettaglio'->>'riga_nr', '?'),
                COALESCE(v_motivo->'dettaglio'->>'modalita_descrizione', v_motivo->'dettaglio'->>'modalita', '?')
            );
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
IS 'Il gate all''emissione della bolla sul valore delle righe: scatta quando la bolla e'' nello stato di emissione (la colonna emissione di config.stati_doc_ddt) e solleva, uno per codice, i motivi di script.fn_check_ddt_emittibile, la stessa check della capability. La causale di trasporto e'' obbligatoria (in bozza il NULL resta legittimo); con una causale fatturabile ogni riga attiva ha un prezzo risolvibile (proprio o ereditato dalla riga d''ordine attraverso il legame di evasione); ogni riga attiva che porta un prezzo ha anche l''aliquota (E_DDT_RIGA_IVA_MANCANTE; nella frase il numero di riga, l''id nel contesto); se la causale manda merce a un cliente (config.causali_trasporto.richiede_cliente) la bolla ha il billing account (E_DDT_CLIENTE_OBBLIGATORIO); una bolla di soli oneri non si emette (E_DDT_EMISSIONE_SOLO_ONERI); un onere che non verrebbe mai fatturato si ferma (E_DDT_ONERE_NON_FATTURABILE: causale non fatturabile, o onere senza legame su una bolla il cui ordine di testata fattura alla conferma); l''onere di trasporto su una bolla in porto ASSEGNATO o con addebito a TERZI si ferma (E_DDT_TRASPORTO_NON_DOVUTO). Tutti CONFLITTO_STATO. Il nome nomina la sola causale ed e'' rimasto quello di quando il motivo era uno.';
```

</div>

---
{% include-markdown "signature-core.md" %}
