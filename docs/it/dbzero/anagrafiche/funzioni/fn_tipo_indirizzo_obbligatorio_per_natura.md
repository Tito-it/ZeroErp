{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipo_indirizzo_obbligatorio_per_natura.md" %}
# ⚙️ Funzione `fn_tipo_indirizzo_obbligatorio_per_natura`

```sql
CREATE FUNCTION fn_tipo_indirizzo_obbligatorio_per_natura(p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura(p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ((EXISTS ( SELECT 1
            FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
           WHERE ((m.tipo_soggetto_dettaglio_id = fn_tipo_indirizzo_obbligatorio_per_natura.p_tipo_soggetto_dettaglio_id) AND (m.tipo_indirizzo_id = fn_tipo_indirizzo_obbligatorio_per_natura.p_tipo_indirizzo_id) AND m.obbligatorio))) AND anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(p_tipo_soggetto_dettaglio_id, p_tipo_indirizzo_id, p_oggi));
END

COMMENT ON FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura(p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
IS 'Vero se il tipo di indirizzo e'' obbligatorio per la natura, il giorno dato: la natura ha in config.tipi_soggetto_dettaglio_tipi_indirizzo la riga del tipo col flag obbligatorio, e anagrafiche.fn_tipo_indirizzo_ammesso_per_natura ammette il tipo quel giorno (la riga e'' attiva e valida). Natura NULL: falso. Il ripiego della riga non conta qui: lo leggono i mancanti (anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto). Sede unica della domanda sul layer SOGGETTO: la leggono i mancanti, la madre plurale anagrafiche.fn_crea_indirizzi_soggetto, i picker anagrafiche.fn_tipi_indirizzo_proponibili_natura e _soggetto, i builder dbops.fn_pgtap_crea_soggetto_pf e _pg e anagrafiche.fn_provisiona_dati_di_sviluppo. Gemella di anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
