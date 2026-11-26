{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipi_indirizzo_proponibili_soggetto.md" %}
# ⚙️ Funzione `fn_tipi_indirizzo_proponibili_soggetto`

```sql
CREATE FUNCTION fn_tipi_indirizzo_proponibili_soggetto(p_soggetto_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(p_soggetto_id uuid)
 RETURNS TABLE(tipo_indirizzo_id integer, obbligatorio boolean, ammesso boolean, motivo_codice text, reason text, reason_key text, reason_valori jsonb, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ti.id,
     anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura(ctx.natura, ti.id, script.fn_data_operativa()) AS fn_tipo_indirizzo_obbligatorio_per_natura,
     (jsonb_array_length(c.motivi) = 0),
     ((c.motivi -> 0) ->> 'codice'::text),
     ((c.motivi -> 0) ->> 'reason'::text),
     ((c.motivi -> 0) ->> 'reason_key'::text),
     COALESCE(((c.motivi -> 0) -> 'valori'::text), '[]'::jsonb) AS "coalesce",
     c.motivi
    FROM ((( SELECT s.id,
             s.tipo_soggetto_dettaglio_id AS natura,
             ARRAY( SELECT i.tipo_indirizzo_id
                    FROM anagrafiche.indirizzi_soggetti i
                   WHERE (i.soggetto_id = s.id)) AS presenti
            FROM anagrafiche.soggetti s
           WHERE (s.id = fn_tipi_indirizzo_proponibili_soggetto.p_soggetto_id)) ctx
      CROSS JOIN config.tipi_indirizzi ti)
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(ctx.natura, ctx.presenti, ti.id, script.fn_data_operativa(), ctx.id) AS motivi) c)
   ORDER BY (jsonb_array_length(c.motivi) = 0) DESC, ti.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(p_soggetto_id uuid)
IS 'Il picker dei tipi di indirizzo per il soggetto salvato (Aggiungi, e i tipi di destinazione della copia): una riga per tipo di config.tipi_indirizzi, con obbligatorio (anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura, oggi), ammesso, il primo motivo (motivo_codice, reason, reason_key, reason_valori) e tutti i motivi. Contesto: la natura e i tipi che il soggetto ha gia'', letti una volta; i motivi sono quelli di anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto, la check che la madre anagrafiche.fn_crea_indirizzo_soggetto solleva: il tipo gia'' presente (E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE), poi il tipo che la natura non ammette (E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO). Prima gli ammessi, poi gli altri, per codice interno. Soggetto inesistente: nessuna riga. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
