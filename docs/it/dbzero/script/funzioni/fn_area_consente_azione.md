{% include-markdown "it/dbzero/script/manual/fn_area_consente_azione.md" %}
# ⚙️ Funzione `fn_area_consente_azione`

```sql
CREATE FUNCTION fn_area_consente_azione(p_livello_area config.livello_accesso, p_livello_minimo config.livello_accesso)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_area_consente_azione(p_livello_area config.livello_accesso, p_livello_minimo config.livello_accesso)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- Scopo: dire se il livello d'area di un operatore consente un'azione di
--   processo che dichiara il minimo p_livello_minimo (brief-db-permessi-tetto-area).
-- ⛔ L'enum config.livello_accesso e' ordinato TUTTO < LETTURA < BLOCCATO:
--   «arriva al minimo» e' livello <= minimo.
-- NULL da qualunque parte vale no (fail-closed).
BEGIN
    RETURN COALESCE(p_livello_area <= p_livello_minimo, false);
END;
$function$

COMMENT ON FUNCTION script.fn_area_consente_azione(p_livello_area config.livello_accesso, p_livello_minimo config.livello_accesso)
IS 'Regola pura del tetto d''area per un''azione di processo: true se il livello d''area dell''operatore arriva al minimo che l''azione dichiara (config.azioni_processo.livello_minimo_area). ⛔ L''enum livello_accesso e'' ordinato TUTTO < LETTURA < BLOCCATO: consente se livello_area <= minimo. NULL da qualunque parte -> false (fail-closed). Sede unica del confronto: la chiamano script.fn_get_permessi_effettivi_azioni (e da li'' fn_check_azione_processo, fn_get_user_actions_map e il pannello permessi) e la fixture dbops.fn_pgtap_concedi_azione. IMMUTABLE, INVOKER. Brief: brief-db-permessi-tetto-area R3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
