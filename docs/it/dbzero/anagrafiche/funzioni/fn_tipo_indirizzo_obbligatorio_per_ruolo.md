{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipo_indirizzo_obbligatorio_per_ruolo.md" %}
# ⚙️ Funzione `fn_tipo_indirizzo_obbligatorio_per_ruolo`

```sql
CREATE FUNCTION fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM anagrafiche.fn_indirizzi_obbligatori_ruolo(fn_tipo_indirizzo_obbligatorio_per_ruolo.p_tipo_ruolo_id, fn_tipo_indirizzo_obbligatorio_per_ruolo.p_tipo_soggetto_dettaglio_id, fn_tipo_indirizzo_obbligatorio_per_ruolo.p_oggi) o(tipo_indirizzo_id, ripiego_tipo_indirizzo_id)
           WHERE (o.tipo_indirizzo_id = fn_tipo_indirizzo_obbligatorio_per_ruolo.p_tipo_indirizzo_id))) AS "exists";
END

COMMENT ON FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
IS 'Vero se il tipo di indirizzo e'' obbligatorio per il tipo di ruolo, su un soggetto della natura data, il giorno dato: e'' uno dei tipi che il requisito del ruolo chiede (anagrafiche.fn_indirizzi_obbligatori_ruolo). Il tipo di una riga obbligatoria che la natura ammette e'' obbligatorio; se la natura non lo ammette, e'' obbligatorio il ripiego della riga, quando il ruolo e la natura lo ammettono. Natura NULL: la natura non conta. Lo leggono la copia degli obbligatori di anagrafiche.fn_crea_indirizzi_ruolo e la colonna obbligatorio dei picker anagrafiche.fn_tipi_indirizzo_proponibili_ruolo e anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo: copiano e propongono cio'' che i guard degli obbligatori pretendono. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
