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
--   rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6c): la
--   bozza dalla colonna iniziale del vocabolario, non dal codice;
--   can_edit_righe dal lock delle righe (script.fn_doc_riga_modificabile).
--   COMMENT riscritto al presente.
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
    -- Lo stato corrente e' quello iniziale? Dal vocabolario.
    v_iniziale     config.stati_doc_contratti.iniziale%TYPE;
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
BEGIN
    -- Stato corrente: codice_interno + codice + valido_dal + listino + capability PDF.
    SELECT c.stato_doc_contratto_id, sdc.codice_interno, sdc.codice, c.valido_dal,
           c.listino_id, c.listino_versione_id, sdc.pdf_mode, sdc.pdf_allow_allegati,
           sdc.meta->>'nessuna_azione_key',
           c.billing_account_id, c.istanza_utility_id, c.utility_id, c.ambito, c.valido_al,
           sdc.iniziale
      INTO v_stato_id, v_stato_cod, v_stato_codice, v_valido_dal,
           v_listino_id, v_listino_versione_id, v_pdf_mode, v_pdf_allow, v_stato_info_key,
           v_billing_account_id, v_istanza_utility_id, v_utility_id, v_ambito, v_valido_al,
           v_iniziale
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
                 -- Solo dallo stato iniziale, l'unico da cui si attiva: il
                 -- contesto espande il listino.
                 || CASE WHEN v_iniziale
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
    -- I passaggi manuali che l'utente puo' fare, dal BB comune (rev
    -- 2026-10-27, 20261027-43, §15.14): matrice viva, manuale, permesso.
    FROM script.fn_doc_azioni_permesse('vendite.contratti'::regclass, v_stato_id) t
    JOIN config.stati_doc_contratti sa ON sa.id = t.stato_a_id
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
    WHERE t.meta ? 'action_key'
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
    -- Le righe si modificano dove il lock delle righe le lascia scrivere
    -- (rev 2026-11-14): la stessa risposta del trigger
    -- vendite.trgfn_doc_righe_lock_fuori_bozza.
    v_can_righe := script.fn_doc_riga_modificabile('vendite.contratti_righe'::regclass, v_stato_cod);

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
IS 'Capability del contratto per il dettaglio (NULL se il contratto non c''e''). available_actions: i passaggi manuali permessi da script.fn_doc_azioni_permesse (matrice viva, manuale; un passaggio con un''azione di processo, emetti_contratto sull''attivazione e sulla cessazione, si nasconde a chi non ce l''ha), ognuno con enabled, reason e reason_key dal primo motivo e reasons, l''array intero; target_state e target_state_descrizione dalla destinazione; label_key, requires_confirm, outlined dal meta del passaggio. I motivi verso lo stato di emissione (l''attivazione), nell''ordine del guard: script.fn_check_listino_congelabile, script.fn_check_prezzi_autorizzati, script.fn_check_indirizzi_documento_cliente, dallo stato iniziale script.fn_check_righe_documento, per ultimo script.fn_check_contratto_sovrapposto; poi DOCUMENTO_SENZA_RIGHE dove il meta del passaggio chiede requires_righe e il contratto e'' vuoto (negoziato puro senza un''AGGIUNTA attiva con prezzo). Sono gli stessi predicati di vendite.trgfn_contratti_guard_transizione_stato e vendite.trgfn_contratti_freeze_listino_versione. can_change_state: vero se c''e'' almeno un''azione. Cosa si modifica: can_edit_testata e non_editable_fields dal montaggio del lock di testata (script.fn_doc_testata_in_stato), can_edit_righe, can_edit_utility e can_edit_indirizzi dal lock delle righe e dei satelliti (script.fn_doc_riga_modificabile), lo stesso che i trigger fanno rispettare. pdf {mode, allow_allegati} dal vocabolario. stato_info_key: la nota dello stato dal suo meta (proprieta'' nessuna_azione_key), sempre presente, null quando lo stato non la dichiara. stato_codice_interno e stato_codice: i codici dello stato corrente. Le reason_key sono chiavi i18n del frontend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
