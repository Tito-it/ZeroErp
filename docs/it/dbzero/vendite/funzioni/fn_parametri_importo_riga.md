{% include-markdown "it/dbzero/vendite/manual/fn_parametri_importo_riga.md" %}
# ⚙️ Funzione `fn_parametri_importo_riga`

```sql
CREATE FUNCTION fn_parametri_importo_riga(p_articolo_id uuid, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_parametri_importo_riga(p_articolo_id uuid, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
 RETURNS TABLE(arrotondamento_importi_dec smallint, metodo_arrotondamento_importi character varying)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT COALESCE(r.arrotondamento_importi_dec, p.arrotondamento_importi_dec) AS "coalesce",
     COALESCE(r.metodo_arrotondamento_importi, p.metodo_arrotondamento_importi) AS "coalesce"
    FROM ((( SELECT 1 AS "?column?") base
      LEFT JOIN vendite.articolo_regole_fatturazione r ON ((r.articolo_id = fn_parametri_importo_riga.p_articolo_id)))
      LEFT JOIN LATERAL anagrafiche.fn_parametri_importo_utility(fn_parametri_importo_riga.p_emittente_soggetto_ruolo_id, fn_parametri_importo_riga.p_utility_id) p(arrotondamento_importi_dec, metodo_arrotondamento_importi, minimo_soglia_min, minimo_soglia_max, personalizzata) ON (true));
END

COMMENT ON FUNCTION vendite.fn_parametri_importo_riga(p_articolo_id uuid, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'Decimali e metodo con cui si arrotonda l''importo di una riga di fattura (2026-10-21, brief-db-modelli-documento-standard §10.7 R-3): la regola dell''articolo (vendite.articolo_regole_fatturazione) se c''e'', altrimenti i parametri effettivi dell''emittente per l''utility della fattura (anagrafiche.fn_parametri_importo_utility). Sempre una riga; NULL solo senza regole dell''articolo e senza utility. Sede unica: la leggono vendite.trgfn_fatture_righe_importo e il BE (gruppo delle attivita'' fatturabili). Prima il default 2 / HALF_UP era un letterale nel trigger e nel BE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
