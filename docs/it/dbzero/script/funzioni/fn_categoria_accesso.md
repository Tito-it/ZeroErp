{% include-markdown "it/dbzero/script/manual/fn_categoria_accesso.md" %}
# ⚙️ Funzione `fn_categoria_accesso`

```sql
CREATE FUNCTION fn_categoria_accesso(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_categoria_accesso(p_auth_user_id integer)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN bool_or(script.fn_veste_di_sistema(idg.ruolo_applicativo, idg.tecnica)) THEN 'SISTEMA'::text
             WHEN bool_or((idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)) THEN 'OPERATORE'::text
             ELSE 'ALTRO'::text
         END AS "case"
    FROM anagrafiche.identita_digitali idg
   WHERE (idg.auth_user_id = fn_categoria_accesso.p_auth_user_id);
END

COMMENT ON FUNCTION script.fn_categoria_accesso(p_auth_user_id integer)
IS 'La categoria di una CREDENZIALE, cioe'' il tab dell''area Accessi in cui sta: SISTEMA (almeno una veste di sistema, script.fn_veste_di_sistema), OPERATORE (altrimenti, almeno una veste OPERATORE), ALTRO (tutte le altre, comprese le credenziali senza alcuna veste). Contano tutte le vesti, anche spente: una persona disattivata resta nel suo tab. Un valore solo per credenziale rende la partizione dei tre tab vera per costruzione (A-2): la leggono le viste anagrafiche.vw_accessi_altri e vw_accessi_sistema e il backend. SISTEMA prima di OPERATORE non sceglie fra due casi del modello: persona e macchina sulla stessa credenziale le rifiuta il guard trgfn_identita_digitali_guard_natura_credenziale; per una riga nata prima del guard vince la sola lettura del tab Di sistema, e la segnala dbops.vw_credenziali_da_sanare. Brief: brief-db-be-fe-area-accessi (R-DB-A1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
