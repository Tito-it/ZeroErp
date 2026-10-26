# ⚙️ Funzione `fn_cambia_stato_ddt`

```sql
CREATE FUNCTION fn_cambia_stato_ddt(p_ddt_id bigint, p_stato character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_ddt(p_ddt_id bigint, p_stato character varying)
 RETURNS TABLE(movimento_id bigint, prelievo_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
-- Scopo: portare una bolla in un nuovo stato e, se il passaggio tocca il
--   registro di una bolla che muove merce, scrivere i movimenti nella
--   stessa transazione. Vedi l'intestazione del changeSet.
-- Ritorna: i movimenti scritti (uscite, entrate o storni); nessuna riga
--   se il passaggio non tocca il registro.
-- rev 2026-10-25 (20261025-16, brief-modello-documento-vendita §7): il
--   permesso dalla riga del passaggio (script.fn_guard_passaggio), lo
--   stato dalla scrittura comune (script.fn_doc_scrivi_stato).
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_ddt          vendite.ddt%ROWTYPE;
    v_da           config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_a_id   config.stati_doc_ddt.id%TYPE;
    v_causale      config.causali_trasporto.causale_magazzino%TYPE;
    v_muove        boolean;
    v_emissione    boolean;
    v_emesso_id    config.stati_doc_ddt.id%TYPE;
    v_annullo      boolean;
    v_consegna_tr  boolean;
    v_sorgente_id  config.sorgenti.id%TYPE;
    v_prelievi     bigint[];
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- Guard di parametro: forme che nessuna interfaccia produce.
    IF p_ddt_id IS NULL OR p_ddt_id <= 0 OR p_stato IS NULL OR btrim(p_stato) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_cambia_stato_ddt',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'bolla maggiore di zero e stato di destinazione obbligatorio',
                               'p_ddt_id', p_ddt_id, 'p_stato', p_stato),
            NULL::uuid, 'vendite.fn_cambia_stato_ddt',
            'p_ddt_id (obbligatorio, maggiore di zero), p_stato (codice dello stato di destinazione)');
    END IF;

    -- La testata, FOR UPDATE, nel perimetro (predicato della policy: DEFINER).
    SELECT d.* INTO v_ddt
      FROM vendite.ddt d
     WHERE d.id = p_ddt_id
       AND script.fn_scope_ef_whitelist_via_ddt(v_utente, d.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_cambia_stato_ddt',
            'E_DDT_NOT_FOUND', jsonb_build_object('ddt_id', p_ddt_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    SELECT s.codice_interno INTO v_da FROM config.stati_doc_ddt s WHERE s.id = v_ddt.stato_doc_ddt_id;
    -- rev 2026-10-25 (20261025-44): codice -> id dal lettore comune.
    -- rev 2026-10-26 (20261026-02): lo stato sconosciuto come i gemelli
    -- (fn_cambia_stato_ordine, fn_cambia_stato_preventivo).
    v_stato_a_id := script.fn_doc_stato_id('vendite.ddt'::regclass, p_stato);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_cambia_stato_ddt',
            'E_STATO_WORKFLOW_NON_TROVATO',
            jsonb_build_object('codice', p_stato),
            NULL::uuid,
            COALESCE(p_stato, 'NULL'));
    END IF;

    -- Il permesso del passaggio, prima di scrivere qualunque cosa: dalla
    -- sua riga della matrice (M-3). Un passaggio di processo chiesto qui
    -- (CONSEGNATO <-> RESO, dei verbi del reso) si ferma qui, e cosi' lo
    -- stato che la bolla ha gia' (rev 2026-10-26, 20261026-01).
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.ddt'::regclass,
                                      v_ddt.stato_doc_ddt_id, v_stato_a_id);

    v_causale     := vendite.fn_ddt_causale_magazzino(v_ddt);
    v_muove       := vendite.fn_ddt_muove_merce(v_ddt);
    -- rev 2026-10-25 (20261025-44): lo stato di emissione dal
    -- vocabolario, non dal letterale (l'emissione si raggiunge solo
    -- dalla bozza: lo dice la matrice).
    v_emesso_id   := script.fn_stato_emissione_id('vendite.ddt'::regclass);
    v_emissione   := v_stato_a_id = v_emesso_id;
    -- rev 2026-10-25 (20261025-78): lo stato d'annullo dal vocabolario.
    v_annullo     := v_ddt.stato_doc_ddt_id = v_emesso_id
                     AND v_stato_a_id = script.fn_stato_abortito_id('vendite.ddt'::regclass);
    v_consegna_tr := p_stato = 'CONSEGNATO' AND v_causale = 'TRASF_OUT' AND v_muove;

    -- Il permesso dell'operazione di magazzino dentro il passaggio: la
    -- consegna di un trasferimento scrive gli arrivi (T-4 di Tid).
    IF v_consegna_tr THEN
        PERFORM script.fn_guard_azione(v_utente, 'registra_magazzino');
    END IF;

    -- All'emissione di una bolla che muove merce: la conferma che parla,
    -- poi i prelievi automatici, finche' la bolla e' in bozza.
    IF v_emissione AND v_muove THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', 'vendite.fn_cambia_stato_ddt',
            script.fn_check_ddt_merce(v_ddt), NULL, NULL::uuid,
            jsonb_build_object('ddt_id', p_ddt_id));

        INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, ddt_riga_componente_id, qta)
        SELECT m.ddt_riga_id, m.ddt_riga_componente_id, m.qta
          FROM vendite.fn_ddt_merce_da_movimentare(v_ddt) m
         WHERE m.prelevata = 0
           AND m.automatico;
    END IF;

    -- Lo stato, dalla scrittura comune: la porta si apre per QUESTA bolla,
    -- e i guard di sempre girano.
    PERFORM script.fn_doc_scrivi_stato('vendite.ddt'::regclass, p_ddt_id, v_stato_a_id);

    -- I movimenti.
    IF v_emissione AND v_muove THEN
        RETURN QUERY
            SELECT pd.movimento_id, pd.prelievo_id, pd.qta
              FROM vendite.fn_posta_ddt(p_ddt_id, 'USCITA') pd;
    ELSIF v_consegna_tr THEN
        RETURN QUERY
            SELECT pd.movimento_id, pd.prelievo_id, pd.qta
              FROM vendite.fn_posta_ddt(p_ddt_id, 'ARRIVO') pd;
    ELSIF v_annullo AND v_muove THEN
        SELECT s.id INTO v_sorgente_id
          FROM config.sorgenti s
         WHERE s.codice_interno = 'DDT_VENDITA_PRELIEVO';
        SELECT COALESCE(array_agg(p.id), '{}'::bigint[]) INTO v_prelievi
          FROM vendite.ddt_righe_prelievi p
          JOIN vendite.ddt_righe dr ON dr.id = p.ddt_riga_id
         WHERE dr.ddt_id = p_ddt_id;
        IF v_sorgente_id IS NOT NULL THEN
            RETURN QUERY
                SELECT st.movimento_id, NULL::bigint, st.qta
                  FROM magazzino.fn_storna_movimenti_sorgente(v_sorgente_id, v_prelievi) st;
        END IF;
    END IF;

    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_ddt(p_ddt_id bigint, p_stato character varying)
IS 'VERBO di ogni cambio di stato manuale di una bolla (modello «una scrittura = un verbo»; modello del documento, brief-modello-documento-vendita §7). Permesso: dalla riga del passaggio (config.transizioni_stati_ddt.azione_processo_codename: emetti_ddt su DRAFT -> EMESSO e EMESSO -> ANNULLATO) con script.fn_guard_passaggio, prima di ogni scrittura; un passaggio di processo (CONSEGNATO <-> RESO, dei verbi del reso) chiesto qui: E_DOC_PASSAGGIO_DI_PROCESSO; gli altri passaggi al permesso sul documento, che controlla il backend. In piu'' registra_magazzino alla consegna di una bolla di trasferimento che muove merce: il permesso dell''operazione di magazzino dentro il passaggio (T-4 di Tid). SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE con il predicato della policy nella WHERE (fuori perimetro E_DDT_NOT_FOUND, no-leak). Lo stato chiesto per codice_interno (script.fn_doc_stato_id: uno stato che il vocabolario non ha o ha spento -> E_STATO_WORKFLOW_NON_TROVATO, come i gemelli), lo stato di emissione dal vocabolario (script.fn_stato_emissione_id). Lo stato lo scrive script.fn_doc_scrivi_stato attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), con la matrice e tutti i guard di sempre. Su una bolla che muove merce: all''emissione solleva il primo motivo di script.fn_check_ddt_merce, crea i prelievi automatici e scrive le uscite (vendite.fn_posta_ddt USCITA); alla consegna di un trasferimento scrive le entrate (ARRIVO); all''annullo di una bolla emessa storna i movimenti dei suoi prelievi (magazzino.fn_storna_movimenti_sorgente). UNA transazione. Ritorna (movimento_id, prelievo_id, qta). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt; il posting in vendite dal 2026-10-01 (brief-db-magazzino-registro-anello-interno); rev 2026-10-25 (20261025-16) il verbo comune; rev 2026-10-25 (20261025-44) i lettori comuni di codice -> id e dello stato di emissione; rev 2026-10-25 (20261025-78, §9, Z-3) l''annullo dell''emessa riconosciuto dallo stato d''annullo del vocabolario (script.fn_stato_abortito_id), non dal letterale ''ANNULLATO''; rev 2026-10-26 (20261026-02, §9.9) lo stato sconosciuto risponde E_STATO_WORKFLOW_NON_TROVATO (era E_VENDITE_CHIAMATA_NON_VALIDA), e lo stato che la bolla ha gia'' lo rifiuta la prima riga (E_DOC_GIA_NELLO_STATO, 20261026-01).';
```

</div>

---
{% include-markdown "signature-core.md" %}
