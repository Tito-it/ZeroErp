{% include-markdown "it/dbzero/script/manual/fn_available_actions_offerta.md" %}
# ⚙️ Funzione `fn_available_actions_offerta`

```sql
CREATE FUNCTION fn_available_actions_offerta(p_offerta_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la capability dell'offerta commerciale per il dettaglio: le azioni
--   di stato proposte (dalla matrice, coi motivi che le spengono), le azioni
--   applicative (crea revisione, genera contratto, genera ordine), cosa si
--   modifica nello stato, il PDF, la nota e il significato dello stato
--   corrente. Il significato di uno stato lo dice il vocabolario
--   (iniziale, emissione, accettazione, is_abortito, terminale), mai il
--   codice; i predicati sono gli stessi del guard di transizione e dei verbi,
--   nello stesso ordine. Dettaglio nel COMMENT.
DECLARE
    -- Tipi nudi solo per valori CALCOLATI (azioni e motivi jsonb, flag,
    -- motivi e chiavi i18n composti): nessuna colonna di cui siano il riflesso.
    v_stato_id    vendite.offerte_commerciali.stato_doc_offerta_id%TYPE;
    v_stato_cod   config.stati_doc_offerte.codice_interno%TYPE;
    -- Lo stato di oggi e' l'iniziale? l'accettazione? l'emissione? e'
    -- terminale? Dal vocabolario.
    v_iniziale     config.stati_doc_offerte.iniziale%TYPE;
    v_accettazione config.stati_doc_offerte.accettazione%TYPE;
    v_emissione    config.stati_doc_offerte.emissione%TYPE;
    v_terminale    config.stati_doc_offerte.terminale%TYPE;
    v_stato_info_key      text;
    v_pdf_mode    config.stati_doc_offerte.pdf_mode%TYPE;
    v_pdf_allow   config.stati_doc_offerte.pdf_allow_allegati%TYPE;
    v_listino_id          vendite.offerte_commerciali.listino_id%TYPE;
    v_listino_versione_id vendite.offerte_commerciali.listino_versione_id%TYPE;
    v_mot_prezzi          jsonb := '[]'::jsonb;
    v_mot_emetti          jsonb := '[]'::jsonb;
    v_mot_rev             jsonb := '[]'::jsonb;
    v_mot_annulla         jsonb := '[]'::jsonb;
    v_mot_push            jsonb := '[]'::jsonb;
    v_mot_ordine          jsonb := '[]'::jsonb;
    v_actions     jsonb;
    v_can_edit    boolean;
    v_can_rev     boolean;
    v_has_contratto boolean;
    v_has_ordine    boolean;
    v_enabled       boolean;
    v_can_push    boolean;
    v_push_reason     text;
    v_push_reason_key text;
    v_can_ordine        boolean;
    v_ordine_reason     text;
    v_ordine_reason_key text;
    c_sempre_non_edit CONSTANT jsonb :=
        '["codice","uid","revisione_numero","revisione_padre_id",'
        '"stato_doc_offerta_id","data_emissione","data_accettazione",'
        '"data_rifiuto","data_annullamento"]'::jsonb;
    -- ⚠️ motivazione_rifiuto non e' piu' fra le «sempre» (rev
    -- 2026-10-11, R-DB-2): la governa il montaggio del lock di testata,
    -- aperta in EMESSA e ACCETTATA (D-10).
    -- Azioni applicative: non sono transizioni, quindi
    -- target_state e target_state_descrizione restano NULL.
    c_action_crea_revisione CONSTANT jsonb := jsonb_build_object(
        'key',                      'crea_revisione',
        'target_state',             NULL,
        'target_state_descrizione', NULL,
        'label_key',                'vendite.offerte.azione_crea_revisione',
        'requires_confirm',         true,
        'requires_motivazione',     false,
        'outlined',                 false,
        'enabled',                  true,
        'reason',                   NULL,
        'reason_key',               NULL
    );
    c_action_push_contratto CONSTANT jsonb := jsonb_build_object(
        'key',                      'push_contratto',
        'target_state',             NULL,
        'target_state_descrizione', NULL,
        'label_key',                'vendite.offerte.azione_push_contratto',
        'requires_confirm',         true,
        'requires_motivazione',     false,
        'outlined',                 false,
        'enabled',                  true,
        'reason',                   NULL,
        'reason_key',               NULL
    );
    c_action_genera_ordine CONSTANT jsonb := jsonb_build_object(
        'key',                      'genera_ordine',
        'target_state',             NULL,
        'target_state_descrizione', NULL,
        'label_key',                'vendite.offerte.azione_genera_ordine',
        'requires_confirm',         true,
        'requires_motivazione',     false,
        'outlined',                 false,
        'enabled',                  true,
        'reason',                   NULL,
        'reason_key',               NULL
    );
    -- La testata nello stato, dal montaggio del lock (rev 2026-10-10):
    -- {modificabile, non_modificabili}.
    v_testata jsonb;
BEGIN
    -- Stato corrente + versione listino + capability PDF.
    SELECT o.stato_doc_offerta_id, sdo.codice_interno,
           sdo.iniziale, sdo.accettazione, sdo.emissione, sdo.terminale,
           sdo.pdf_mode, sdo.pdf_allow_allegati,
           o.listino_id, o.listino_versione_id,
           sdo.meta->>'nessuna_azione_key'
      INTO v_stato_id, v_stato_cod, v_iniziale, v_accettazione, v_emissione, v_terminale,
           v_pdf_mode, v_pdf_allow,
           v_listino_id, v_listino_versione_id, v_stato_info_key
      FROM vendite.offerte_commerciali o
      JOIN config.stati_doc_offerte sdo ON sdo.id = o.stato_doc_offerta_id
     WHERE o.id = p_offerta_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Motivi dei prezzi non autorizzati (rev 2026-09-24): lo stesso
    -- building block con cui trgfn_offerte_commerciali_guard_transizione
    -- solleva verso EMESSA e ACCETTATA, quindi pulsanti e guard non
    -- possono divergere. Il rientro da SUPERATA non e' un'azione manuale:
    -- non compare qui (filtro `manuale` sotto).
    v_mot_prezzi := script.fn_check_prezzi_autorizzati('vendite.offerte_commerciali'::regclass,
                                                       p_offerta_id);

    -- Verso EMESSA: prima il listino (senza, l'offerta non ha prezzi da
    -- autorizzare che reggano), poi i prezzi.
    -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.3): il
    -- motivo del listino lo dice script.fn_check_listino_congelabile, lo
    -- stesso predicato con cui il guard BOZZA->EMESSA solleva e poi congela.
    -- Giudica la versione che VERREBBE congelata (la fissata, altrimenti
    -- quella in vigore oggi), non la colonna nuda: prima «Emetti» restava
    -- spento proprio perche' il congelamento non c'era ancora stato.
    v_mot_emetti := script.fn_check_listino_congelabile('OFFERTA_COMMERCIALE', v_listino_id, v_listino_versione_id);
    v_mot_emetti := v_mot_emetti || v_mot_prezzi;
    -- rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-3):
    -- poi gli indirizzi che non sono del cliente, lo stesso building block e
    -- lo stesso ordine del guard BOZZA->EMESSA.
    v_mot_emetti := v_mot_emetti
                 || script.fn_check_indirizzi_documento_cliente('OFFERTA_COMMERCIALE', p_offerta_id);
    -- rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.2, H-R1):
    -- per ultime le righe che la regola intera non ammette piu', lo stesso
    -- building block e lo stesso ordine del guard all'emissione. Solo nello
    -- stato iniziale, l'unico da cui si emette: il contesto espande il listino.
    IF v_iniziale THEN
        v_mot_emetti := v_mot_emetti
                     || script.fn_check_righe_documento('OFFERTA_COMMERCIALE', p_offerta_id);
    END IF;

    -- rev 2026-10-21 (§H.3, H-R3): verso ANNULLATA, nessun contratto o
    -- ordine vivo nato dall'offerta — lo stesso predicato del guard.
    v_mot_annulla := script.fn_check_offerta_annullabile(p_offerta_id);

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',                t.meta->>'action_key',
                'target_state',       sa.codice_interno,
                -- Forma leggibile della destinazione: la colonna
                -- accanto, nello stesso JOIN.
                'target_state_descrizione', sa.descrizione,
                'label_key',          t.meta->>'label_key',
                'requires_confirm',   COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'requires_motivazione', COALESCE((t.meta->>'requires_motivazione')::boolean, false),
                'outlined',           COALESCE((t.meta->>'outlined')::boolean, false),
                -- Tutto discende dall'array dei motivi: nessuna
                -- regola puo' mascherarne un'altra (rev 2026-09-24).
                'enabled',            jsonb_array_length(m.motivi) = 0,
                'reason',             m.motivi -> 0 ->> 'reason',
                'reason_key',         m.motivi -> 0 ->> 'reason_key',
                'reasons',            m.motivi
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    -- I passaggi manuali che l'utente puo' fare, dal BB comune (rev
    -- 2026-10-27, 20261027-42, §15.14): matrice viva, manuale, permesso.
    FROM script.fn_doc_azioni_permesse('vendite.offerte_commerciali'::regclass, v_stato_id) t
    JOIN config.stati_doc_offerte sa ON sa.id = t.stato_a_id
    CROSS JOIN LATERAL (
        -- rev 2026-10-26 (20261026-27): l'emissione e l'annullo li dice il
        -- vocabolario (emissione, is_abortito), non il codice.
        SELECT CASE WHEN sa.emissione
                    THEN v_mot_emetti ELSE '[]'::jsonb END
            || CASE WHEN sa.accettazione
                    THEN v_mot_prezzi ELSE '[]'::jsonb END
            || CASE WHEN sa.is_abortito
                    THEN v_mot_annulla ELSE '[]'::jsonb END AS motivi
    ) m
    WHERE t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    v_can_rev := v_emissione;
    -- «Crea revisione» (rev 2026-09-24): proposta da EMESSA, SPENTA col
    -- motivo se il documento ha un prezzo IN ATTESA — lo stesso
    -- script.fn_check_prezzi_in_attesa con cui la madre
    -- vendite.fn_crea_revisione_offerta rifiuta. Pulsante e madre non possono
    -- dissentire. ⭐ can_create_revisione diventa VERITIERO: vero solo se
    -- la revisione si puo' davvero creare (il FE legge l'azione, non il
    -- flag; il BE lo trasporta).
    IF v_can_rev THEN
        v_mot_rev := script.fn_check_prezzi_in_attesa('vendite.offerte_commerciali'::regclass, p_offerta_id);
        v_actions := v_actions || jsonb_build_array(
            c_action_crea_revisione || jsonb_build_object(
                'enabled',    jsonb_array_length(v_mot_rev) = 0,
                'reason',     v_mot_rev -> 0 ->> 'reason',
                'reason_key', v_mot_rev -> 0 ->> 'reason_key',
                'reasons',    v_mot_rev));
        v_can_rev := jsonb_array_length(v_mot_rev) = 0;
    END IF;

    -- rev 2026-10-11 (D-3/D-6 di brief-db-annullo-documento-con-legami):
    --   i soli documenti VIVI, dalla sede unica vendite.fn_offerta_documenti_vivi,
    --   la stessa del push. Un contratto o un ordine annullato conserva la
    --   provenienza ma non consuma l'offerta.
    SELECT COALESCE(bool_or(d.tipo = 'CONTRATTO'), false),
           COALESCE(bool_or(d.tipo = 'ORDINE_VENDITA'), false)
      INTO v_has_contratto, v_has_ordine
      FROM vendite.fn_offerta_documenti_vivi(p_offerta_id) AS d;

    v_enabled := (v_accettazione
                  AND NOT v_has_contratto
                  AND NOT v_has_ordine);

    -- rev 2026-10-21 (§I.2, H-R2 e I-D2): un'offerta trasformabile propone
    -- le due azioni, SPENTE col motivo se una riga non puo' andare nel
    -- documento da generare. Le righe da ammettere nel contratto sono
    -- quelle dell'offerta (stesse regole, stesso listino congelato):
    -- script.fn_check_righe_documento; nell'ordine, le righe espanse
    -- giudicate da ordine: script.fn_check_righe_offerta_in_ordine, la
    -- stessa che legge vendite.fn_genera_ordine_da_offerta. I guard di riga
    -- restano la rete.
    IF v_enabled THEN
        v_mot_push   := script.fn_check_righe_documento('OFFERTA_COMMERCIALE', p_offerta_id);
        v_mot_ordine := script.fn_check_righe_offerta_in_ordine(p_offerta_id);
    END IF;

    v_can_push := v_enabled AND jsonb_array_length(v_mot_push) = 0;
    IF v_enabled THEN
        v_push_reason     := v_mot_push -> 0 ->> 'reason';
        v_push_reason_key := v_mot_push -> 0 ->> 'reason_key';
        v_actions := v_actions || jsonb_build_array(
            c_action_push_contratto || jsonb_build_object(
                'enabled',    v_can_push,
                'reason',     v_push_reason,
                'reason_key', v_push_reason_key,
                'reasons',    v_mot_push));
    ELSIF v_has_contratto THEN
        v_push_reason     := 'OFFERTA_CONTRATTO_GIA_GENERATO';
        v_push_reason_key := 'vendite.offerte.push_reason.gia_generato';
    ELSIF v_has_ordine THEN
        v_push_reason     := 'OFFERTA_ORDINE_GIA_GENERATO';
        v_push_reason_key := 'vendite.offerte.push_reason.ordine_gia_generato';
    ELSE
        v_push_reason     := 'OFFERTA_NON_ACCETTATA';
        v_push_reason_key := 'vendite.offerte.push_reason.non_accettata';
    END IF;

    v_can_ordine := v_enabled AND jsonb_array_length(v_mot_ordine) = 0;
    IF v_enabled THEN
        v_ordine_reason     := v_mot_ordine -> 0 ->> 'reason';
        v_ordine_reason_key := v_mot_ordine -> 0 ->> 'reason_key';
        v_actions := v_actions || jsonb_build_array(
            c_action_genera_ordine || jsonb_build_object(
                'enabled',    v_can_ordine,
                'reason',     v_ordine_reason,
                'reason_key', v_ordine_reason_key,
                'reasons',    v_mot_ordine));
    ELSIF v_has_ordine THEN
        v_ordine_reason     := 'OFFERTA_ORDINE_GIA_GENERATO';
        v_ordine_reason_key := 'vendite.offerte.push_reason.ordine_gia_generato';
    ELSIF v_has_contratto THEN
        v_ordine_reason     := 'OFFERTA_CONTRATTO_GIA_GENERATO';
        v_ordine_reason_key := 'vendite.offerte.push_reason.gia_generato';
    ELSE
        v_ordine_reason     := 'OFFERTA_NON_ACCETTATA';
        v_ordine_reason_key := 'vendite.offerte.push_reason.non_accettata';
    END IF;

    -- Le eccezioni, le righe dell'offerta: dal montaggio del lock delle
    -- righe, come la fornitura e gli indirizzi. La capability specchia il
    -- trigger, e il trigger legge la bozza dal vocabolario.
    v_can_edit := script.fn_doc_riga_modificabile('vendite.offerte_commerciali_eccezioni'::regclass, v_stato_cod);

    -- La testata nello stato, letta dal montaggio del lock di testata
    -- (rev 2026-10-10): le colonne «sempre» della capability, poi quelle
    -- che il lock blocca in questo stato. Nessuno stato scritto qui.
    v_testata := script.fn_doc_testata_in_stato('vendite.offerte_commerciali'::regclass, v_stato_cod, c_sempre_non_edit);

    RETURN jsonb_build_object(
        'available_actions',             v_actions,
        'can_change_state',              jsonb_array_length(v_actions) > 0,
        'can_edit_testata',  (v_testata ->> 'modificabile')::boolean,
        'can_edit_eccezioni',            v_can_edit,
        -- Dal montaggio del lock dei satelliti (rev 2026-10-11, R-DB-3):
        -- la fornitura e gli indirizzi si scrivono solo in bozza.
        'can_edit_utility',    script.fn_doc_riga_modificabile('vendite.offerte_commerciali_utilities'::regclass, v_stato_cod),
        'can_edit_indirizzi',  script.fn_doc_riga_modificabile('vendite.offerte_commerciali_indirizzi'::regclass, v_stato_cod),
        'can_create_revisione',          v_can_rev,
        'can_push_contratto',            v_can_push,
        'can_push_contratto_reason',     v_push_reason,
        'can_push_contratto_reason_key', v_push_reason_key,
        'can_genera_ordine',             v_can_ordine,
        'can_genera_ordine_reason',      v_ordine_reason,
        'can_genera_ordine_reason_key',  v_ordine_reason_key,
        'non_editable_fields', v_testata -> 'non_modificabili',
        'pdf',                           jsonb_build_object('mode', v_pdf_mode, 'allow_allegati', v_pdf_allow),
        'stato_info_key',                v_stato_info_key,
        'stato_codice',                  v_stato_cod,
        -- Lo stato corrente e' terminale (config.stati_doc_offerte.terminale):
        -- il documento non ha piu' passaggi a mano in uscita.
        'stato_terminale',               v_terminale
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
IS 'Capability dell''offerta commerciale per il dettaglio (NULL se l''offerta non c''e''). available_actions: i passaggi manuali permessi da script.fn_doc_azioni_permesse (matrice viva, manuale; un passaggio con un''azione di processo si nasconde a chi non ce l''ha), ognuno con enabled, reason, reason_key dal primo motivo e reasons, l''array intero; target_state e target_state_descrizione dalla destinazione; label_key, requires_confirm, requires_motivazione, outlined dal meta della transizione. I motivi, sul significato della destinazione: verso lo stato di emissione script.fn_check_listino_congelabile, script.fn_check_prezzi_autorizzati, script.fn_check_indirizzi_documento_cliente e, dallo stato iniziale, script.fn_check_righe_documento; verso lo stato di accettazione i prezzi; verso lo stato di annullo script.fn_check_offerta_annullabile. Sono gli stessi predicati, nello stesso ordine, di vendite.trgfn_offerte_commerciali_guard_transizione. Azioni applicative: crea_revisione dallo stato di emissione, spenta col motivo di script.fn_check_prezzi_in_attesa (can_create_revisione e'' vero solo se la revisione si puo'' creare); push_contratto e genera_ordine dallo stato di accettazione senza documenti vivi nati dall''offerta (vendite.fn_offerta_documenti_vivi), spente coi motivi di script.fn_check_righe_documento e script.fn_check_righe_offerta_in_ordine; can_push_contratto, can_genera_ordine e i loro reason e reason_key. Cosa si modifica: can_edit_testata e non_editable_fields dal montaggio del lock di testata (script.fn_doc_testata_in_stato), can_edit_eccezioni, can_edit_utility e can_edit_indirizzi dal lock delle righe e dei satelliti (script.fn_doc_riga_modificabile), lo stesso che il trigger fa rispettare. pdf {mode, allow_allegati} dal vocabolario. stato_info_key: la nota dello stato dal suo meta (proprieta'' nessuna_azione_key), sempre presente, null quando lo stato non la dichiara. stato_codice: il codice_interno dello stato corrente. stato_terminale: config.stati_doc_offerte.terminale dello stato corrente, perche'' chi mostra il documento non ricopi l''elenco degli stati terminali. Le reason_key sono chiavi i18n del frontend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
