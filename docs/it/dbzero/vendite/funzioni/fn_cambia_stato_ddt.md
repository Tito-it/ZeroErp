# ⚙️ Funzione `fn_cambia_stato_ddt`

```sql
CREATE FUNCTION fn_cambia_stato_ddt(p_ddt_id bigint, p_stato character varying)
```

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
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_ddt          vendite.ddt%ROWTYPE;
    v_da           config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_a_id   config.stati_doc_ddt.id%TYPE;
    v_causale      config.causali_trasporto.causale_magazzino%TYPE;
    v_muove        boolean;
    v_emissione    boolean;
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
    SELECT s.id INTO v_stato_a_id FROM config.stati_doc_ddt s WHERE s.codice_interno = p_stato AND s.attivo;
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_cambia_stato_ddt',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'stato di destinazione inesistente o spento', 'p_stato', p_stato),
            NULL::uuid, 'vendite.fn_cambia_stato_ddt',
            'p_stato (codice_interno di config.stati_doc_ddt, attivo)');
    END IF;

    v_causale     := vendite.fn_ddt_causale_magazzino(v_ddt);
    v_muove       := vendite.fn_ddt_muove_merce(v_ddt);
    v_emissione   := v_da = 'DRAFT'  AND p_stato = 'EMESSO';
    v_annullo     := v_da = 'EMESSO' AND p_stato = 'ANNULLATO';
    v_consegna_tr := p_stato = 'CONSEGNATO' AND v_causale = 'TRASF_OUT' AND v_muove;

    -- Il permesso, prima di scrivere qualunque cosa (D-2).
    IF p_stato = 'EMESSO' OR v_annullo THEN
        PERFORM script.fn_guard_azione(v_utente, 'emetti_ddt');
    END IF;
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

    -- Lo stato: la porta si apre per QUESTA bolla, e i guard di sempre girano.
    PERFORM set_config('zeroerp.ddt_cambio_stato', p_ddt_id::text, true);
    UPDATE vendite.ddt d
       SET stato_doc_ddt_id = v_stato_a_id
     WHERE d.id = p_ddt_id;

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

    PERFORM set_config('zeroerp.ddt_cambio_stato', '', true);
    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_ddt(p_ddt_id bigint, p_stato character varying)
IS 'VERBO di ogni cambio di stato di una bolla (D-L3-e; modello «una scrittura = un verbo»). Permesso: emetti_ddt per -> EMESSO e per EMESSO -> ANNULLATO, registra_magazzino per la consegna di una bolla di trasferimento che muove merce (script.fn_guard_azione, E_PERMESSO_NEGATO); gli altri passaggi restano al permesso del backend. SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE con il predicato della policy nella WHERE (fuori perimetro E_DDT_NOT_FOUND, no-leak). Fa l''UPDATE dello stato — la matrice e tutti i guard di sempre — aprendo la porta del registro con la GUC transazionale zeroerp.ddt_cambio_stato. Su una bolla che muove merce: all''emissione solleva il primo motivo di script.fn_check_ddt_merce, crea i prelievi automatici e scrive le uscite (vendite.fn_posta_ddt USCITA); alla consegna di un trasferimento scrive le entrate (ARRIVO); all''annullo di una bolla emessa storna i movimenti dei suoi prelievi (magazzino.fn_storna_movimenti_sorgente). UNA transazione. Ritorna (movimento_id, prelievo_id, qta). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt; il posting in vendite dal 2026-10-01 (brief-db-magazzino-registro-anello-interno).';
```

</div>

---
{% include-markdown "signature-core.md" %}
