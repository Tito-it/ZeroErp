{% include-markdown "it/dbzero/vendite/manual/fn_snapshot_intestazione_fattura.md" %}
# ⚙️ Funzione `fn_snapshot_intestazione_fattura`

```sql
CREATE FUNCTION fn_snapshot_intestazione_fattura(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_snapshot_intestazione_fattura(p_fattura_id bigint)
 RETURNS TABLE(scritta boolean)
 LANGUAGE plpgsql
AS $function$
-- Scopo: congelare sulla testata l'identita' fiscale delle due
--        parti — emittente e cliente — cosi' come sono nel
--        momento in cui la fattura nasce.
-- Uso:   wrapper di lotto vendite.fn_snapshot_fattura_lotto,
--        step DRAFT, insieme allo snapshot degli indirizzi.
DECLARE
    v_emittente_sr anagrafiche.soggetti_ruoli.id%TYPE;
    v_cliente_sr   anagrafiche.soggetti_ruoli.id%TYPE;
    v_ba_id        anagrafiche.billing_account.id%TYPE;
    v_ba_codice    anagrafiche.billing_account.codice%TYPE;
    v_emittente    jsonb;
    v_cliente      jsonb;
    v_sede         jsonb;
    v_scritta      boolean := FALSE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_intestazione_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id),
            NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- Le due controparti. Il BA e' quello di TESTATA, che in
    -- gerarchia e' il padre (D-P): la fattura e' del padre.
    SELECT f.emittente_soggetto_ruolo_id, ba.soggetto_ruolo_id,
           ba.id, ba.codice
      INTO v_emittente_sr, v_cliente_sr, v_ba_id, v_ba_codice
      FROM vendite.fatture f
      JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
     WHERE f.id = p_fattura_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_intestazione_fattura', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id),
            NULL::uuid, p_fattura_id::text);
    END IF;

    -- ===== Sede legale dell'emittente =====
    -- Stessa catena del cliente: RUOLO e, in mancanza, SOGGETTO.
    -- Istanza NULL: l'emittente non ha forniture.
    SELECT r.snapshot INTO v_sede
      FROM script.fn_resolve_indirizzo_documento(
               v_emittente_sr, NULL, 'SEDELEG') r;

    -- ===== Emittente =====
    SELECT jsonb_strip_nulls(jsonb_build_object(
             'soggetto_ruolo_id',   v_emittente_sr,
             'soggetto_id',         srd.soggetto_id,
             'denominazione',       NULLIF(btrim(srd.ragione_sociale_completa::text), ''),
             'codice_fiscale',      NULLIF(btrim(srd.codice_fiscale::text), ''),
             'id_fiscale',          NULLIF(btrim(srd.id_fiscale_univoco_cf_piva::text), ''),
             'emittente_fiscale_id', ef.id,
             'emittente_codice',    NULLIF(btrim(ef.codice::text), ''),
             'regime_fiscale_rf',   NULLIF(btrim(ef.regime_fiscale_rf::text), ''),
             'capitale_sociale',    ds.capitale_sociale,
             'socio_unico',         NULLIF(btrim(ds.socio_unico::text), ''),
             'liquidazione',        NULLIF(btrim(ds.liquidazione::text), ''),
             -- Valore + id: il numero REA senza la provincia non
             -- identifica nulla, e la sigla e' un char(n).
             'rea', CASE WHEN ds.iscrizione_rea IS NULL THEN NULL
                         ELSE jsonb_strip_nulls(jsonb_build_object(
                                'numero',       NULLIF(btrim(ds.iscrizione_rea::text), ''),
                                'provincia',    NULLIF(btrim(pr.sigla::text), ''),
                                'provincia_id', ds.id_prov_iscri_rea)) END,
             'forma_giuridica', CASE WHEN fg.id IS NULL THEN NULL
                         ELSE jsonb_strip_nulls(jsonb_build_object(
                                'id',          fg.id,
                                'codice',      NULLIF(btrim(fg.codice::text), ''),
                                'descrizione', NULLIF(btrim(fg.descrizione::text), ''))) END,
             'sede', v_sede))
      INTO v_emittente
      FROM anagrafiche.vw_soggetti_ruoli_dettaglio srd
      LEFT JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = srd.soggetto_ruolo_id
      LEFT JOIN anagrafiche.dati_societari ds ON ds.soggetto_id = srd.soggetto_id
      LEFT JOIN config.province pr        ON pr.id = ds.id_prov_iscri_rea
      LEFT JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id
     WHERE srd.soggetto_ruolo_id = v_emittente_sr;

    -- ===== Cliente =====
    -- L'indirizzo di fatturazione NON sta qui: sta in
    -- vendite.fatture_indirizzi, che e' la collezione degli
    -- indirizzi del cliente. Qui c'e' solo la sua identita'.
    SELECT jsonb_strip_nulls(jsonb_build_object(
             'soggetto_ruolo_id',  v_cliente_sr,
             'soggetto_id',        srd.soggetto_id,
             'denominazione',      NULLIF(btrim(srd.ragione_sociale_completa::text), ''),
             'codice_fiscale',     NULLIF(btrim(srd.codice_fiscale::text), ''),
             'id_fiscale',         NULLIF(btrim(srd.id_fiscale_univoco_cf_piva::text), ''),
             'billing_account_id', v_ba_id,
             'ba_codice',          NULLIF(btrim(v_ba_codice::text), ''),
             -- Instradamento SDI: «a chi l'abbiamo trasmessa» e'
             -- un fatto del documento, non dell'anagrafica.
             'codice_sdi',         NULLIF(btrim(ds.codice_sdi::text), ''),
             'pec_fatturazione',   NULLIF(btrim(ds.pec_fatturazione::text), ''),
             'destinatario_fe',    NULLIF(btrim(ds.destinatario_fe::text), '')))
      INTO v_cliente
      FROM anagrafiche.vw_soggetti_ruoli_dettaglio srd
      LEFT JOIN anagrafiche.dati_societari ds ON ds.soggetto_id = srd.soggetto_id
     WHERE srd.soggetto_ruolo_id = v_cliente_sr;

    -- ===== Scrittura, solo se cambia qualcosa =====
    UPDATE vendite.fatture f
       SET emittente_snapshot = v_emittente,
           cliente_snapshot   = v_cliente
     WHERE f.id = p_fattura_id
       AND (f.emittente_snapshot IS DISTINCT FROM v_emittente
         OR f.cliente_snapshot   IS DISTINCT FROM v_cliente);

    IF FOUND THEN
        v_scritta := TRUE;
    END IF;

    RETURN QUERY SELECT v_scritta;
END;
$function$

COMMENT ON FUNCTION vendite.fn_snapshot_intestazione_fattura(p_fattura_id bigint)
IS 'Congela sulla testata l''identita'' fiscale delle due parti al momento in cui la fattura nasce: emittente (denominazione, CF, id fiscale, regime fiscale, REA, capitale sociale, socio unico, liquidazione, forma giuridica e SEDE LEGALE) e cliente (denominazione, CF, id fiscale, billing account e instradamento SDI). SORELLA di fn_snapshot_indirizzi_fattura e non sua estensione: quella conta RIGHE di indirizzo, e scriverci dentro la testata farebbe mentire i suoi contatori. La sede dell''emittente usa la stessa catena del cliente — script.fn_resolve_indirizzo_documento(sr, NULL, ''SEDELEG'') — cioe'' RUOLO e, in mancanza, SOGGETTO: e'' li'' che la sede degli emittenti effettivamente sta, ed e'' il motivo per cui non era mai comparsa in stampa. Di ogni entita'' referenziata si congela il VALORE e si tiene l''id come provenienza: uno snapshot che contiene solo id non e'' uno snapshot. Ogni testo passa da NULLIF(btrim(...)) perche'' destinatario_fe e la sigla provincia sono character a larghezza fissa. L''UPDATE ha il WHERE IS DISTINCT FROM: a dati invariati non scrive. Ritorna scritta = true solo se ha davvero cambiato qualcosa. Shape NON contrattuale finche'' il builder XML FatturaPA non esiste. brief-db-snapshot-intestazione-fattura §3.1/§3.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
