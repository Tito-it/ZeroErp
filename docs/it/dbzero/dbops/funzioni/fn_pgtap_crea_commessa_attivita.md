{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_commessa_attivita.md" %}
# ⚙️ Funzione `fn_pgtap_crea_commessa_attivita`

```sql
CREATE FUNCTION fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric DEFAULT 10)
 RETURNS TABLE(attivita_id bigint, articolo_id uuid, uom_id bigint, competenza_dal date, competenza_al date)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un'ATTIVITA' approvata su una
--   commessa gia' costruita, scritta dalla madre del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_a AS
--   SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
--              (SELECT commessa_id FROM tmp_c));
-- ⛔ L'emissione NON la fa: e' il caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ba_id    vendite.commesse.billing_account_id%TYPE;
    v_dal      vendite.commesse_attivita.competenza_dal%TYPE;
    v_al       vendite.commesse_attivita.competenza_al%TYPE;
    v_ist_id   anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_articolo vendite.commesse_attivita.articolo_id%TYPE;
    v_uom      vendite.commesse_attivita.uom_id%TYPE;
    v_attivita vendite.commesse_attivita.id%TYPE;
BEGIN
    SELECT c.billing_account_id,
           COALESCE(c.competenza_dal, date_trunc('month', (SELECT script.fn_data_operativa()))::date),
           COALESCE(c.competenza_al,
                    (date_trunc('month', (SELECT script.fn_data_operativa())) + interval '1 month - 1 day')::date)
      INTO v_ba_id, v_dal, v_al
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    -- ⚠️ Guard sul parametro: una commessa che non esiste
    --   farebbe morire la madre su un NULL che non la nomina.
    IF v_ba_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_commessa_attivita: nessuna commessa con id = %',
            p_commessa_id;
    END IF;

    SELECT ba.istanza_utility_id INTO v_ist_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = v_ba_id;

    -- L'articolo si costruisce: il catalogo, da zero, e' vuoto.
    v_articolo := dbops.fn_pgtap_crea_articolo(
        ('PGT-ATT-' || substr(md5(clock_timestamp()::text || p_commessa_id::text), 1, 12))::varchar,
        false);

    SELECT a.uom_id INTO v_uom
      FROM catalogo.articoli a
     WHERE a.id = v_articolo;

    SELECT r.attivita_id INTO v_attivita
      FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => p_commessa_id,
        p_segment_key                   => ('PGT-SEG-' || substr(md5(clock_timestamp()::text || v_articolo::text), 1, 12))::varchar,
        p_articolo_id                   => v_articolo,
        p_istanza_utility_id            => v_ist_id,
        p_data_attivita                 => v_dal,
        p_uom_id                        => v_uom,
        p_quantita                      => 1.000000,
        p_competenza_mese               => date_trunc('month', v_dal)::date,
        p_competenza_dal                => v_dal,
        p_competenza_al                 => v_al,
        p_prezzo_snapshot               => p_prezzo_snapshot,
        p_prezzo_base_snapshot          => NULL,
        p_origine_prezzo                => NULL,
        p_tipo_variazione_applicata     => NULL,
        p_valore_variazione_applicata   => NULL,
        p_promo_id                      => NULL,
        p_contratto_id                  => NULL,
        p_categoria_cliente_id_snapshot => NULL,
        p_classe_utenza_id_snapshot     => NULL,
        p_stato_approvazione            => 'APPROVATA',
        p_stato_emissione               => 'NON_EMESSA',
        p_sorgente_tipo_id              => (SELECT s.id FROM config.sorgenti s
                                             WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
        p_sorgente_uid                  => p_commessa_id::text,
        p_tipo_movimento                => 'NORMALE',
        p_tipo_consumo                  => 'CONGUAGLIO',
        p_meta                          => jsonb_build_object('test_scope', 'pgtap_commessa_attivita')) r;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_attivita, v_articolo, v_uom, v_dal, v_al;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric)
IS 'Fixture pgTAP: un''ATTIVITA'' su una commessa gia'' costruita (dbops.fn_pgtap_crea_commessa), scritta dalla madre vendite.fn_upsert_commessa_attivita: APPROVATA e NON_EMESSA, con la commessa come sorgente, quantita'' 1 e prezzo snapshot FIXED (secondo parametro, default 10). L''articolo lo costruisce (dbops.fn_pgtap_crea_articolo, non gestito): da zero il catalogo e'' vuoto. Istanza dal billing account della commessa, competenza dalla commessa (o il mese corrente). ⛔ NON emette e non lega a una fattura: e'' il caso del test. ⚠️ Una commessa inesistente parla. Esce con i vincoli IMMEDIATE. Brief: brief-db-fixture-rls-documenti-costruiti.';
```

---
{% include-markdown "signature-core.md" %}
