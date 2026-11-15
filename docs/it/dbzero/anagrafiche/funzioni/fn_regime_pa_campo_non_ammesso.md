# ⚙️ Funzione `fn_regime_pa_campo_non_ammesso`

```sql
CREATE FUNCTION fn_regime_pa_campo_non_ammesso(p_tipo_soggetto_dettaglio_id bigint, p_cliente_pa character, p_split_payment character)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_regime_pa_campo_non_ammesso(p_tipo_soggetto_dettaglio_id bigint, p_cliente_pa character, p_split_payment character)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN ((fn_regime_pa_campo_non_ammesso.p_cliente_pa = 'S'::bpchar) AND (NOT tsd.cliente_pa_ammesso)) THEN 'cliente_pa'::text
             WHEN ((fn_regime_pa_campo_non_ammesso.p_split_payment = 'S'::bpchar) AND (NOT tsd.split_payment_ammesso)) THEN 'split_payment'::text
             ELSE NULL::text
         END AS "case"
    FROM config.tipi_soggetto_dettaglio tsd
   WHERE (tsd.id = fn_regime_pa_campo_non_ammesso.p_tipo_soggetto_dettaglio_id);
END

COMMENT ON FUNCTION anagrafiche.fn_regime_pa_campo_non_ammesso(p_tipo_soggetto_dettaglio_id bigint, p_cliente_pa character, p_split_payment character)
IS 'Il primo flag del regime PA proposto a S che la natura di dettaglio non ammette: ''cliente_pa'' se cliente_pa = S e config.tipi_soggetto_dettaglio.cliente_pa_ammesso e'' falso, altrimenti ''split_payment'' se split_payment = S e split_payment_ammesso e'' falso; NULL se entrambi sono ammessi, o se la natura e'' NULL o non esiste. Sui valori proposti, non sulla riga salvata. Sede unica del predicato: la leggono anagrafiche.trgfn_soggetti_guard_regime_pa e anagrafiche.fn_check_cambio_natura_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
