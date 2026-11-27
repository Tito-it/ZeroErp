{% include-markdown "it/dbzero/anagrafiche/manual/fn_parametri_importo_utility.md" %}
# ⚙️ Funzione `fn_parametri_importo_utility`

```sql
CREATE FUNCTION fn_parametri_importo_utility(p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_parametri_importo_utility(p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
 RETURNS TABLE(arrotondamento_importi_dec smallint, metodo_arrotondamento_importi character varying, minimo_soglia_min numeric, minimo_soglia_max numeric, personalizzata boolean)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT script.fn_log_and_raise_error('anagrafiche'::text, 'fn_parametri_importo_utility'::text, 'E_PARAMETRO_INVALIDO'::text, jsonb_build_object('detail', 'p_emittente_soggetto_ruolo_id non e'' un emittente', 'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id, 'utility_id', p_utility_id), NULL::uuid, VARIADIC ARRAY['p_emittente_soggetto_ruolo_id non e'' un emittente'::text]) AS fn_log_and_raise_error
   WHERE (NOT (EXISTS ( SELECT 1
            FROM anagrafiche.emittenti_fiscali ef
           WHERE (ef.soggetto_ruolo_id = fn_parametri_importo_utility.p_emittente_soggetto_ruolo_id))));
 SELECT COALESCE(e.arrotondamento_importi_dec, u.arrotondamento_importi_dec) AS "coalesce",
     COALESCE(e.metodo_arrotondamento_importi, ef.rounding_policy, u.metodo_arrotondamento_importi) AS "coalesce",
     e.minimo_soglia_min,
     e.minimo_soglia_max,
     (e.id IS NOT NULL)
    FROM ((config.utilities u
      LEFT JOIN anagrafiche.emittenti_fiscali_utilities e ON (((e.utility_id = u.id) AND (e.emittente_soggetto_ruolo_id = fn_parametri_importo_utility.p_emittente_soggetto_ruolo_id) AND (e.attivo IS TRUE))))
      LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = fn_parametri_importo_utility.p_emittente_soggetto_ruolo_id)))
   WHERE (u.id = fn_parametri_importo_utility.p_utility_id);
END

COMMENT ON FUNCTION anagrafiche.fn_parametri_importo_utility(p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'I parametri d''importo effettivi di un emittente per una utility: decimali e metodo d''arrotondamento della riga attiva di anagrafiche.emittenti_fiscali_utilities se c''e'', altrimenti (per il solo metodo) la policy generale emittenti_fiscali.rounding_policy, altrimenti il valore di sistema di config.utilities; le soglie del minimo solo dall''emittente (NULL = nessun minimo); personalizzata = la riga dell''emittente c''e''. Un ruolo che non e'' un emittente, o NULL, solleva E_PARAMETRO_INVALIDO: i valori di sistema sono quelli di un''azienda senza personalizzazioni, non la risposta per chi azienda non e''. Una riga se l''utility esiste, zero se non esiste o e'' NULL: e'' il segnale che i lettori traducono in E_CONFIG_MANCANTE. Sede unica: la leggono vendite.fn_ricalcola_totali_fattura, vendite.fn_parametri_importo_riga e anagrafiche.fn_lookup_utilities_per_ba.';
```

</div>

---
{% include-markdown "signature-core.md" %}
