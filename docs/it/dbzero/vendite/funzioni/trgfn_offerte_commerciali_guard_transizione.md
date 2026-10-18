{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_guard_transizione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- Scopo: bloccare transizioni stato non ammesse sul workflow offerta
-- commerciale (config-driven via stati_doc_offerte_transizioni).
-- Valorizza i timestamp di passaggio stato e applica guard listino
-- al momento dell'emissione (BOZZA->EMESSA).
-- rev 2026-08-28: + regola del rientro da uno stato di superamento;
-- data_emissione non si riscrive su un secondo ingresso in EMESSA.
-- rev 2026-09-24: + i prezzi non autorizzati verso EMESSA e ACCETTATA,
-- dal building block script.fn_check_prezzi_autorizzati; escluso il
-- rientro da uno stato di superamento (brief-db-preventivi-congelamento-
-- pricing, D-4/D-5).
-- rev 2026-10-07: BOZZA->EMESSA congela la versione di listino (la fissata,
-- altrimenti quella in vigore oggi) dopo il predicato
-- script.fn_check_listino_congelabile (brief-db-offerta-emissione-ed-
-- erogazione §C.1.3).
-- rev 2026-10-11: BOZZA->EMESSA solleva anche il primo motivo di
-- script.fn_check_indirizzi_documento_cliente — un indirizzo d'anagrafica
-- che non e' del cliente dell'offerta (brief-db-indirizzi-documento-
-- seguono-il-cliente, D-3).
DECLARE
    v_codice_da config.stati_doc_offerte.codice_interno%TYPE;
    v_codice_a  config.stati_doc_offerte.codice_interno%TYPE;
    v_superato_da boolean;
    v_superato_a  boolean;
    v_figlia_viva_codice vendite.offerte_commerciali.codice%TYPE;
BEGIN
    -- Nessuna transizione effettiva: niente da validare.
    IF OLD.stato_doc_offerta_id = NEW.stato_doc_offerta_id THEN
        RETURN NEW;
    END IF;

    -- Risolve i codici interni degli stati per messaggi leggibili,
    -- e la dichiarazione di superamento dei due estremi.
    SELECT
        max(CASE WHEN id = OLD.stato_doc_offerta_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_offerta_id THEN codice_interno END),
        bool_or(id = OLD.stato_doc_offerta_id AND is_superato IS TRUE),
        bool_or(id = NEW.stato_doc_offerta_id AND is_superato IS TRUE)
      INTO v_codice_da, v_codice_a, v_superato_da, v_superato_a
      FROM config.stati_doc_offerte
     WHERE id IN (OLD.stato_doc_offerta_id, NEW.stato_doc_offerta_id);

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

    -- ⭐ RIENTRO da uno stato di superamento. La transizione SUPERATA->EMESSA
    -- esiste per l'automatismo «annullo la revisione, il padre torna vivo»
    -- (trg_offerte_commerciali_z90_rientro_padre_upd). Ma una transizione
    -- ammessa e' una porta aperta a chiunque scriva, quindi la condizione va
    -- detta qui, dove vale per tutti: si esce dal superamento SOLO se non c'e'
    -- piu' una revisione figlia viva. Altrimenti il lineage avrebbe due
    -- revisioni vive insieme, che e' l'invariante che il dominio non ammette.
    IF COALESCE(v_superato_da, false) AND NOT COALESCE(v_superato_a, false) THEN

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

    -- Emissione (BOZZA -> EMESSA), rev 2026-10-07 (brief-db-offerta-
    -- emissione-ed-erogazione §C.1.3): l'offerta vive sulla versione di
    -- listino in vigore e la CONGELA qui, nella stessa scrittura del cambio
    -- stato. Prima il predicato, script.fn_check_listino_congelabile: lo
    -- stesso con cui fn_available_actions_offerta spegne «Emetti», quindi
    -- pulsante e guard non possono dissentire. Poi il congelamento,
    -- vendite.fn_listino_versione_operativa: la fissata se c'e', altrimenti
    -- quella in vigore oggi.
    -- ⚠️ Fino a questa rev la versione la fissava il backend prima del
    --   cambio stato, e la capability guardava la colonna nuda: «Emetti»
    --   restava spento perche' il congelamento non c'era ancora stato.
    IF v_codice_da = 'BOZZA' AND v_codice_a = 'EMESSA' THEN
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

    -- Prezzi non autorizzati (rev 2026-09-24): un'offerta con un prezzo che
    -- nessuno ha autorizzato — in attesa o rifiutato, su eccezioni o loro
    -- componenti BoM attivi — non va al cliente (EMESSA) e non diventa un
    -- impegno (ACCETTATA). D-1, D-4.
    --
    -- ⭐ Il predicato e' il building block script.fn_check_prezzi_autorizzati,
    --   lo STESSO che fn_available_actions_offerta usa per spegnere i
    --   pulsanti: qui si solleva soltanto.
    -- ⛔ NON sul RIENTRO da uno stato di superamento (SUPERATA -> EMESSA):
    --   e' l'automatismo «annullo la revisione, il padre torna vivo»
    --   (trg_offerte_commerciali_z90_rientro_padre_upd), non un invio al
    --   cliente — l'offerta era gia' stata mandata. Un prezzo rimasto non
    --   autorizzato sul padre bloccherebbe l'ANNULLAMENTO della revisione,
    --   cioe' una via d'uscita (D-2). Letto dal flag is_superato, non da un
    --   codice.
    IF v_codice_a IN ('EMESSA', 'ACCETTATA')
       AND NOT COALESCE(v_superato_da, false) THEN
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

    -- Indirizzi del cliente (rev 2026-10-11, brief-db-indirizzi-documento-
    -- seguono-il-cliente, D-3 di Tid): il cliente dell'offerta (BA/istanza) si
    -- cambia in bozza, e un indirizzo d'anagrafica del cliente di prima, o di
    -- una fornitura che l'offerta non ha piu', non va al cliente.
    -- ⭐ Il predicato e' script.fn_check_indirizzi_documento_cliente, lo
    --   stesso che fn_available_actions_offerta legge per spegnere «Emetti»,
    --   dopo listino e prezzi: lo stesso ordine qui.
    -- ⚠️ Solo all'emissione (BOZZA -> EMESSA): il rientro da uno stato di
    --   superamento non e' un invio al cliente.
    IF v_codice_da = 'BOZZA' AND v_codice_a = 'EMESSA' THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_indirizzi_documento_cliente('OFFERTA', NEW.id),
            'tipo_indirizzo_id',
            NEW.tx_id,
            jsonb_build_object(
                'offerta_id', NEW.id,
                'codice',     NEW.codice,
                'stato_da',   v_codice_da,
                'stato_a',    v_codice_a));
    END IF;

    -- Valorizza il timestamp corrispondente al passaggio stato.
    -- ⚠️ data_emissione con COALESCE: un rientro SUPERATA->EMESSA e' un
    -- SECONDO ingresso in EMESSA, e riscrivere la data cancellerebbe il
    -- giorno in cui l'offerta e' stata davvero mandata al cliente. Sul primo
    -- ingresso (BOZZA->EMESSA) la colonna e' NULL: valore identico a prima.
    CASE v_codice_a
        WHEN 'EMESSA'    THEN NEW.data_emissione    := COALESCE(NEW.data_emissione, now());
        WHEN 'ACCETTATA' THEN NEW.data_accettazione := now();
        WHEN 'RIFIUTATA' THEN NEW.data_rifiuto      := now();
        WHEN 'ANNULLATA' THEN NEW.data_annullamento  := now();
        ELSE NULL;
    END CASE;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_guard_transizione()
IS 'BEFORE UPDATE OF stato_doc_offerta_id: blocca transizioni non ammesse (config-driven via config.stati_doc_offerte_transizioni). Guard BOZZA->EMESSA: listino_versione_id NOT NULL + stato ATTIVA. Regola del RIENTRO (rev 2026-08-28): si esce da uno stato con is_superato solo se non esiste piu'' una revisione figlia non abortita, altrimenti E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA — la condizione vale per chiunque scriva, non solo per il trigger di rientro. Valorizza data_accettazione|data_rifiuto|data_annullamento, e data_emissione solo se ancora NULL (un rientro non riscrive la data di emissione reale). rev 2026-09-24: verso EMESSA e ACCETTATA solleva il primo motivo di script.fn_check_prezzi_autorizzati (prezzi PENDING o REJECTED su eccezioni e loro componenti BoM attivi, E_DOC_PREZZO_PENDENTE / E_DOC_PREZZO_RIFIUTATO) — prima nessun controllo sul prezzo. ⛔ Non sul rientro da uno stato di superamento (flag is_superato): e'''' l''''automatismo del padre che torna vivo, e bloccarlo fermerebbe l''''annullamento della revisione. La capability fn_available_actions_offerta legge la stessa funzione. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-4, D-5). Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.3): BOZZA->EMESSA non pretende più una versione già fissata, la CONGELA: solleva il primo motivo di script.fn_check_listino_congelabile(''OFFERTA'', ...) — nessuna versione in vigore oggi (E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO) o versione fissata non ATTIVA (E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA), lo stesso predicato della capability — poi scrive NEW.listino_versione_id := vendite.fn_listino_versione_operativa (la fissata, altrimenti quella in vigore oggi), nella stessa scrittura del cambio stato. Prima la fissava il backend, e la capability spegneva «Emetti» perché non era ancora fissata. rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-3 di Tid): BOZZA->EMESSA solleva anche il primo motivo di script.fn_check_indirizzi_documento_cliente(''OFFERTA'', id) — E_INDIRIZZO_DOC_NON_DEL_CLIENTE, un indirizzo d''anagrafica che non e'' del cliente dell''offerta (altro ruolo, o fornitura diversa) — dopo listino e prezzi, nell''ordine della capability. ⭐ rev 2026-10-19 (20261019-28, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. ⚠️ fn_check_indirizzi_documento_cliente riceve ancora OFFERTA: grammatica delle testate, lotto 2.';
```

---
{% include-markdown "signature-core.md" %}
