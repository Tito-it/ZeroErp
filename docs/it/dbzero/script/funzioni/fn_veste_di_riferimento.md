{% include-markdown "it/dbzero/script/manual/fn_veste_di_riferimento.md" %}
# ⚙️ Funzione `fn_veste_di_riferimento`

```sql
CREATE FUNCTION fn_veste_di_riferimento(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_veste_di_riferimento(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
 RETURNS bigint
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT idg.id
    FROM anagrafiche.identita_digitali idg
   WHERE ((idg.auth_user_id = fn_veste_di_riferimento.p_auth_user_id) AND (idg.ruolo_applicativo = fn_veste_di_riferimento.p_ruolo_applicativo))
   ORDER BY idg.attivo DESC, idg.data_insert DESC, idg.id DESC
  LIMIT 1;
END

COMMENT ON FUNCTION script.fn_veste_di_riferimento(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Fra le vesti di un tipo che una credenziale porta, quella che si guarda: l''accesa (al piu'' una, gli indici unici valgono WHERE attivo), altrimenti la spenta piu'' recente (data_insert, poi id). Ritorna l''id della veste, NULL se non ce n''e''. Building block (regola del 2): la leggono script.fn_get_user_profile e script.fn_get_operatore_detail. Nasce con R-DB-1: da li'' la veste OPERATORE spenta resta OPERATORE, e un JOIN nudo sul tipo prenderebbe la spenta accanto all''accesa. Brief: brief-db-be-fe-area-accessi (R-DB-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
