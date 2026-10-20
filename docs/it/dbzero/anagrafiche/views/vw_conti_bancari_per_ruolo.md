{% include-markdown "it/dbzero/anagrafiche/manual/vw_conti_bancari_per_ruolo.md" %}
# 🔍 View `vw_conti_bancari_per_ruolo`

> 📝 **Descrizione**
>
> Vista flat conti bancari con istanza_utility_id. Tutte le candidate RUOLO + SOGGETTO. Selezione singola in fn_get_conto_bancario_predefinito.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_conti_bancari_per_ruolo AS
WITH role_cand AS (
         SELECT sr.id AS soggetto_ruolo_id,
            r.uso,
            r.conto_bancario_id,
            r.id AS soggetto_ruolo_conto_id,
            NULL::bigint AS soggetto_conto_id,
            r.istanza_utility_id,
            r.predefinito,
            r.valido_dal,
            r.valido_al,
            r.data_update,
            'RUOLO'::character varying(10) AS fonte
           FROM ((anagrafiche.soggetti_ruoli sr
             JOIN anagrafiche.soggetti_ruoli_conti_bancari r ON ((r.soggetto_ruolo_id = sr.id)))
             JOIN anagrafiche.conti_bancari cb ON ((cb.id = r.conto_bancario_id)))
          WHERE (((r.valido_dal IS NULL) OR (r.valido_dal <= ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AND ((r.valido_al IS NULL) OR (r.valido_al >= ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AND (COALESCE(r.bloccato, false) = false) AND (cb.attivo = true))
        ), subj_cand AS (
         SELECT sr.id AS soggetto_ruolo_id,
            s.uso,
            s.conto_bancario_id,
            NULL::bigint AS soggetto_ruolo_conto_id,
            s.id AS soggetto_conto_id,
            NULL::bigint AS istanza_utility_id,
            s.predefinito,
            s.valido_dal,
            s.valido_al,
            s.data_update,
            'SOGGETTO'::character varying(10) AS fonte
           FROM ((anagrafiche.soggetti_ruoli sr
             JOIN anagrafiche.soggetti_conti_bancari s ON ((s.soggetto_id = sr.soggetto_id)))
             JOIN anagrafiche.conti_bancari cb ON ((cb.id = s.conto_bancario_id)))
          WHERE (((s.valido_dal IS NULL) OR (s.valido_dal <= ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AND ((s.valido_al IS NULL) OR (s.valido_al >= ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AND (COALESCE(s.bloccato, false) = false) AND (cb.attivo = true))
        )
 SELECT soggetto_ruolo_id,
    uso,
    conto_bancario_id,
    soggetto_ruolo_conto_id,
    soggetto_conto_id,
    istanza_utility_id,
    fonte,
    predefinito,
    valido_dal,
    valido_al,
    data_update
   FROM ( SELECT role_cand.soggetto_ruolo_id,
            role_cand.uso,
            role_cand.conto_bancario_id,
            role_cand.soggetto_ruolo_conto_id,
            role_cand.soggetto_conto_id,
            role_cand.istanza_utility_id,
            role_cand.predefinito,
            role_cand.valido_dal,
            role_cand.valido_al,
            role_cand.data_update,
            role_cand.fonte
           FROM role_cand
        UNION ALL
         SELECT subj_cand.soggetto_ruolo_id,
            subj_cand.uso,
            subj_cand.conto_bancario_id,
            subj_cand.soggetto_ruolo_conto_id,
            subj_cand.soggetto_conto_id,
            subj_cand.istanza_utility_id,
            subj_cand.predefinito,
            subj_cand.valido_dal,
            subj_cand.valido_al,
            subj_cand.data_update,
            subj_cand.fonte
           FROM subj_cand) c
  ORDER BY soggetto_ruolo_id, uso,
        CASE
            WHEN (((fonte)::text = 'RUOLO'::text) AND (istanza_utility_id IS NOT NULL)) THEN 1
            WHEN (((fonte)::text = 'RUOLO'::text) AND (istanza_utility_id IS NULL)) THEN 2
            WHEN ((fonte)::text = 'SOGGETTO'::text) THEN 3
            ELSE NULL::integer
        END, predefinito DESC, data_update DESC;
```

</div>


---
{% include-markdown "signature-core.md" %}
