{% include-markdown "it/dbzero/anagrafiche/manual/fn_tipo_indirizzo_ammesso_per_ruolo.md" %}
# ⚙️ Funzione `fn_tipo_indirizzo_ammesso_per_ruolo`

```sql
CREATE FUNCTION fn_tipo_indirizzo_ammesso_per_ruolo(p_tipo_ruolo_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(p_tipo_ruolo_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ((p_tipo_ruolo_id IS NULL) OR (NOT (EXISTS ( SELECT 1
            FROM config.tipi_ruolo_tipi_indirizzo m
           WHERE (m.tipo_ruolo_id = fn_tipo_indirizzo_ammesso_per_ruolo.p_tipo_ruolo_id)))) OR (EXISTS ( SELECT 1
            FROM config.tipi_ruolo_tipi_indirizzo m
           WHERE ((m.tipo_ruolo_id = fn_tipo_indirizzo_ammesso_per_ruolo.p_tipo_ruolo_id) AND (m.tipo_indirizzo_id = fn_tipo_indirizzo_ammesso_per_ruolo.p_tipo_indirizzo_id) AND m.attivo AND ((m.valido_dal IS NULL) OR (m.valido_dal <= fn_tipo_indirizzo_ammesso_per_ruolo.p_oggi)) AND ((m.valido_al IS NULL) OR (m.valido_al >= fn_tipo_indirizzo_ammesso_per_ruolo.p_oggi))))));
END

COMMENT ON FUNCTION anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(p_tipo_ruolo_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
IS 'Il tipo di ruolo ammette il tipo di indirizzo, secondo config.tipi_ruolo_tipi_indirizzo: vero se il tipo di ruolo e'' NULL o non ha nessuna riga di matrice (fallback permissivo: indirizzi liberi), altrimenti solo se c''e'' una riga per la coppia attiva e valida il giorno passato. Il giorno lo passa il chiamante. Sede unica del predicato sul layer RUOLO: la leggono anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo (quando si scrive un indirizzo del ruolo), anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto e anagrafiche.fn_crea_indirizzi_ruolo (gli obbligatori da copiare). Gemella di anagrafiche.fn_tipo_indirizzo_ammesso_per_natura, che giudica il layer SOGGETTO su un''altra matrice.';
```

</div>

---
{% include-markdown "signature-core.md" %}
