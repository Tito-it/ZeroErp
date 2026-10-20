# ⚙️ Funzione `fn_get_permessi_ereditati_azioni`

```sql
CREATE FUNCTION fn_get_permessi_ereditati_azioni(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_permessi_ereditati_azioni(p_auth_user_id integer)
 RETURNS TABLE(azione_id integer, abilitata boolean, profilo_accesso_id integer, profilo_tipo config.tipo_profilo_accesso, profilo_descrizione text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT DISTINCT ON (paz.azione_id) paz.azione_id,
     paz.abilitata,
     pa.id,
     pa.tipo,
     pa.descrizione
    FROM ((script.fn_get_profili_accesso_applicabili(fn_get_permessi_ereditati_azioni.p_auth_user_id, 'OPERATORE'::config.ruolo_applicativo) h(profilo_accesso_id, priorita)
      JOIN config.profili_accesso_azioni paz ON ((paz.profilo_accesso_id = h.profilo_accesso_id)))
      JOIN config.profili_accesso pa ON ((pa.id = h.profilo_accesso_id)))
   ORDER BY paz.azione_id, h.priorita;
END

COMMENT ON FUNCTION script.fn_get_permessi_ereditati_azioni(p_auth_user_id integer)
IS 'L''ereditato delle azioni di processo di un operatore: per ogni azione coperta da almeno un profilo della veste OPERATORE, l''abilitazione del profilo di priorita'' piu'' bassa (AD_HOC 1, REPARTO 2, PORTALE 3) e il profilo che la da'' (id, tipo, descrizione). Azione assente = nessun profilo la copre: vale negata, e lo decide il chiamante. Niente override, niente super admin. Sede UNICA del passo 4 di script.fn_check_azione_processo e script.fn_get_user_actions_map (che la chiamano) e delle azioni «ereditate» del pannello permessi (backend). Gemella di script.fn_get_permessi_ereditati_aree. BEGIN ATOMIC, INVOKER, STABLE. Brief: brief-db-pgtap-permessi-ereditati (D-1, D-2, D-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
