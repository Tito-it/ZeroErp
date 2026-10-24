{% include-markdown "it/dbzero/vendite/manual/trgfn_guard_fatturazione_immediata_immutabile.md" %}
# ⚙️ Funzione `trgfn_guard_fatturazione_immediata_immutabile`

```sql
CREATE FUNCTION trgfn_guard_fatturazione_immediata_immutabile()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedire il cambio del flag di instradamento corsia su un
--        documento gia' inviato in commessa, dove sarebbe inerte.
-- Uso:   BEFORE UPDATE OF fatturazione_immediata FOR EACH ROW
--        WHEN (NEW.fatturazione_immediata IS DISTINCT FROM
--              OLD.fatturazione_immediata)
--        EXECUTE FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile('<CODICE_INTERNO_SORGENTE>')
-- brief-db-emissione-fattura-per-documento-sorgente PARTE B, D-7.
DECLARE
    v_sorgente_codice  config.sorgenti.codice_interno%TYPE;
    v_sorgente_tipo_id vendite.commesse_sorgenti.sorgente_tipo_id%TYPE;
    v_key_selector     config.sorgenti.key_selector%TYPE;
    v_chiave           vendite.commesse_sorgenti.sorgente_uid%TYPE;
    v_commessa_id      vendite.commesse_sorgenti.commessa_id%TYPE;
BEGIN
    -- Guard di configurazione del trigger: l'argomento e'
    -- obbligatorio (senza, il guard sarebbe un no-op silenzioso).
    IF TG_NARGS < 1 OR btrim(COALESCE(TG_ARGV[0], '')) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'TG_ARGV[0]', 'tabella', TG_TABLE_NAME),
            NULL::uuid,
            'TG_ARGV[0] (codice_interno sorgente) obbligatorio'
        );
    END IF;

    v_sorgente_codice := btrim(TG_ARGV[0]);

    -- Sorgente per codice_interno (immutabile), MAI per codice
    -- (mutabile) — linee-guida-sql §6c/§6d.
    -- NB: nessun filtro su attivo. Il legame documento->commessa
    -- esiste anche se la sorgente venisse disattivata, e il guard
    -- deve continuare a proteggerlo.
    SELECT s.id, s.key_selector
      INTO v_sorgente_tipo_id, v_key_selector
      FROM config.sorgenti s
     WHERE s.codice_interno = v_sorgente_codice
     LIMIT 1;

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_CODICE',
            jsonb_build_object('codice', v_sorgente_codice, 'tabella', TG_TABLE_NAME),
            NULL::uuid, v_sorgente_codice, 'config.sorgenti'
        );
    END IF;

    -- Chiave CANONICA secondo key_selector, la stessa forma che
    -- fn_link_commessa_sorgente normalizza in scrittura:
    --   'uid' -> uuid::text   (preventivi, offerte)
    --   'id'  -> id::text     (ordini, contratti, DDT, ...)
    -- Non si deduce dal valore passato dal push (che e' sempre
    -- l'uid): la normalizzazione sta dentro la fn di link.
    v_chiave := CASE v_key_selector
                    WHEN 'uid' THEN NEW.uid::text
                    WHEN 'id'  THEN NEW.id::text
                END;

    IF v_chiave IS NULL THEN
        -- key_selector fuori dominio: fail-loud, non silenzio.
        -- Un guard che non risolve la chiave e' un guard che non
        -- protegge, e non deve poter passare inosservato.
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_SORG_CONF',
            jsonb_build_object('sorgente', v_sorgente_codice,
                               'key_selector', COALESCE(v_key_selector, '<NULL>'),
                               'tabella', TG_TABLE_NAME),
            NULL::uuid,
            concat('key_selector non gestito: ', COALESCE(v_key_selector, '<NULL>'))
        );
    END IF;

    -- Il documento sta in una commessa APERTA?
    -- ⭐ rev 2026-10-12 (20261012-47, brief-db-annullo-a-valle-riapre-a-
    --   monte D-14 di Tid): solo una commessa aperta blocca il flag. Dal
    --   20261012-43 il link resta come storia dopo la chiusura e l'annullo
    --   della commessa: un documento la cui commessa e' stata annullata torna
    --   da mandare, e il suo flag di corsia torna una scelta da fare. La
    --   domanda «quale commessa aperta» ha una sede sola, il building block
    --   (prima: qualunque link, con un LIMIT 1).
    v_commessa_id := vendite.fn_commessa_viva_di_sorgente(v_sorgente_tipo_id, v_chiave);

    IF v_commessa_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_guard_fatturazione_immediata_immutabile',
            'E_FATT_IMMEDIATA_NON_MODIFICABILE',
            jsonb_build_object(
                'tabella',       TG_TABLE_NAME,
                'documento_id',  NEW.id,
                'documento_uid', NEW.uid,
                'chiave_canonica', v_chiave,
                'sorgente',      v_sorgente_codice,
                'commessa_id',   v_commessa_id,
                'valore_attuale', OLD.fatturazione_immediata,
                'valore_richiesto', NEW.fatturazione_immediata
            ),
            NULL::uuid,
            v_chiave, v_sorgente_codice
        );
    END IF;

    RETURN NEW;
END;

$function$

COMMENT ON FUNCTION vendite.trgfn_guard_fatturazione_immediata_immutabile()
IS 'Guard generico (BEFORE UPDATE OF fatturazione_immediata): blocca il cambio del flag di instradamento corsia su un documento che sta in una commessa APERTA. Sorgente passata come codice_interno in TG_ARGV[0]. La chiave e'' quella CANONICA secondo config.sorgenti.key_selector (''uid'' -> uid::text, ''id'' -> id::text), la forma che vendite.fn_link_commessa_sorgente normalizza in scrittura, non quella che il push passa (sempre l''uid): dedurla dal chiamante produrrebbe un guard che non trova mai il link. Vedi guida /guide/sorgente-polimorfa §2 e §4. Finche'' il documento e'' in una commessa aperta il flag e'' inerte: e'' nella chiave di dedup di fn_get_or_create_commessa, e si sposterebbe l''intera commessa multi-sorgente. Il caso «cambio idea dopo» e'' coperto dall''emissione mirata per gruppo fatturabile. Errore: E_FATT_IMMEDIATA_NON_MODIFICABILE. brief-db-emissione-fattura-per-documento-sorgente PARTE B / D-7, rev 2026-07-27. ⭐ rev 2026-10-12 (20261012-47, brief-db-annullo-a-valle-riapre-a-monte D-14 di Tid): conta solo una commessa APERTA (vendite.fn_commessa_viva_di_sorgente). Il link resta come storia dopo la chiusura o l''annullo della commessa (20261012-43): il documento non e'' piu'' legato a una commessa per sempre, e quando la sua commessa e'' annullata torna da mandare con il flag di nuovo modificabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
