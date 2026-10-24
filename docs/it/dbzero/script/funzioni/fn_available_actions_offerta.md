{% include-markdown "it/dbzero/script/manual/fn_available_actions_offerta.md" %}
# ⚙️ Funzione `fn_available_actions_offerta`

```sql
CREATE FUNCTION fn_available_actions_offerta(p_offerta_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$


-- Scopo: capability offerta commerciale per detail API (data-driven,
--   specchio di fn_available_actions_preventivo). push_contratto e
--   genera_ordine mutuamente esclusive (ACCETTATA).
--   rev 2026-07-11: + blocco pdf {mode, allow_allegati} da
--   config.stati_doc_offerte (bottone PDF data-driven via capabilities).
--   rev 2026-07-19: + enabled/reason/reason_key su ogni azione
--   (uniformita' 6 domini): verso EMESSA disabled se la versione
--   listino manca o non e' ATTIVA — specchio del guard
--   BOZZA->EMESSA (brief-db-guard-righe-avanzamento-stato §1a).
--   rev 2026-07-19 (bis): le 3 push_reason passano al namespace
--   i18n vendite.offerte.* (era offerte.*, radice inesistente nei
--   locales FE) — brief-db-i18n-reason-mancanti-offerte-preventivi.
--   rev 2026-08-06: + outlined dal meta della transizione (era
--   l'unica insieme al preventivo a non emetterlo: il dato del
--   seed non arrivava al pulsante) e + target_state_descrizione,
--   la forma leggibile dello stato di destinazione, che il
--   codice_interno non permette di derivare (BOZZA -> Bozza vale
--   per caso, ALLOCATO -> «Allocato a magazzino» no). NULL sulle
--   azioni che non cambiano stato.
--   rev 2026-08-11: + stato_info_key, la nota che spiega cosa sta
--   succedendo quando il documento e' in uno stato chiuso. Arriva dal
--   `meta` dello stato, e viene emessa SEMPRE che lo stato la dichiari —
--   anche accanto a un'azione ancora abilitata: la nota spiega lo STATO,
--   non risponde a una barra vuota (decisione §5 di Tid, gia' applicata a
--   preventivo/ordine/DDT con 20260810-04/-05/-06). Questo dominio era
--   fra i cinque che non emettevano affatto il campo, mentre il drawer lo
--   legge gia': il cablaggio c'era ed era inerte.
--   ⚠️ La PROPRIETA' nel meta si chiama `nessuna_azione_key` mentre il
--   campo del blob si chiama `stato_info_key`. L'asimmetria e' voluta:
--   scripts/check_i18n_keys.py trova le chiavi seminate per QUEL nome
--   (RE_SEED_KEY sui CSV, elenco _PROP_KEY), e rinominarla senza toccare
--   il guard lo renderebbe verde per cecita'.
--   ⚠️ Il campo e' SEMPRE presente nel blob, col valore a null quando non
--   si applica: filtrare per presenza risponde vero per tutti i documenti,
--   va guardato il valore.
--   brief-db-vie-uscita-operatore §12.6; attivita-urgenti-del-10-08 §3.
--   rev 2026-09-24: le azioni di stato passano alla forma dell'ARRAY DEI
--   MOTIVI (come preventivo e ordine): verso EMESSA il motivo del listino
--   e poi i prezzi non autorizzati, verso ACCETTATA i prezzi — dal
--   building block script.fn_check_prezzi_autorizzati, lo stesso del
--   guard di transizione (brief-db-preventivi-congelamento-pricing, D-4).
--   rev 2026-09-24 (2): «Crea revisione» spento col motivo se c'e' un
--   prezzo IN ATTESA (script.fn_check_prezzi_in_attesa, stessa funzione
--   della madre fn_crea_revisione_offerta); can_create_revisione
--   veritiero. Brief §10.
--   rev 2026-10-07: il motivo del listino verso EMESSA viene da
--   script.fn_check_listino_congelabile sulla versione che verrebbe
--   congelata (brief-db-offerta-emissione-ed-erogazione §C.1.3).
--   rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.2, §H.3):
--   verso EMESSA, per ultime, le righe che la regola intera non ammette
--   (script.fn_check_righe_documento, lo stesso del guard); «Genera
--   contratto» e «Genera ordine» da ACCETTATA restano PROPOSTE e si
--   spengono col motivo delle righe (script.fn_check_righe_documento e
--   script.fn_check_righe_offerta_in_ordine, gli stessi del push e del
--   verbo); verso ANNULLATA il motivo di script.fn_check_offerta_annullabile.
DECLARE
    -- Tipi nudi solo per valori CALCOLATI (azioni e motivi jsonb, flag,
    -- motivi e chiavi i18n composti): nessuna colonna di cui siano il riflesso.
    v_stato_id    vendite.offerte_commerciali.stato_doc_offerta_id%TYPE;
    v_stato_cod   config.stati_doc_offerte.codice_interno%TYPE;
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
           sdo.pdf_mode, sdo.pdf_allow_allegati,
           o.listino_id, o.listino_versione_id,
           sdo.meta->>'nessuna_azione_key'
      INTO v_stato_id, v_stato_cod, v_pdf_mode, v_pdf_allow,
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
    -- building block e lo stesso ordine del guard BOZZA->EMESSA. Solo in
    -- BOZZA, l'unico stato da cui si emette: il contesto espande il listino.
    IF v_stato_cod = 'BOZZA' THEN
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
    FROM config.stati_doc_offerte_transizioni t
    JOIN config.stati_doc_offerte sa ON sa.id = t.stato_a_id
    CROSS JOIN LATERAL (
        SELECT CASE WHEN sa.codice_interno = 'EMESSA'
                    THEN v_mot_emetti ELSE '[]'::jsonb END
            || CASE WHEN sa.codice_interno = 'ACCETTATA'
                    THEN v_mot_prezzi ELSE '[]'::jsonb END
            || CASE WHEN sa.codice_interno = 'ANNULLATA'
                    THEN v_mot_annulla ELSE '[]'::jsonb END AS motivi
    ) m
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    v_can_rev := (v_stato_cod = 'EMESSA');
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

    v_enabled := (v_stato_cod = 'ACCETTATA'
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

    v_can_edit := (v_stato_cod = 'BOZZA');

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
        'stato_codice',                  v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
IS 'Capability offerta commerciale per detail API: available_actions + can_edit_* + push_contratto/genera_ordine (mutuamente esclusive) + create_revisione + non_editable_fields. rev 2026-07-11: + blocco pdf {mode, allow_allegati}. rev 2026-07-19: + enabled/reason/reason_key su ogni azione (uniformita'' 6 domini, brief-db-guard-righe-avanzamento-stato §1a) — la transizione verso EMESSA e'' disabled con reason LISTINO_VERSIONE_MANCANTE / LISTINO_VERSIONE_NON_ATTIVA, specchio del guard BOZZA->EMESSA (per le offerte il "vuoto" e'' la versione listino, non le righe: sono espanse dal listino). rev 2026-07-19 (bis): le 3 push_reason (gia_generato / ordine_gia_generato / non_accettata, usate sia da can_push_contratto_reason_key sia da can_genera_ordine_reason_key) passano al namespace i18n vendite.offerte.* — erano sotto offerte.*, radice inesistente nei locales, quindi il motivo non compariva mai in interfaccia; brief-db-i18n-reason-mancanti-offerte-preventivi. rev 2026-08-06: ogni azione espone outlined (dal meta della transizione, COALESCE a false) e target_state_descrizione (config.stati_doc_offerte.descrizione della destinazione). outlined mancava qui e sul preventivo: il seed lo portava ma la funzione non lo emetteva, quindi il pulsante distruttivo restava rosso pieno mentre negli altri sei domini era outlined. target_state_descrizione serve alla frase di conferma «portare il documento nello stato X»: il codice_interno non e'' la forma leggibile e derivarla nel FE sarebbe una seconda copia del vocabolario degli stati; NULL sulle azioni applicative (crea_revisione / push_contratto / genera_ordine), che non cambiano stato. rev 2026-08-11: + stato_info_key, la nota di stato letta dal meta dello stato corrente ed emessa SEMPRE che lo stato la dichiari, anche accanto a un''azione ancora abilitata: la nota spiega lo STATO e non risponde a una barra vuota (decisione §5 di Tid, gia'' applicata a preventivo/ordine/DDT con 20260810-04/-05/-06). Questo dominio era fra i cinque che non emettevano affatto il campo mentre il drawer lo legge gia'': il cablaggio c''era ed era inerte. ⚠️ La PROPRIETA'' nel meta resta nessuna_azione_key mentre il campo del blob si chiama stato_info_key: scripts/check_i18n_keys.py trova le chiavi seminate per quel nome, e rinominarla senza toccare il guard lo renderebbe verde per cecita''. ⚠️ Il campo e'' SEMPRE presente nel blob, col valore a null quando non si applica: filtrare per presenza risponde vero per tutti i documenti, va guardato il valore. brief-db-vie-uscita-operatore §12.6; attivita-urgenti-del-10-08 §3. rev 2026-09-24: le azioni di stato passano alla forma dell''''ARRAY DEI MOTIVI — enabled/reason/reason_key discendono da `reasons` (chiave nuova). Verso EMESSA: il motivo del listino (LISTINO_VERSIONE_MANCANTE / _NON_ATTIVA, invariato) e poi i prezzi non autorizzati; verso ACCETTATA: i prezzi. I prezzi (PENDING o REJECTED su eccezioni e loro componenti BoM attivi) vengono da script.fn_check_prezzi_autorizzati, lo stesso building block con cui trgfn_offerte_commerciali_guard_transizione solleva. ⚠️ Le reason_key common.azione_reason.prezzo_pendente / prezzo_rifiutato sono un debito verso il frontend. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-4, D-5). rev 2026-09-24 (2, 20260924-37): «Crea revisione» resta proposto su EMESSA ma SPENTO col motivo (enabled/reason/reason_key/reasons) se l''''offerta ha un prezzo IN ATTESA — script.fn_check_prezzi_in_attesa, la stessa funzione con cui vendite.fn_crea_revisione_offerta rifiuta. can_create_revisione diventa veritiero. Brief: brief-db-preventivi-congelamento-pricing §10. rev 2026-09-27 (20260927-11): le azioni non portano piu'' la chiave icon. Il DB manda il SIGNIFICATO (key), il frontend sceglie il segno dal key con una mappa verbo -> icona in core/ (decisione D-1 di Tid, opzione A): un segno scritto qui era l''unico dell''app che non passava dalle costanti del frontend, e lo stesso verbo ne portava due. Brief: brief-db-icone-azioni-per-significato (D-1). rev 2026-09-28 (20260928-08): le azioni non portano piu'' la chiave severity. Come l''icona, il colore del pulsante lo decide il VERBO, uguale in tutti i domini, e il frontend lo ricava dal key (mappa verbo -> aspetto in core/, decisione di Tid): lo stesso verbo portava colori diversi fra i domini. label_key e outlined restano dati. Brief: brief-db-icone-azioni-per-significato (§9). rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.3): il motivo del listino verso EMESSA viene da script.fn_check_listino_congelabile(''OFFERTA'', listino, versione), lo stesso predicato del guard BOZZA->EMESSA, e giudica la versione che verrebbe congelata (la fissata, altrimenti quella in vigore oggi) invece della colonna nuda. Un''offerta in bozza su un listino con una versione in vigore ha «Emetti» acceso. Motivi: LISTINO_SENZA_VERSIONE_IN_VIGORE (reason_key nuova vendite.offerte.azione_reason.listino_senza_versione_in_vigore, debito verso il frontend) e LISTINO_VERSIONE_NON_ATTIVA (invariata). LISTINO_VERSIONE_MANCANTE non si emette più. I motivi del listino portano ora il codice che il guard solleva. rev 2026-10-10 (brief-db-testata-dopo-emissione fase 2): non_editable_fields e can_edit_testata si leggono dal montaggio del lock di testata con script.fn_doc_testata_in_stato: le colonne «sempre» della capability seguite da quelle che il lock blocca nello stato, e can_edit_testata vero se nello stato almeno una colonna nominata si cambia. Ritirate le liste scritte a mano dei campi bloccati fuori bozza (la terza copia della regola, accanto a lock e backend): con D-8/D-10 le colonne aperte dopo l''emissione (note, trasporto, valido_al e CIG/CUP del contratto…) si cambiano negli stati del montaggio e si fermano a documento chiuso. rev 2026-10-11 (brief-db-testata-dopo-emissione §11, R-DB-2 e R-DB-3): motivazione_rifiuto esce dalle colonne ferme in ogni stato — la governa il montaggio del lock di testata, aperta in EMESSA e ACCETTATA (D-10). can_edit_utility non e'' piu'' lo stato BOZZA scritto qui: si legge dal montaggio del lock di vendite.offerte_commerciali_utilities (script.fn_doc_riga_modificabile); + can_edit_indirizzi dal montaggio del lock di vendite.offerte_commerciali_indirizzi rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-3 di Tid): verso EMESSA, dopo listino e prezzi, il motivo di script.fn_check_indirizzi_documento_cliente(''OFFERTA'', id) — E_INDIRIZZO_DOC_NON_DEL_CLIENTE, reason INDIRIZZO_NON_DEL_CLIENTE, reason_key common.azione_reason.indirizzo_non_del_cliente (debito verso il frontend) — lo stesso che il guard BOZZA->EMESSA solleva. Firma ancorata: p_offerta_id vendite.offerte_commerciali.id%TYPE (stesso tipo, stessa identita''). rev 2026-10-11 (20261011-75, brief-db-annullo-documento-con-legami D-3/D-6): can_push_contratto e can_genera_ordine guardano i soli documenti VIVI nati dall''offerta, da vendite.fn_offerta_documenti_vivi (la sede che legge anche il push): un contratto o un ordine annullato non consuma piu'' l''offerta. ⭐ rev 2026-10-19 (20261019-27, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. ⚠️ fn_check_indirizzi_documento_cliente riceve ancora OFFERTA: e'' la grammatica delle testate, la migra il lotto 2. ⭐ rev 2026-10-19 (20261019-54, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. Rev 2026-10-21 (20261021-58, brief-db-offerta-emissione-ed-erogazione §I.2, §H.3): verso EMESSA (solo da BOZZA), per ultime, le righe che la regola intera non ammette (script.fn_check_righe_documento: E_DOC_RIGA_NON_AMMESSA, reason RIGA_NON_AMMESSA, reason_key common.azione_reason.riga_non_ammessa, debito verso il frontend), lo stesso del guard BOZZA->EMESSA (H-R1). Da ACCETTATA senza documenti vivi push_contratto e genera_ordine sono PROPOSTE con enabled/reason/reason_key/reasons: spente se una riga non puo'' andare nel documento da generare (script.fn_check_righe_documento per il contratto, script.fn_check_righe_offerta_in_ordine per l''ordine, la stessa del verbo vendite.fn_genera_ordine_da_offerta); can_push_contratto e can_genera_ordine seguono, con reason e reason_key del primo motivo (H-R2, I-D2). Verso ANNULLATA (da BOZZA e, nuova, da ACCETTATA) il motivo di script.fn_check_offerta_annullabile: E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI, reason DOCUMENTI_VIVI, reason_key vendite.offerte.azione_reason.documenti_vivi, debito verso il frontend (H-R3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
