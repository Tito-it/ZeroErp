{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5.md" %}
# ⚙️ Funzione `trgfn_listini_righe_comp_guard_immutabilita_v5`

```sql
CREATE FUNCTION trgfn_listini_righe_comp_guard_immutabilita_v5()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INS/UPD/DEL su listini_righe_componenti: i prezzi dei
--   componenti si scrivono solo in bozza, come le righe
--   (script.fn_check_listino_riga_scrivibile, la stessa che dice la
--   superficie della versione). Eccezione: la porta della chiusura del
--   legame (GUC zeroerp.legame_distinta_chiudi = id del legame, col
--   proprietario della tabella) accorcia la sola valido_al.
--   Il periodo si legge da valido_dal/valido_al: validita e' STORED
--   generated, non visibile nei BEFORE trigger.
DECLARE
    v_porta    text := COALESCE(current_setting('zeroerp.legame_distinta_chiudi', true), '');
    -- Nomi di colonna della tabella: la chiusura del legame cambia la
    --   sola valido_al; validita e' generata, le altre tre le scrivono
    --   i trigger generati.
    v_chiusura text[] := ARRAY['valido_al', 'validita', 'data_update', 'user_update', 'tx_id'];
BEGIN
    -- La porta della chiusura del legame: solo la fine, solo piu'
    -- corta, solo per il legame della riga, solo dal verbo.
    IF TG_OP = 'UPDATE'
       AND v_porta = OLD.articolo_componente_id::text
       AND script.fn_is_proprietario_tabella(TG_RELID)
       AND (to_jsonb(NEW) - v_chiusura) = (to_jsonb(OLD) - v_chiusura)
       AND NEW.valido_al IS NOT NULL
       AND NEW.valido_al < COALESCE(OLD.valido_al, 'infinity'::date)
    THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        script.fn_check_listino_riga_scrivibile(
            CASE WHEN TG_OP = 'INSERT' THEN NEW.listino_versione_id ELSE OLD.listino_versione_id END,
            CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.id END,
            TG_OP),
        NULL,
        CASE WHEN TG_OP = 'INSERT' THEN NEW.tx_id ELSE OLD.tx_id END,
        jsonb_build_object('operazione', TG_OP, 'tabella', 'listini_righe_componenti'));

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()
IS 'Trigger BEFORE INS/UPD/DEL su vendite.listini_righe_componenti: i prezzi bundle si scrivono solo in bozza, lo stato iniziale del vocabolario config.stati_doc_listino_versioni, come le righe. Solleva il primo motivo di script.fn_check_listino_riga_scrivibile, la regola che dice anche la superficie vendite.vw_listini_versioni_azioni (prezzi_bundle_blocco_*): CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, fuori dalla bozza E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA, per ogni colonna, attivo compreso (disattivare un prezzo bundle cambia il prezzo che il resolver risolve). Una bozza si elimina con le sue righe da vendite.fn_elimina_versione_listino. Una sola eccezione, la chiusura del legame di distinta: con la GUC transazionale zeroerp.legame_distinta_chiudi = id del legame della riga (articolo_componente_id) e il proprietario della tabella (script.fn_is_proprietario_tabella), la riga accorcia la sola valido_al (non NULL, prima della fine di adesso) e il resto resta fermo. La porta l''apre solo il verbo catalogo.fn_chiudi_legame_distinta (SECURITY DEFINER), che chiede il permesso e la conferma: il prezzo sta dentro il periodo del legame (FK temporale fk_listrighe_comp_articoli_comp_temporal) e chiudendo il legame si chiude anche lui. E'' il verbo dell''azione PREZZI_BUNDLE_LISTINO nel registro config.azioni_riga: i prezzi bundle si scrivono direttamente, e chi rifiuta e'' questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
