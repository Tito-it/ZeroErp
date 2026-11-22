{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipi_indirizzo_proponibili_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_tipi_indirizzo_proponibili_tipo_ruolo`

```sql
CREATE FUNCTION fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer, p_soggetto_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer, p_soggetto_id uuid)
 RETURNS TABLE(tipo_indirizzo_id integer, obbligatorio boolean, ammesso boolean, motivo_codice text, reason text, reason_key text, reason_valori jsonb, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ti.id,
     anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id, ctx.natura, ti.id, script.fn_data_operativa()) AS fn_tipo_indirizzo_obbligatorio_per_ruolo,
     (jsonb_array_length(c.motivi) = 0),
     ((c.motivi -> 0) ->> 'codice'::text),
     ((c.motivi -> 0) ->> 'reason'::text),
     ((c.motivi -> 0) ->> 'reason_key'::text),
     COALESCE(((c.motivi -> 0) -> 'valori'::text), '[]'::jsonb) AS "coalesce",
     c.motivi
    FROM ((( SELECT ( SELECT s.tipo_soggetto_dettaglio_id
                    FROM anagrafiche.soggetti s
                   WHERE (s.id = fn_tipi_indirizzo_proponibili_tipo_ruolo.p_soggetto_id)) AS natura) ctx
      CROSS JOIN config.tipi_indirizzi ti)
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id, '{}'::integer[], ti.id, script.fn_data_operativa(), NULL::bigint, ctx.natura) AS motivi) c)
   WHERE (((fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id IS NULL) OR (EXISTS ( SELECT 1
            FROM config.tipi_ruoli tr
           WHERE (tr.id = fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id)))) AND ((fn_tipi_indirizzo_proponibili_tipo_ruolo.p_soggetto_id IS NULL) OR (EXISTS ( SELECT 1
            FROM anagrafiche.soggetti s
           WHERE (s.id = fn_tipi_indirizzo_proponibili_tipo_ruolo.p_soggetto_id)))))
   ORDER BY (jsonb_array_length(c.motivi) = 0) DESC, ti.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer, p_soggetto_id uuid)
IS 'Il picker dei tipi di indirizzo per un ruolo che non esiste ancora, sul tipo di ruolo dell''assegnazione e sul soggetto a cui il ruolo si assegna: una riga per tipo di config.tipi_indirizzi, con obbligatorio (anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo sul tipo di ruolo e sulla natura del soggetto, oggi), ammesso, il primo motivo (motivo_codice, reason, reason_key, reason_valori) e tutti i motivi. Legge la stessa check della madre singolare, anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto, senza tipi presenti: i motivi possibili sono il tipo che il tipo di ruolo non ammette (E_TIPO_INDIRIZZO_NON_PERMESSO) e il tipo che la natura del soggetto non ammette (E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO). Il soggetto non ha default: NULL vuol dire soggetto non ancora scelto, e la natura non conta. Tipo di ruolo NULL o senza matrice: il ruolo non da'' motivi, come per il guard. Tipo di ruolo o soggetto non NULL che non esistono: nessuna riga, come anagrafiche.fn_tipi_indirizzo_proponibili_ruolo per un ruolo che non c''e''. Prima gli ammessi, poi gli altri, per codice interno. Giorno: script.fn_data_operativa(). SECURITY INVOKER. Gemello di anagrafiche.fn_tipi_indirizzo_proponibili_natura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
