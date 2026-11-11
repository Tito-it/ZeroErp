{% include-markdown "it/dbzero/catalogo/manual/fn_uom_conversione_capability.md" %}
# ⚙️ Funzione `fn_uom_conversione_capability`

```sql
CREATE FUNCTION fn_uom_conversione_capability(p_valido_dal date, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_uom_conversione_capability(p_valido_dal date, p_valido_al date)
 RETURNS TABLE(puo_eliminarsi boolean, puo_cambiare_attivo boolean, puo_chiudersi boolean, data_min_chiusura date, data_default_chiusura date, motivo_non_eliminabile text, motivo_non_chiudibile text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (NOT s.in_vigore),
     (NOT s.in_vigore),
     s.chiudibile,
         CASE
             WHEN s.chiudibile THEN GREATEST(s.dal, (s.oggi - 1))
             ELSE NULL::date
         END AS "case",
         CASE
             WHEN s.chiudibile THEN GREATEST(s.dal, s.oggi)
             ELSE NULL::date
         END AS "case",
         CASE
             WHEN s.in_vigore THEN 'UOM_STORIA_IN_VIGORE'::text
             ELSE NULL::text
         END AS "case",
         CASE
             WHEN (NOT s.chiudibile) THEN 'UOM_STORIA_CHIUSA'::text
             ELSE NULL::text
         END AS "case"
    FROM ( SELECT o.oggi,
             COALESCE(fn_uom_conversione_capability.p_valido_dal, '-infinity'::date) AS dal,
             (COALESCE(fn_uom_conversione_capability.p_valido_dal, '-infinity'::date) < o.oggi) AS in_vigore,
             ((fn_uom_conversione_capability.p_valido_al IS NULL) OR (fn_uom_conversione_capability.p_valido_al >= o.oggi)) AS chiudibile
            FROM ( SELECT script.fn_data_operativa() AS oggi) o) s;
END

COMMENT ON FUNCTION catalogo.fn_uom_conversione_capability(p_valido_dal date, p_valido_al date)
IS 'Che cosa si puo'' fare oggi su una conversione versionata, dalle sue date: una mappatura di un articolo (catalogo.articoli_uom_operativa) o una conversione generale (catalogo.unita_misura_conversioni). Una riga. p_valido_dal NULL vuol dire «da sempre». In vigore = comincia prima di oggi (ha giorni passati). puo_eliminarsi e puo_cambiare_attivo (spegnere o riaccendere): solo se non e'' in vigore, altrimenti motivo_non_eliminabile UOM_STORIA_IN_VIGORE. puo_chiudersi: la fine e'' vuota o non ancora passata (oggi o dopo), altrimenti motivo_non_chiudibile UOM_STORIA_CHIUSA. data_min_chiusura: la prima fine ammessa, la piu'' tarda fra l''inizio e ieri; data_default_chiusura: la piu'' tarda fra l''inizio e oggi; vuote se non si chiude. Il giorno e'' script.fn_data_operativa. Sono le regole 2 e 3 di catalogo.trgfn_uom_guard_storia, che la legge: lo stesso giudizio per il guard e per le viste catalogo.vw_articoli_uom_operativa_dettaglio e catalogo.vw_unita_misura_conversioni_dettaglio. Le colonne che fanno la conversione (unita'', articolo, fattore, inizio) non si cambiano mai: le blocca script.trgfn_lock_columns, e il form le legge da dbops.vw_non_editable_fields. La riga dell''unita'' base non e'' affare suo. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
