{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_guard_transizione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il guard del cambio di stato dell'offerta commerciale. La
--   transizione deve stare nella matrice (config.stati_doc_offerte_
--   transizioni, righe attive); poi le regole del passaggio, ognuna sul
--   SIGNIFICATO che il vocabolario dichiara in colonna, mai sul codice:
--   - l'emissione (dallo stato iniziale allo stato di emissione) congela la
--     versione di listino e giudica indirizzi e righe;
--   - verso l'emissione e verso l'accettazione, i prezzi autorizzati;
--   - verso lo stato di annullo, i documenti vivi nati dall'offerta;
--   - l'uscita da uno stato di superamento, la revisione figlia viva;
--   - la data del passaggio, dal significato dello stato di destinazione.
--   I codici servono solo ai messaggi.
DECLARE
    -- I codici degli estremi, per i messaggi.
    v_codice_da       config.stati_doc_offerte.codice_interno%TYPE;
    v_codice_a        config.stati_doc_offerte.codice_interno%TYPE;
    -- Il significato degli estremi, dalle colonne del vocabolario.
    v_iniziale_da     config.stati_doc_offerte.iniziale%TYPE;
    v_superato_da     config.stati_doc_offerte.is_superato%TYPE;
    v_emissione_a     config.stati_doc_offerte.emissione%TYPE;
    v_accettazione_a  config.stati_doc_offerte.accettazione%TYPE;
    v_rifiuto_a       config.stati_doc_offerte.rifiuto%TYPE;
    v_abortito_a      config.stati_doc_offerte.is_abortito%TYPE;
    v_superato_a      config.stati_doc_offerte.is_superato%TYPE;
    v_figlia_viva_codice vendite.offerte_commerciali.codice%TYPE;
BEGIN
    -- Nessuna transizione effettiva: niente da validare.
    IF OLD.stato_doc_offerta_id = NEW.stato_doc_offerta_id THEN
        RETURN NEW;
    END IF;

    -- Le due righe del vocabolario, lette una volta: le colonne dicono il
    -- significato, il codice resta per i messaggi. Lo stato e' una FK verso
    -- il vocabolario: le due righe ci sono.
    SELECT s.codice_interno, s.iniziale, s.is_superato
      INTO v_codice_da, v_iniziale_da, v_superato_da
      FROM config.stati_doc_offerte s
     WHERE s.id = OLD.stato_doc_offerta_id;

    SELECT s.codice_interno, s.emissione, s.accettazione, s.rifiuto,
           s.is_abortito, s.is_superato
      INTO v_codice_a, v_emissione_a, v_accettazione_a, v_rifiuto_a,
           v_abortito_a, v_superato_a
      FROM config.stati_doc_offerte s
     WHERE s.id = NEW.stato_doc_offerta_id;

    -- Verifica transizione ammessa (config-driven, solo righe attive).
    IF NOT EXISTS (
        SELECT 1
          FROM config.stati_doc_offerte_transizioni
         WHERE stato_da_id = OLD.stato_doc_offerta_id
           AND stato_a_id  = NEW.stato_doc_offerta_id
           AND attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_OFFERTA_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'offerta_id', NEW.id,
                'stato_da',   coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
                'stato_a',    coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text)
            ),
            NEW.tx_id,
            coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
            coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text)
        );
    END IF;

    -- ⭐ RIENTRO da uno stato di superamento. La transizione di rientro
    -- esiste per l'automatismo «annullo la revisione, il padre torna vivo»
    -- (trg_offerte_commerciali_z90_rientro_padre_upd). Ma una transizione
    -- ammessa e' una porta aperta a chiunque scriva, quindi la condizione va
    -- detta qui, dove vale per tutti: si esce dal superamento SOLO se non c'e'
    -- piu' una revisione figlia viva. Altrimenti il lineage avrebbe due
    -- revisioni vive insieme, che e' l'invariante che il dominio non ammette.
    IF v_superato_da AND NOT v_superato_a THEN

        -- Una figlia "viva" e' una revisione il cui stato non e' di
        -- annullamento: una revisione abortita non rimpiazza nessuno.
        -- ⚠️ Legge sotto RLS, e regge perche' le figlie ereditano
        -- l'emittente del padre (fn_crea_revisione_offerta) e la policy
        -- scopa per emittente: chi aggiorna il padre vede le figlie.
        SELECT f.codice
          INTO v_figlia_viva_codice
          FROM vendite.offerte_commerciali f
          JOIN config.stati_doc_offerte sf
            ON sf.id = f.stato_doc_offerta_id
         WHERE f.revisione_padre_id = NEW.id
           AND sf.is_abortito IS FALSE
         ORDER BY f.revisione_numero DESC, f.id DESC
         LIMIT 1;

        IF v_figlia_viva_codice IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA',
                jsonb_build_object(
                    'offerta_id',   NEW.id,
                    'stato_da',     coalesce(v_codice_da, OLD.stato_doc_offerta_id::text),
                    'stato_a',      coalesce(v_codice_a,  NEW.stato_doc_offerta_id::text),
                    'revisione_viva_codice', v_figlia_viva_codice
                ),
                NEW.tx_id,
                coalesce(NEW.codice, NEW.id::text),
                v_figlia_viva_codice
            );
        END IF;

    END IF;

    -- L'emissione (dallo stato iniziale allo stato di emissione): l'offerta
    -- vive sulla versione di listino in vigore e la CONGELA qui, nella stessa
    -- scrittura del cambio stato. Prima il predicato,
    -- script.fn_check_listino_congelabile: lo stesso con cui
    -- fn_available_actions_offerta spegne «Emetti», quindi pulsante e guard
    -- non possono dissentire. Poi il congelamento,
    -- vendite.fn_listino_versione_operativa: la fissata se c'e', altrimenti
    -- quella in vigore oggi.
    -- ⚠️ Dallo stato INIZIALE, non da qualunque stato verso l'emissione: il
    --   rientro da uno stato di superamento arriva anche lui nello stato di
    --   emissione, e non e' un invio al cliente.
    IF v_iniziale_da AND v_emissione_a THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_listino_congelabile('OFFERTA_COMMERCIALE', NEW.listino_id, NEW.listino_versione_id),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));

        NEW.listino_versione_id := vendite.fn_listino_versione_operativa(
            NEW.listino_id, NEW.listino_versione_id);
    END IF;

    -- Prezzi non autorizzati: un'offerta con un prezzo che nessuno ha
    -- autorizzato — in attesa o rifiutato, su eccezioni o loro componenti BoM
    -- attivi — non va al cliente (stato di emissione) e non diventa un
    -- impegno (stato di accettazione).
    --
    -- ⭐ Il predicato e' il building block script.fn_check_prezzi_autorizzati,
    --   lo STESSO che fn_available_actions_offerta usa per spegnere i
    --   pulsanti: qui si solleva soltanto.
    -- ⛔ NON sul RIENTRO da uno stato di superamento: e' l'automatismo
    --   «annullo la revisione, il padre torna vivo»
    --   (trg_offerte_commerciali_z90_rientro_padre_upd), non un invio al
    --   cliente — l'offerta era gia' stata mandata. Un prezzo rimasto non
    --   autorizzato sul padre bloccherebbe l'ANNULLAMENTO della revisione,
    --   cioe' una via d'uscita.
    IF (v_emissione_a OR v_accettazione_a) AND NOT v_superato_da THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_prezzi_autorizzati('vendite.offerte_commerciali'::regclass, NEW.id),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));
    END IF;

    -- Indirizzi del cliente: il cliente dell'offerta (BA/istanza) si cambia
    -- in bozza, e un indirizzo d'anagrafica del cliente di prima, o di una
    -- fornitura che l'offerta non ha piu', non va al cliente.
    -- ⭐ Il predicato e' script.fn_check_indirizzi_documento_cliente, lo
    --   stesso che fn_available_actions_offerta legge per spegnere «Emetti»,
    --   dopo listino e prezzi: lo stesso ordine qui.
    -- ⚠️ Solo all'emissione dallo stato iniziale: il rientro da uno stato di
    --   superamento non e' un invio al cliente.
    IF v_iniziale_da AND v_emissione_a THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_indirizzi_documento_cliente('OFFERTA_COMMERCIALE', NEW.id),
            'tipo_indirizzo_id',
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));
    END IF;

    -- Le righe: la regola di una riga dipende da dati che stanno fuori dalla
    -- riga (il listino operativo, il vocabolario del perimetro), e i guard di
    -- riga la giudicano solo quando la riga si scrive. Le righe gia' scritte
    -- le intercetta l'emissione.
    -- ⭐ Il predicato e' script.fn_check_righe_documento, lo stesso che
    --   fn_available_actions_offerta legge per spegnere «Emetti», dopo
    --   listino, prezzi e indirizzi: lo stesso ordine qui. Il contesto
    --   legge la versione di listino della riga in tabella (la fissata,
    --   altrimenti quella in vigore oggi), che e' quella congelata sopra.
    IF v_iniziale_da AND v_emissione_a THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_righe_documento('OFFERTA_COMMERCIALE', NEW.id),
            'articolo_id',
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));
    END IF;

    -- Annullo: dallo stato di accettazione si esce anche annullando, ma non
    -- sotto i piedi di un contratto o di un ordine ancora vivo nato
    -- dall'offerta: prima si annulla lui. Il predicato e'
    -- script.fn_check_offerta_annullabile, lo stesso della capability.
    -- Sulla DESTINAZIONE: dalla bozza non ci sono documenti, e passa.
    IF v_abortito_a THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_offerta_annullabile(NEW.id),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));
    END IF;

    -- La data del passaggio, dal significato dello stato di destinazione.
    -- ⚠️ data_emissione con COALESCE: un rientro da uno stato di superamento
    -- e' un SECONDO ingresso nello stato di emissione, e riscrivere la data
    -- cancellerebbe il giorno in cui l'offerta e' stata davvero mandata al
    -- cliente. Sul primo ingresso la colonna e' NULL.
    IF v_emissione_a THEN
        NEW.data_emissione := COALESCE(NEW.data_emissione, now());
    ELSIF v_accettazione_a THEN
        NEW.data_accettazione := now();
    ELSIF v_rifiuto_a THEN
        NEW.data_rifiuto := now();
    ELSIF v_abortito_a THEN
        NEW.data_annullamento := now();
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
IS 'Guard del cambio di stato dell''offerta commerciale (BEFORE UPDATE OF stato_doc_offerta_id). Ogni regola legge il significato dello stato dalle colonne del vocabolario config.stati_doc_offerte, mai il codice, che serve solo ai messaggi. (1) La transizione deve essere una riga attiva di config.stati_doc_offerte_transizioni, altrimenti E_OFFERTA_TRANSIZIONE_NON_AMMESSA. (2) Si esce da uno stato is_superato solo se non resta una revisione figlia non abortita, altrimenti E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA: la condizione vale per chiunque scriva, non solo per l''automatismo del rientro. (3) L''emissione, dallo stato iniziale allo stato di emissione, solleva il primo motivo di script.fn_check_listino_congelabile e congela la versione di listino (vendite.fn_listino_versione_operativa: la fissata, altrimenti quella in vigore oggi); poi il primo motivo di script.fn_check_indirizzi_documento_cliente e quello di script.fn_check_righe_documento. Il rientro da uno stato di superamento non e'' un''emissione. (4) Verso lo stato di emissione e quello di accettazione, fuori dal rientro, il primo motivo di script.fn_check_prezzi_autorizzati (E_DOC_PREZZO_PENDENTE, E_DOC_PREZZO_RIFIUTATO). (5) Verso lo stato di annullo (is_abortito), il primo motivo di script.fn_check_offerta_annullabile (E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI). (6) La data del passaggio: emissione -> data_emissione, solo se ancora NULL (un rientro non riscrive il giorno dell''invio); accettazione -> data_accettazione; rifiuto -> data_rifiuto; is_abortito -> data_annullamento. I predicati sono gli stessi che script.fn_available_actions_offerta legge per spegnere i pulsanti, nello stesso ordine.';
```

</div>

---
{% include-markdown "signature-core.md" %}
