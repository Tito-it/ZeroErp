{% include-markdown "it/dbzero/script/manual/fn_veste_di_sistema.md" %}
# ⚙️ Funzione `fn_veste_di_sistema`

```sql
CREATE FUNCTION fn_veste_di_sistema(p_ruolo_applicativo config.ruolo_applicativo, p_tecnica boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_veste_di_sistema(p_ruolo_applicativo config.ruolo_applicativo, p_tecnica boolean)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
BEGIN ATOMIC
 SELECT ((p_ruolo_applicativo = 'API_CLIENT'::config.ruolo_applicativo) OR p_tecnica);
END

COMMENT ON FUNCTION script.fn_veste_di_sistema(p_ruolo_applicativo config.ruolo_applicativo, p_tecnica boolean)
IS 'Una veste e'' di una MACCHINA? true se e'' API_CLIENT (un sistema terzo) o porta il flag tecnica (l''utente tecnico di un processo automatico, script.fn_crea_utente_tecnico); la persona e'' il complemento. Pura sui valori, IMMUTABLE: la leggono script.fn_categoria_accesso, il guard anagrafiche.trgfn_identita_digitali_guard_natura_credenziale e il presidio dbops.vw_credenziali_da_sanare, sede unica del predicato. Brief: brief-db-be-fe-area-accessi (R-DB-A1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
