{% include-markdown "it/dbzero/script/manual/fn_available_actions_contratto.md" %}
# ⚙️ Funzione `fn_available_actions_contratto`

```sql
CREATE FUNCTION fn_available_actions_contratto(p_contratto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_contratto(p_contratto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: capability del contratto per il detail API (pattern data-driven).
--   rev 2026-07-11: + blocco pdf {mode, allow_allegati} da
--   config.stati_doc_contratti (bottone PDF data-driven via capabilities).
--   rev 2026-07-16: + enabled/reason/reason_key da meta.requires_righe
--   (documento vuoto non avanza di stato). "Vuoto" per il contratto:
--   negoziato puro (listino_id NULL) senza AGGIUNTA attiva con prezzo.
--   rev 2026-08-06: + target_state_descrizione, la forma leggibile
--   dello stato di destinazione. Serve alla frase di conferma
--   «portare il documento nello stato X»: il codice_interno non e'
--   quella forma (DRAFT -> Bozza) e tradurlo nel FE sarebbe una
--   seconda copia del vocabolario degli stati.
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
--   rev 2026-09-24: le azioni passano alla forma dell'ARRAY DEI MOTIVI
--   (come preventivo e ordine): enabled/reason/reason_key discendono da
--   `reasons`, che somma i prezzi non autorizzati verso ATTIVO (building
--   block script.fn_check_prezzi_autorizzati, lo stesso del guard di
--   transizione) e il generico «documento vuoto».
--   (brief-db-preventivi-congelamento-pricing, D-4/D-5).
--   rev 2026-10-07: verso ATTIVO, prima dei prezzi, il motivo del listino
--   senza versione in vigore (script.fn_check_listino_congelabile,
--   brief-db-offerta-emissione-ed-erogazione §C.1.2).
--   rev 2026-10-20: verso ATTIVO, dopo gli indirizzi, il contratto
--   vincolante sovrapposto (script.fn_check_contratto_sovrapposto, lo
--   stesso del guard di transizione). Richiesta BE del 2026-10-19.
--   rev 2026-10-21: verso ATTIVO (solo da DRAFT), dopo gli indirizzi e
--   prima del sovrapposto, le righe che la regola intera non ammette
--   (script.fn_check_righe_documento, lo stesso del guard di transizione).
--   brief-db-offerta-emissione-ed-erogazione §I.2, H-R4.
--   rev 2026-10-26 (20261026-11, brief-modello-documento-vendita §11, M-3):
--   un passaggio con un'azione di processo sulla sua riga della matrice
--   (letta da script.fn_doc_passaggio: emetti_contratto sull'attivazione e
--   sulla cessazione) si NASCONDE a chi non ha l'azione: permesso =>
--   nascondi, stato => disabilita col motivo. I motivi dell'attivazione si
--   legano allo stato che il vocabolario dichiara d'emissione, non al
--   letterale 'ATTIVO'.
DECLARE
    -- Tipi nudi solo per valori CALCOLATI (azioni e motivi jsonb, flag,
    -- motivi e chiavi i18n composti): nessuna colonna di cui siano il riflesso.
    v_stato_id     vendite.contratti.stato_doc_contratto_id%TYPE;
    v_stato_cod    config.stati_doc_contratti.codice_interno%TYPE;
    v_stato_info_key text;
    v_stato_codice config.stati_doc_contratti.codice%TYPE;
    v_valido_dal   vendite.contratti.valido_dal%TYPE;
    v_listino_id   vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    -- La quintupla dell'EXCLUDE, per il motivo della sovrapposizione.
    v_billing_account_id vendite.contratti.billing_account_id%TYPE;
    v_istanza_utility_id vendite.contratti.istanza_utility_id%TYPE;
    v_utility_id         vendite.contratti.utility_id%TYPE;
    v_ambito             vendite.contratti.ambito%TYPE;
    v_valido_al          vendite.contratti.valido_al%TYPE;
    v_mot_attiva   jsonb := '[]'::jsonb;
    v_pdf_mode     config.stati_doc_contratti.pdf_mode%TYPE;
    v_pdf_allow    config.stati_doc_contratti.pdf_allow_allegati%TYPE;
    v_actions      jsonb;
    v_ha_righe     boolean := false;
    v_can_edit     boolean;
    v_can_righe    boolean;
    -- La testata nello stato, dal montaggio del lock (rev 2026-10-10):
    -- {modificabile, non_modificabili}.
    v_testata jsonb;
    -- L'utente della sessione, per l'azione del passaggio (rev 2026-10-26).
    v_utente  config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- Stato corrente: codice_interno + codice + valido_dal + listino + capability PDF.
    SELECT c.stato_doc_contratto_id, sdc.codice_interno, sdc.codice, c.valido_dal,
           c.listino_id, c.listino_versione_id, sdc.pdf_mode, sdc.pdf_allow_allegati,
           sdc.meta->>'nessuna_azione_key',
           c.billing_account_id, c.istanza_utility_id, c.utility_id, c.ambito, c.valido_al
      INTO v_stato_id, v_stato_cod, v_stato_codice, v_valido_dal,
           v_listino_id, v_listino_versione_id, v_pdf_mode, v_pdf_allow, v_stato_info_key,
           v_billing_account_id, v_istanza_utility_id, v_utility_id, v_ambito, v_valido_al
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti sdc ON sdc.id = c.stato_doc_contratto_id
     WHERE c.id = p_contratto_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Precondizione "documento non vuoto" per le transizioni che la
    -- esigono (meta.requires_righe). Per il contratto NON e' un
    -- semplice conteggio: con listino non e' mai vuoto di sostanza
    -- (le righe arrivano dal listino); negoziato puro (listino_id
    -- NULL) e' vuoto senza almeno una AGGIUNTA attiva con prezzo.
    -- Specchia trgfn_contratti_freeze_listino_versione
    -- (E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE).
    v_ha_righe := (v_listino_id IS NOT NULL)
        OR EXISTS (
            SELECT 1
              FROM vendite.contratti_righe cr
             WHERE cr.contratto_id = p_contratto_id
               AND cr.tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
               AND cr.prezzo_unitario IS NOT NULL
               AND cr.attivo = TRUE
        );

    -- Motivi ostativi all'ATTIVAZIONE: i prezzi non autorizzati. E' il
    -- building block che trgfn_contratti_guard_transizione_stato usa per
    -- sollevare, quindi «Attiva» e guard non possono divergere.
    -- rev 2026-09-24, brief-db-preventivi-congelamento-pricing (D-4).
    -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2,
    -- decisione A-D2 di Tid): PRIMA il listino. Senza una versione in vigore
    -- il contratto con listino non si attiva: lo stesso predicato,
    -- script.fn_check_listino_congelabile, con cui
    -- trgfn_contratti_freeze_listino_versione solleva e poi congela.
    v_mot_attiva := script.fn_check_listino_congelabile('CONTRATTO', v_listino_id, v_listino_versione_id)
                 || script.fn_check_prezzi_autorizzati('vendite.contratti'::regclass,
                                                       p_contratto_id)
                 -- rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente,
                 -- D-3): poi gli indirizzi che non sono del cliente, lo stesso
                 -- building block e lo stesso ordine del guard verso ATTIVO.
                 || script.fn_check_indirizzi_documento_cliente('CONTRATTO', p_contratto_id)
                 -- rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione
                 -- §I.2, H-R4): poi le righe che la regola intera non ammette
                 -- piu', lo stesso building block e lo stesso ordine del guard.
                 -- Solo da DRAFT, l'unico stato da cui si attiva: il contesto
                 -- espande il listino.
                 || CASE WHEN v_stato_cod = 'DRAFT'
                         THEN script.fn_check_righe_documento('CONTRATTO', p_contratto_id)
                         ELSE '[]'::jsonb END
                 -- rev 2026-10-20 (richiesta BE del 2026-10-19): per ultimo il
                 -- contratto vincolante sovrapposto. Prima i motivi che si
                 -- correggono su QUESTO contratto, poi il conflitto con un altro
                 -- documento. Lo stesso building block e lo stesso ordine del
                 -- guard di transizione: prima «Attiva» restava acceso e il
                 -- rifiuto arrivava solo dall'EXCLUDE, alla conferma.
                 || script.fn_check_contratto_sovrapposto(
                        v_billing_account_id, v_istanza_utility_id, v_utility_id,
                        v_ambito, v_valido_dal, v_valido_al);

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',             t.meta->>'action_key',
                'target_state',    sa.codice_interno,
                -- Forma leggibile della destinazione: la colonna
                -- accanto, nello stesso JOIN. Il FE non puo'
                -- derivarla dal codice.
                'target_state_descrizione', sa.descrizione,
                'label_key',       t.meta->>'label_key',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'requires_date',   COALESCE((t.meta->>'requires_date')::boolean, false),
                'outlined',        COALESCE((t.meta->>'outlined')::boolean, false),
                -- Tutto discende dall'array dei motivi: nessuna
                -- regola puo' mascherarne un'altra (rev 2026-09-24).
                'enabled',         jsonb_array_length(m.motivi) = 0,
                'reason',          m.motivi -> 0 ->> 'reason',
                'reason_key',      m.motivi -> 0 ->> 'reason_key',
                'reasons',         m.motivi
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.transizioni_stati_contratti t
    JOIN config.stati_doc_contratti sa ON sa.id = t.stato_a_id
    -- L'azione del passaggio dal lettore unico (rev 2026-10-26, M-3).
    CROSS JOIN LATERAL script.fn_doc_passaggio('vendite.contratti'::regclass, t.stato_da_id, t.stato_a_id) pz
    -- I motivi della destinazione, sommati in un array solo. Ordine:
    -- prima quelli specifici della destinazione, poi il generico
    -- «documento vuoto»; il primo e' quello che il FE mostra da solo.
    -- ⚠️ Il motivo «documento vuoto» e' lo stesso di prima, scritto nella
    --   forma di un motivo: stessi reason e reason_key.
    CROSS JOIN LATERAL (
        -- rev 2026-10-26 (20261026-11): l'attivazione la dice il vocabolario
        -- (emissione), non il codice.
        SELECT CASE WHEN sa.emissione
                    THEN v_mot_attiva ELSE '[]'::jsonb END
            || CASE WHEN COALESCE((t.meta->>'requires_righe')::boolean, false)
                         AND NOT v_ha_righe
                    THEN jsonb_build_array(jsonb_build_object(
                             'codice',     NULL,
                             'reason',     'DOCUMENTO_SENZA_RIGHE',
                             'reason_key', 'common.azione_reason.senza_righe',
                             'dettaglio',  NULL))
                    ELSE '[]'::jsonb END AS motivi
    ) m
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      -- Permesso => nascondi: chi non ha l'azione del passaggio non vede il bottone.
      AND (pz.azione_processo_codename IS NULL
           OR script.fn_check_azione_processo(v_utente, pz.azione_processo_codename))
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    -- Arricchimento delle sole azioni con data: somma chiavi,
    -- non tocca quelle gia' presenti.
    IF jsonb_array_length(v_actions) > 0 THEN
        SELECT jsonb_agg(
            CASE WHEN (elem->>'requires_date')::boolean IS TRUE
                 THEN elem || jsonb_build_object(
                          'default_date', (SELECT script.fn_data_operativa())::text,
                          'min_date',     v_valido_dal::text
                      )
                 ELSE elem
            END
        )
        INTO v_actions
        FROM jsonb_array_elements(v_actions) AS elem;
    END IF;

    -- La testata nello stato, letta dal montaggio del lock di testata
    -- (rev 2026-10-10): le colonne «sempre» della capability, poi quelle
    -- che il lock blocca in questo stato. Nessuno stato scritto qui.
    v_testata := script.fn_doc_testata_in_stato('vendite.contratti'::regclass, v_stato_cod, '[]'::jsonb);

    v_can_edit  := (v_testata ->> 'modificabile')::boolean;
    v_can_righe := (v_stato_cod = 'DRAFT');

    RETURN jsonb_build_object(
        'available_actions',   v_actions,
        'can_change_state',    jsonb_array_length(v_actions) > 0,
        'can_edit_testata',    v_can_edit,
        'can_edit_righe',      v_can_righe,
        -- Dal montaggio del lock dei satelliti (rev 2026-10-11, R-DB-3):
        -- la fornitura e gli indirizzi si scrivono solo in bozza.
        'can_edit_utility',    script.fn_doc_riga_modificabile('vendite.contratti_utilities'::regclass, v_stato_cod),
        'can_edit_indirizzi',  script.fn_doc_riga_modificabile('vendite.contratti_indirizzi'::regclass, v_stato_cod),
        'non_editable_fields', v_testata -> 'non_modificabili',
        'pdf',                 jsonb_build_object('mode', v_pdf_mode, 'allow_allegati', v_pdf_allow),
        'stato_codice_interno', v_stato_cod,
        'stato_info_key',       v_stato_info_key,
        'stato_codice',         v_stato_codice
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_contratto(p_contratto_id bigint)
IS 'Capability contratto per detail API: available_actions + can_change_state + can_edit_testata/righe + non_editable_fields + stato_codice_interno + stato_codice. rev 2026-07-11: + blocco pdf {mode, allow_allegati} da config.stati_doc_contratti. rev 2026-07-16: ogni azione espone enabled/reason/reason_key; se la transizione ha meta.requires_righe e il contratto e'' vuoto -> enabled=false + reason DOCUMENTO_SENZA_RIGHE. Vuoto per il contratto = negoziato puro (listino_id NULL) senza AGGIUNTA attiva con prezzo; con listino mai vuoto (predicato specchiato da trgfn_contratti_freeze_listino_versione). rev 2026-08-06: + target_state_descrizione accanto a target_state (config.stati_doc_contratti.descrizione della destinazione). Serve alla frase di conferma «portare il documento nello stato X»: il codice_interno non e'' la forma leggibile (DRAFT -> Bozza) e derivarla nel FE sarebbe una seconda copia del vocabolario degli stati. L''arricchimento requires_date a valle somma chiavi e non la tocca. rev 2026-08-11: + stato_info_key, la nota di stato letta dal meta dello stato corrente ed emessa SEMPRE che lo stato la dichiari, anche accanto a un''azione ancora abilitata: la nota spiega lo STATO e non risponde a una barra vuota (decisione §5 di Tid, gia'' applicata a preventivo/ordine/DDT con 20260810-04/-05/-06). Questo dominio era fra i cinque che non emettevano affatto il campo mentre il drawer lo legge gia'': il cablaggio c''era ed era inerte. ⚠️ La PROPRIETA'' nel meta resta nessuna_azione_key mentre il campo del blob si chiama stato_info_key: scripts/check_i18n_keys.py trova le chiavi seminate per quel nome, e rinominarla senza toccare il guard lo renderebbe verde per cecita''. ⚠️ Il campo e'' SEMPRE presente nel blob, col valore a null quando non si applica: filtrare per presenza risponde vero per tutti i documenti, va guardato il valore. brief-db-vie-uscita-operatore §12.6; attivita-urgenti-del-10-08 §3. rev 2026-09-24: le azioni passano alla forma dell''''ARRAY DEI MOTIVI, come preventivo e ordine — enabled/reason/reason_key discendono da `reasons` (chiave nuova nel blob). Verso ATTIVO l''''array somma i prezzi non autorizzati (PENDING o REJECTED su righe e componenti BoM attivi) da script.fn_check_prezzi_autorizzati, lo stesso building block con cui trgfn_contratti_guard_transizione_stato solleva; poi il generico DOCUMENTO_SENZA_RIGHE, invariato. ⚠️ La reason_key common.azione_reason.prezzo_pendente / prezzo_rifiutato e'''' un debito verso il frontend. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-4, D-5). rev 2026-09-27 (20260927-17): le azioni non portano piu'' la chiave icon. Il DB manda il SIGNIFICATO (key), il frontend sceglie il segno dal key con una mappa verbo -> icona in core/ (decisione D-1 di Tid, opzione A): un segno scritto qui era l''unico dell''app che non passava dalle costanti del frontend, e lo stesso verbo ne portava due. Brief: brief-db-icone-azioni-per-significato (D-1). rev 2026-09-28 (20260928-14): le azioni non portano piu'' la chiave severity. Come l''icona, il colore del pulsante lo decide il VERBO, uguale in tutti i domini, e il frontend lo ricava dal key (mappa verbo -> aspetto in core/, decisione di Tid): lo stesso verbo portava colori diversi fra i domini. label_key e outlined restano dati. Brief: brief-db-icone-azioni-per-significato (§9). rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, decisione A-D2 di Tid): verso ATTIVO l''array dei motivi comincia dal listino — script.fn_check_listino_congelabile(''CONTRATTO'', listino, versione), lo stesso predicato di trgfn_contratti_freeze_listino_versione: un contratto con listino senza versione in vigore oggi non si attiva (reason LISTINO_SENZA_VERSIONE_IN_VIGORE, reason_key nuova vendite.contratti.azione_reason.listino_senza_versione_in_vigore, debito verso il frontend). Poi i prezzi non autorizzati e il documento vuoto, invariati. rev 2026-10-10 (brief-db-testata-dopo-emissione fase 2): non_editable_fields e can_edit_testata si leggono dal montaggio del lock di testata con script.fn_doc_testata_in_stato: le colonne «sempre» della capability seguite da quelle che il lock blocca nello stato, e can_edit_testata vero se nello stato almeno una colonna nominata si cambia. Ritirate le liste scritte a mano dei campi bloccati fuori bozza (la terza copia della regola, accanto a lock e backend): con D-8/D-10 le colonne aperte dopo l''emissione (note, trasporto, valido_al e CIG/CUP del contratto…) si cambiano negli stati del montaggio e si fermano a documento chiuso. rev 2026-10-11 (brief-db-testata-dopo-emissione §11, R-DB-3): + can_edit_utility e can_edit_indirizzi, dal montaggio dei lock di vendite.contratti_utilities e vendite.contratti_indirizzi (script.fn_doc_riga_modificabile): fornitura e indirizzi si scrivono solo in bozza, e il backend non lo scrive piu'' (_assert_contratto_draft, _INDIRIZZI_CFG) rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-3 di Tid): verso ATTIVO, dopo listino e prezzi, il motivo di script.fn_check_indirizzi_documento_cliente(''CONTRATTO'', id) — E_INDIRIZZO_DOC_NON_DEL_CLIENTE, reason INDIRIZZO_NON_DEL_CLIENTE, reason_key common.azione_reason.indirizzo_non_del_cliente (debito verso il frontend) — lo stesso che trgfn_contratti_guard_transizione_stato solleva. Firma ancorata: p_contratto_id vendite.contratti.id%TYPE (stesso tipo, stessa identita''). rev 2026-10-20 (richiesta BE del 2026-10-19): verso ATTIVO, dopo gli indirizzi, il motivo di script.fn_check_contratto_sovrapposto(quintupla salvata) — E_CONTRATTO_OVERLAP_ESISTENTE, reason CONTRATTO_SOVRAPPOSTO, reason_key vendite.contratti.azione_reason.contratto_sovrapposto (debito verso il frontend), valori [numero del contratto in conflitto] — lo stesso che trgfn_contratti_guard_transizione_stato solleva. Prima «Attiva» restava acceso su una bozza sovrapposta a un contratto vincolante e il rifiuto arrivava dall''EXCLUDE ex_contratti_no_overlap, alla conferma. rev 2026-10-21 (20261021-60, brief-db-offerta-emissione-ed-erogazione §I.2, H-R4): verso ATTIVO (solo da DRAFT), dopo gli indirizzi e prima del sovrapposto, i motivi di script.fn_check_righe_documento(''CONTRATTO'', id) — E_DOC_RIGA_NON_AMMESSA, reason RIGA_NON_AMMESSA, reason_key common.azione_reason.riga_non_ammessa (debito verso il frontend), una riga che la regola intera non ammette piu'' — gli stessi che trgfn_contratti_guard_transizione_stato solleva. ⭐ rev 2026-10-26 (20261026-11, brief-modello-documento-vendita §11, M-3): un passaggio con un''azione di processo sulla sua riga della matrice (letta da script.fn_doc_passaggio: emetti_contratto sull''attivazione e sulla cessazione) si NASCONDE a chi non ha l''azione (script.fn_check_azione_processo, utente da app.current_user_id): permesso => nascondi, stato => disabilita col motivo. I motivi dell''attivazione si legano allo stato che il vocabolario dichiara d''emissione, non al letterale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
