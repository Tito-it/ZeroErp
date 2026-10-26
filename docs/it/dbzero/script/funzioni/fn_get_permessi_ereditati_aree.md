# ⚙️ Funzione `fn_get_permessi_ereditati_aree`

```sql
CREATE FUNCTION fn_get_permessi_ereditati_aree(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_permessi_ereditati_aree(p_auth_user_id integer)
 RETURNS TABLE(area_id integer, livello config.livello_accesso, profilo_accesso_id integer, profilo_tipo config.tipo_profilo_accesso, profilo_descrizione text)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT DISTINCT ON (paa.area_id) paa.area_id,
     paa.livello,
     pa.id,
     pa.tipo,
     pa.descrizione
    FROM ((script.fn_get_profili_accesso_applicabili(fn_get_permessi_ereditati_aree.p_auth_user_id, 'OPERATORE'::config.ruolo_applicativo) h(profilo_accesso_id, priorita)
      JOIN config.profili_accesso_aree paa ON ((paa.profilo_accesso_id = h.profilo_accesso_id)))
      JOIN config.profili_accesso pa ON ((pa.id = h.profilo_accesso_id)))
   ORDER BY paa.area_id, h.priorita;
END

COMMENT ON FUNCTION script.fn_get_permessi_ereditati_aree(p_auth_user_id integer)
IS 'L''ereditato dei permessi di area di un operatore: per ogni area coperta da almeno un profilo della veste OPERATORE, il livello del profilo di priorita'' piu'' bassa (AD_HOC 1, REPARTO 2, PORTALE 3) e il profilo che lo da'' (id, tipo, descrizione). Area assente = nessun profilo la copre: vale BLOCCATO, e lo decide il chiamante. Niente override, niente super admin: e'' cio'' che l''operatore avrebbe dal solo profilo. Sede UNICA del passo 4 di script.fn_resolve_livello_area e script.fn_get_user_permissions_map (che la chiamano) e della colonna «ereditato» del pannello permessi (backend). Lo spareggio e'' determinato: sotto una veste ogni priorita'' ha al massimo un profilo (indici unici dei binding, di risorse_umane e di identita_digitali). BEGIN ATOMIC, INVOKER, STABLE. Brief: brief-db-pgtap-permessi-ereditati (D-1, D-2, D-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
