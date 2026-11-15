# ⚙️ Funzione `fn_tipi_indirizzo_proponibili_tipo_ruolo`

```sql
CREATE FUNCTION fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer)
 RETURNS TABLE(tipo_indirizzo_id integer, obbligatorio boolean, ammesso boolean, motivo_codice text, reason text, reason_key text, reason_valori jsonb, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ti.id,
     (EXISTS ( SELECT 1
            FROM config.tipi_ruolo_tipi_indirizzo mo
           WHERE ((mo.tipo_ruolo_id = fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id) AND (mo.tipo_indirizzo_id = ti.id) AND mo.obbligatorio AND anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo((fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id)::bigint, ti.id, script.fn_data_operativa())))) AS "exists",
     (jsonb_array_length(c.motivi) = 0),
     ((c.motivi -> 0) ->> 'codice'::text),
     ((c.motivi -> 0) ->> 'reason'::text),
     ((c.motivi -> 0) ->> 'reason_key'::text),
     COALESCE(((c.motivi -> 0) -> 'valori'::text), '[]'::jsonb) AS "coalesce",
     c.motivi
    FROM (config.tipi_indirizzi ti
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id, '{}'::integer[], ti.id, script.fn_data_operativa(), NULL::bigint) AS motivi) c)
   WHERE ((fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id IS NULL) OR (EXISTS ( SELECT 1
            FROM config.tipi_ruoli tr
           WHERE (tr.id = fn_tipi_indirizzo_proponibili_tipo_ruolo.p_tipo_ruolo_id))))
   ORDER BY (jsonb_array_length(c.motivi) = 0) DESC, ti.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(p_tipo_ruolo_id integer)
IS 'Il picker dei tipi di indirizzo per un ruolo che non esiste ancora, sul tipo di ruolo dell''assegnazione: una riga per tipo di config.tipi_indirizzi, con obbligatorio (riga obbligatoria della matrice che anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo ammette oggi), ammesso, il primo motivo (motivo_codice, reason, reason_key, reason_valori) e tutti i motivi. Legge la stessa check della madre singolare, anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto, senza tipi presenti: l''unico motivo possibile e'' il tipo che il tipo di ruolo non ammette (E_TIPO_INDIRIZZO_NON_PERMESSO). Tipo di ruolo NULL o senza matrice: tutti ammessi, come per il guard. Tipo di ruolo che non esiste in config.tipi_ruoli: nessuna riga, come anagrafiche.fn_tipi_indirizzo_proponibili_ruolo per un ruolo che non c''e''. Prima gli ammessi, poi gli altri, per codice interno. Giorno: script.fn_data_operativa(). Gemello di anagrafiche.fn_tipi_indirizzo_proponibili_natura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
