{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_transizione`

```sql
CREATE FUNCTION trgfn_ddt_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato DDT.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_ddt.
--   Letto dalla matrice (no grafo hardcodato). Mirror del guard
--   ordini (trgfn_ordini_guard_transizione).
--   rev 2026-07-19: la Regola 2 (righe) delega a
--   script.fn_check_ddt_emittibile — single source con la capability.
DECLARE
    v_codice_da config.stati_doc_ddt.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ddt.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_guc          text;
    v_dentro_verbo boolean;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ddt_id IS NOT DISTINCT FROM OLD.stato_doc_ddt_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ddt_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ddt_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_ddt
     WHERE id IN (OLD.stato_doc_ddt_id, NEW.stato_doc_ddt_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_ddt t
         WHERE t.stato_da_id = OLD.stato_doc_ddt_id
           AND t.stato_a_id  = NEW.stato_doc_ddt_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_DDT_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'stato_da', v_codice_da,
                'stato_a',  v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: DRAFT->EMESSO richiede almeno una riga attiva.
    -- Zero righe = niente da trasportare. Il "DDT solo trasporto"
    -- resta possibile: e' righe senza prezzo, non zero righe.
    -- Verdetto dalla single source (fn_check_ddt_emittibile).
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'EMESSO'
       AND script.fn_check_ddt_emittibile(NEW)
           @> '[{"codice": "E_DDT_EMISSIONE_SENZA_RIGHE"}]'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_DDT_EMISSIONE_SENZA_RIGHE',
            jsonb_build_object(
                'ddt_id', NEW.id,
                'numero', NEW.numero
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(NEW.numero, 'NULL')
        );
    END IF;

    -- Regola 3 — LA PORTA DEL REGISTRO (rev 2026-09-28,
    --   brief-db-magazzino-lotto-3-scarico-da-ddt, D-L3-e affinata da Tid).
    --   I passaggi che toccano il registro di magazzino — l'emissione, l'annullo
    --   di una bolla emessa, la consegna di una bolla di trasferimento — di una
    --   bolla che muove merce davvero (vendite.fn_ddt_muove_merce, sulla riga
    --   NUOVA: causale e magazzino possono cambiare nello stesso UPDATE) si fanno
    --   solo dal verbo vendite.fn_cambia_stato_ddt, che nella stessa transazione
    --   scrive i movimenti. Due condizioni, come la porta POSTED dei documenti
    --   interni (D-V1): la GUC transazionale porta NEW.id E chi esegue e' il
    --   proprietario della tabella (un verbo DEFINER, non l'app che accende la
    --   GUC da se').
    --   ⚠️ Sulle bolle che NON muovono merce l'UPDATE diretto resta ammesso: e' la
    --   porta del registro, non ancora quella del permesso su tutta la bolla.
    IF ((v_codice_da = 'DRAFT'  AND v_codice_a = 'EMESSO')
        OR (v_codice_da = 'EMESSO' AND v_codice_a = 'ANNULLATO')
        OR (v_codice_a = 'CONSEGNATO' AND vendite.fn_ddt_causale_magazzino(NEW) = 'TRASF_OUT'))
       AND vendite.fn_ddt_muove_merce(NEW) THEN
        v_guc          := current_setting('zeroerp.ddt_cambio_stato', true);
        v_dentro_verbo := script.fn_is_proprietario_tabella(TG_RELID);
        IF v_guc IS DISTINCT FROM NEW.id::text OR NOT v_dentro_verbo THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_DDT_STATO_SOLO_DA_VERBO',
                jsonb_build_object(
                    'ddt_id',       NEW.id,
                    'numero',       NEW.numero,
                    'stato_da',     v_codice_da,
                    'stato_a',      v_codice_a,
                    'guc_valore',   v_guc,
                    'dentro_verbo', v_dentro_verbo,
                    'db_user',      current_user
                ),
                NEW.tx_id,
                coalesce(NEW.numero, NEW.id::text),
                coalesce(v_codice_a, 'NULL')
            );
        END IF;
    END IF;

    -- Regola 4 — RITIRATA (rev 2026-10-11, D-4 di
    --   brief-db-annullo-documento-con-legami). L'avviso dell'annullo con
    --   legami vale per bolla, ordine, preventivo e contratto, e sta nel BB
    --   vendite.trgfn_doc_guard_annullo_con_legami (trg_ddt_m10_guard_annullo_
    --   con_legami_upd), che conta i legami da vendite.fn_documento_legami
    --   (anche le righe di commessa NON_EMESSA) e solleva
    --   E_DOC_ANNULLO_CON_LEGAMI. Una regola, una sede.

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato DDT letto da config.transizioni_stati_ddt (E_STATO_DDT_TRANSIZIONE_NON_VALIDA). Regola 2: DRAFT->EMESSO richiede almeno una riga attiva (E_DDT_EMISSIONE_SENZA_RIGHE) — verdetto delegato a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt). Mirror di trgfn_ordini_guard_transizione. rev 2026-07-19 (brief-db-guard-righe-avanzamento-stato Rev 2). rev 2026-09-28 (brief-db-magazzino-lotto-3-scarico-da-ddt, D-L3-e): Regola 3, la PORTA DEL REGISTRO. DRAFT->EMESSO, EMESSO->ANNULLATO e ->CONSEGNATO di una bolla di trasferimento, su una bolla che muove merce (vendite.fn_ddt_muove_merce sulla riga NUOVA), passano solo dal verbo vendite.fn_cambia_stato_ddt: GUC transazionale zeroerp.ddt_cambio_stato = NEW.id E chi esegue e'' il proprietario della tabella (script.fn_is_proprietario_tabella), altrimenti E_DDT_STATO_SOLO_DA_VERBO. Le bolle che non muovono merce restano all''UPDATE diretto. rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-8): Regola 4, L''ANNULLO CON LEGAMI CHIEDE CONFERMA. Verso ANNULLATO, una bolla che porta legami con ordini o resi (vendite.fn_ddt_legami: fulfillment e ponti di ri-consegna) e'' rifiutata con E_DDT_ANNULLO_CON_LEGAMI (CONFLITTO_STATO; valori: etichetta della bolla, numero di righe legate): e'' l''avviso, su ogni strada. L''annullo vero passa dal verbo vendite.fn_annulla_ddt, che riceve la conferma, ritira i legami (vendite.fn_ddt_riga_ritira_legami) e poi cambia lo stato: qui arriva senza legami e passa. rev 2026-10-11 (20261011-83, brief-db-annullo-documento-con-legami D-4): la Regola 4 si RITIRA. L''avviso dell''annullo con legami vale per bolla, ordine, preventivo e contratto e sta nel BB vendite.trgfn_doc_guard_annullo_con_legami (trg_ddt_m10_guard_annullo_con_legami_upd), con il codice E_DOC_ANNULLO_CON_LEGAMI; E_DDT_ANNULLO_CON_LEGAMI e vendite.fn_ddt_legami si ritirano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
