# ⚙️ Funzione `fn_tipi_indirizzo_proponibili_ruolo`

```sql
CREATE FUNCTION fn_tipi_indirizzo_proponibili_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
 RETURNS TABLE(tipo_indirizzo_id integer, obbligatorio boolean, ammesso boolean, motivo_codice text, reason text, reason_key text, reason_valori jsonb, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ti.id,
     anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(ctx.tipo_ruolo, ctx.natura, ti.id, script.fn_data_operativa()) AS fn_tipo_indirizzo_obbligatorio_per_ruolo,
     (jsonb_array_length(c.motivi) = 0),
     ((c.motivi -> 0) ->> 'codice'::text),
     ((c.motivi -> 0) ->> 'reason'::text),
     ((c.motivi -> 0) ->> 'reason_key'::text),
     COALESCE(((c.motivi -> 0) -> 'valori'::text), '[]'::jsonb) AS "coalesce",
     c.motivi
    FROM ((( SELECT sr.id,
             sr.tipo_ruolo_id AS tipo_ruolo,
             s.tipo_soggetto_dettaglio_id AS natura,
             ARRAY( SELECT i.tipo_indirizzo_id
                    FROM anagrafiche.indirizzi i
                   WHERE ((i.soggetto_ruolo_id = sr.id) AND (NOT (i.istanza_utility_id IS DISTINCT FROM fn_tipi_indirizzo_proponibili_ruolo.p_istanza_utility_id)))) AS presenti
            FROM (anagrafiche.soggetti_ruoli sr
              JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
           WHERE (sr.id = fn_tipi_indirizzo_proponibili_ruolo.p_soggetto_ruolo_id)) ctx
      CROSS JOIN config.tipi_indirizzi ti)
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(ctx.tipo_ruolo, ctx.presenti, ti.id, script.fn_data_operativa(), ctx.id, ctx.natura) AS motivi) c)
   ORDER BY (jsonb_array_length(c.motivi) = 0) DESC, ti.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
IS 'Il picker dei tipi di indirizzo per il ruolo salvato, sul ruolo stesso (istanza NULL) o su una sua istanza (Aggiungi, e i tipi di destinazione della copia): una riga per tipo di config.tipi_indirizzi, con obbligatorio (anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo sul tipo di ruolo e sulla natura del soggetto, oggi), ammesso, il primo motivo (motivo_codice, reason, reason_key, reason_valori) e tutti i motivi. Contesto: il tipo di ruolo, la natura del soggetto del ruolo e i tipi che la chiave (ruolo, istanza) ha gia'', letti una volta; i motivi sono quelli di anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto, la check che la madre anagrafiche.fn_crea_indirizzo_ruolo solleva: il tipo gia'' presente (E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE), il tipo che il tipo di ruolo non ammette (E_TIPO_INDIRIZZO_NON_PERMESSO), il tipo che la natura non ammette (E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO). L''istanza non ha default: NULL vuol dire il ruolo. Prima gli ammessi, poi gli altri, per codice interno. Ruolo inesistente: nessuna riga. SECURITY INVOKER. Gemello di anagrafiche.fn_tipi_indirizzo_proponibili_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
