# ⚙️ Funzione `fn_utilities_emittente`

```sql
CREATE FUNCTION fn_utilities_emittente(p_emittente_soggetto_ruolo_id bigint, p_ruolo_codice_soggetto character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_utilities_emittente(p_emittente_soggetto_ruolo_id bigint, p_ruolo_codice_soggetto character varying DEFAULT NULL::character varying)
 RETURNS TABLE(utility_id integer, codice character varying, descrizione character varying, gestita boolean, riga_id bigint, arrotondamento_importi_dec smallint, metodo_arrotondamento_importi character varying, minimo_soglia_min numeric, minimo_soglia_max numeric, personalizzata boolean)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT script.fn_log_and_raise_error('anagrafiche'::text, 'fn_utilities_emittente'::text, 'E_PARAMETRO_INVALIDO'::text, jsonb_build_object('detail', 'p_emittente_soggetto_ruolo_id non e'' un emittente', 'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id), NULL::uuid, VARIADIC ARRAY['p_emittente_soggetto_ruolo_id non e'' un emittente'::text]) AS fn_log_and_raise_error
   WHERE (NOT (EXISTS ( SELECT 1
            FROM anagrafiche.emittenti_fiscali ef
           WHERE (ef.soggetto_ruolo_id = fn_utilities_emittente.p_emittente_soggetto_ruolo_id))));
 SELECT u.id,
     u.codice,
     u.descrizione,
     ((e.id IS NOT NULL) AND (ef.attivo IS TRUE)),
     e.id,
     par.arrotondamento_importi_dec,
     par.metodo_arrotondamento_importi,
     par.minimo_soglia_min,
     par.minimo_soglia_max,
     par.personalizzata
    FROM (((config.utilities u
      JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = fn_utilities_emittente.p_emittente_soggetto_ruolo_id)))
      LEFT JOIN anagrafiche.emittenti_fiscali_utilities e ON (((e.emittente_soggetto_ruolo_id = fn_utilities_emittente.p_emittente_soggetto_ruolo_id) AND (e.utility_id = u.id))))
      CROSS JOIN LATERAL anagrafiche.fn_parametri_importo_utility(fn_utilities_emittente.p_emittente_soggetto_ruolo_id, u.id) par(arrotondamento_importi_dec, metodo_arrotondamento_importi, minimo_soglia_min, minimo_soglia_max, personalizzata))
   WHERE ((EXISTS ( SELECT 1
            FROM (config.utilities_tipi_ruolo m
              JOIN config.tipi_ruoli t ON ((t.id = m.tipo_ruolo_id)))
           WHERE ((m.utility_id = u.id) AND ((t.codice_interno)::text = 'EF'::text) AND (m.attivo IS TRUE) AND ((m.valido_dal IS NULL) OR (m.valido_dal <= script.fn_data_operativa())) AND ((m.valido_al IS NULL) OR (m.valido_al >= script.fn_data_operativa()))))) AND ((fn_utilities_emittente.p_ruolo_codice_soggetto IS NULL) OR (EXISTS ( SELECT 1
            FROM (config.utilities_tipi_ruolo m
              JOIN config.tipi_ruoli t ON ((t.id = m.tipo_ruolo_id)))
           WHERE ((m.utility_id = u.id) AND ((t.codice_interno)::text = (fn_utilities_emittente.p_ruolo_codice_soggetto)::text) AND (m.attivo IS TRUE) AND ((m.valido_dal IS NULL) OR (m.valido_dal <= script.fn_data_operativa())) AND ((m.valido_al IS NULL) OR (m.valido_al >= script.fn_data_operativa())))))))
   ORDER BY u.codice;
END

COMMENT ON FUNCTION anagrafiche.fn_utilities_emittente(p_emittente_soggetto_ruolo_id bigint, p_ruolo_codice_soggetto character varying)
IS 'Le utility di un''azienda (emittente fiscale): una riga per ogni utility che la matrice config.utilities_tipi_ruolo ammette oggi (giorno operativo) per l''emittente fiscale e, se p_ruolo_codice_soggetto e'' dato (codice_interno: CL, FO, GE), anche per quel ruolo. gestita = l''azienda ha la sua riga in anagrafiche.emittenti_fiscali_utilities ed e'' accesa; riga_id e'' quella riga, NULL se non c''e''; i parametri d''importo e personalizzata vengono da anagrafiche.fn_parametri_importo_utility. Un ruolo che non e'' un emittente, o NULL, solleva E_PARAMETRO_INVALIDO. Sede unica della regola delle utility ammesse: la leggono anagrafiche.fn_lookup_utilities_per_ba (le sole gestite) e il drawer dell''azienda (tutte, per attivarle). STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
