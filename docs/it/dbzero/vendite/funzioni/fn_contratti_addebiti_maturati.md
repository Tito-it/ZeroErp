{% include-markdown "it/dbzero/vendite/manual/fn_contratti_addebiti_maturati.md" %}
# ⚙️ Funzione `fn_contratti_addebiti_maturati`

```sql
CREATE FUNCTION fn_contratti_addebiti_maturati(p_competenza_mese date, p_billing_account_id bigint, p_contratto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratti_addebiti_maturati(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_contratto_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(contratto_id bigint, contratto_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, meta jsonb, ramo integer, scarto text)
 LANGUAGE plpgsql
AS $function$
-- Scopo: gli addebiti maturati dei contratti, senza la provenienza del
--   prezzo: la proiezione di vendite.fn_contratti_addebiti_maturati_con_provenienza,
--   dove la regola sta una volta. Resta per chi legge questa firma
--   (vendite.vw_dash_fatturazione_contratti e le viste a valle).
BEGIN
  RETURN QUERY
  SELECT a.contratto_id,
         a.contratto_uid,
         a.riga_id,
         a.billing_account_id,
         a.utility_id,
         a.emittente_soggetto_ruolo_id,
         a.competenza_dal,
         a.competenza_al,
         a.fatturazione_immediata,
         a.segment_key,
         a.articolo_id,
         a.istanza_utility_id,
         a.data_attivita,
         a.uom_id,
         a.quantita,
         a.qta_operativa,
         a.uom_operativa_id,
         a.factor_to_base,
         a.competenza_mese,
         a.prezzo_snapshot,
         a.prezzo_bloccato,
         a.meta,
         a.ramo,
         a.scarto
    FROM vendite.fn_contratti_addebiti_maturati_con_provenienza(
           p_competenza_mese, p_billing_account_id, p_contratto_id) a;
END
$function$

COMMENT ON FUNCTION vendite.fn_contratti_addebiti_maturati(p_competenza_mese date, p_billing_account_id bigint, p_contratto_id bigint)
IS 'Gli addebiti maturati dei contratti ATTIVO e CESSATO a questo giro e non ancora in commessa, con gli scartati e il motivo (scarto), senza la provenienza del prezzo: la proiezione di vendite.fn_contratti_addebiti_maturati_con_provenienza, che ha la regola (rami, fonti, scarti). La legge vendite.vw_dash_fatturazione_contratti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
