{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_guard_chiusura_sorgente.md" %}
# ⚙️ Funzione `trgfn_doc_guard_chiusura_sorgente`

```sql
CREATE FUNCTION trgfn_doc_guard_chiusura_sorgente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sorgente_codice  text := TG_ARGV[0];
    v_colonna_stato    text := TG_ARGV[1];
    v_vocabolario      text := TG_ARGV[2];
    v_sorgente_tipo_id config.sorgenti.id%TYPE;
    v_stato_new        bigint;
    v_stato_old        bigint;
    v_chiude_new       boolean := false;
    v_chiude_old       boolean := false;
    v_motivi           jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare la CHIUSURA di un documento che ha spinto in
    --   commessa righe gia' EMESSA. Quelle sono in volo verso
    --   una fattura e non si ritirano; le NON_EMESSA sono legami
    --   di consumo: le ritira il verbo di annullo dopo la conferma
    --   (BB vendite.fn_documento_ritira_legami; l'avviso e' il guard
    --   _m10_ vendite.trgfn_doc_guard_annullo_con_legami). Rev
    --   2026-10-11, brief-db-annullo-documento-con-legami D-5: il
    --   ritiro automatico e silenzioso _z90_ si e' ritirato.
    --
    -- ⭐ Generica: TG_ARGV[0] = codice_interno della sorgente,
    --   TG_ARGV[1] = colonna di stato della testata,
    --   TG_ARGV[2] = tabella del vocabolario degli stati.
    --   Quattro copie divergerebbero.
    --
    -- ⭐ Si aggancia a `is_abortito` e NON a un codice cablato:
    --   cosa significhi «chiuso» e' una proprieta' del DATO, come
    --   gia' lo e' la matrice delle transizioni. Un secondo stato
    --   abortito sara' coperto da solo.
    -- =========================================================
    v_stato_new := (to_jsonb(NEW) ->> v_colonna_stato)::bigint;
    v_stato_old := (to_jsonb(OLD) ->> v_colonna_stato)::bigint;

    -- No-op se lo stato non cambia davvero.
    IF v_stato_new IS NOT DISTINCT FROM v_stato_old THEN
        RETURN NEW;
    END IF;

    EXECUTE format(
        'SELECT COALESCE(bool_or(s.is_abortito) FILTER (WHERE s.id = $1), false),'
        '       COALESCE(bool_or(s.is_abortito) FILTER (WHERE s.id = $2), false)'
        '  FROM %s s WHERE s.id IN ($1, $2)', v_vocabolario)
       INTO v_chiude_new, v_chiude_old
      USING v_stato_new, v_stato_old;

    -- Interessa SOLO l'ingresso in uno stato abortito. Uscirne o
    -- restarci non e' una chiusura.
    IF NOT v_chiude_new OR v_chiude_old THEN
        RETURN NEW;
    END IF;

    SELECT s.id INTO v_sorgente_tipo_id
      FROM config.sorgenti s
     WHERE s.codice_interno = v_sorgente_codice;

    IF v_sorgente_tipo_id IS NULL THEN
        -- ⛔ Fail-closed su un trigger montato male: meglio un
        --    errore parlante che un freno silenziosamente inerte.
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text,
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'TG_ARGV[0]',
                               'valore',    v_sorgente_codice),
            NULL::uuid, 'TG_ARGV[0]');
    END IF;

    -- ⛔ LA CHIAVE e' quella del modello: il trigger ha il documento,
    --    e ne passa l'id e l'uid (regola d'incontro). Sbagliarla non
    --    darebbe errore, darebbe ZERO motivi.
    v_motivi := script.fn_check_sorgente_chiudibile(
                    v_sorgente_tipo_id,
                    (to_jsonb(NEW) ->> 'id')::bigint,
                    (to_jsonb(NEW) ->> 'uid')::uuid);

    -- ⭐ La coda del primo motivo sta in un posto solo: l'helper legge il
    --   codice da `v_motivi -> 0`, ne prende i `valori` per la frase, fonde il
    --   `dettaglio` nel contesto e ci mette sempre l'elenco COMPLETO dei motivi.
    -- ⚠️ L'IF e' sparito e NON e' fail-open: l'helper tace su un array vuoto,
    --   che e' esattamente la risposta «passa». Su un non-array resta rumoroso.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'database', TG_NAME::text,
        v_motivi,
        NULL,
        NULL::uuid,
        jsonb_build_object(
            'sorgente',     v_sorgente_codice,
            'sorgente_uid', (to_jsonb(NEW) ->> 'uid'),
            'documento_id', (to_jsonb(NEW) ->> 'id')));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_guard_chiusura_sorgente()
IS 'FRENO generico: rifiuta la CHIUSURA di un documento che ha spinto in commessa righe gia'' EMESSA. ⭐ E'' meta'' della regola decisa con la strada A: quando un documento si chiude, le righe NON_EMESSA il documento le RITIRA (dal 2026-10-11 dopo la conferma, nel verbo di annullo: BB vendite.fn_documento_ritira_legami) e le EMESSA lo BLOCCANO — sono in volo verso una fattura, e ritirarle lascerebbe un''attivita'' fatturabile orfana in viaggio, cioe'' il residuo che questo cantiere esiste per chiudere. ⭐ E dal lotto L5 il rifiuto ha una VIA D''USCITA che il messaggio nomina: «Riporta da emettere» riporta la riga a NON_EMESSA e da li'' il ritiro la prende; prima di L5 sarebbe stato un vicolo cieco, ed e'' esattamente cio'' che E_PREV_ANNULLA_COMMESSA_EMESSA era. ⭐ SI AGGANCIA AL DATO e non a un codice cablato: legge is_abortito dal vocabolario degli stati del documento invece di confrontare codice_interno = ANNULLATO. Tutti e quattro i vocabolari (config.stati_doc_preventivi, _ordini, _ddt, _contratti) hanno quel flag, ed e'' la stessa scelta gia'' fatta per la matrice delle transizioni: cosa significhi «chiuso» e'' una proprieta'' del dato. ⚠️ Il giorno che nasce un secondo stato abortito, questo guard lo copre da solo — con un codice cablato non l''avrebbe coperto, e in silenzio. ⭐ UNA funzione parametrizzata su (TG_ARGV[0] = codice_interno della sorgente, TG_ARGV[1] = colonna di stato, TG_ARGV[2] = tabella del vocabolario), non quattro copie: e'' l''idioma di dbops.trgfn_child_requires_active_parent. ⛔ La CHIAVE passata alla check e'' NEW.uid::text, cioe'' quella di vendite.commesse_attivita — verificata sul corpo delle cinque fn_list_*_da_pushare, che compongono tutte x.uid::text. NON e'' la chiave di vendite.commesse_sorgenti, che varia per sorgente: confonderle non darebbe un errore, darebbe ZERO motivi, cioe'' un freno che lascia passare tutto. ⛔ Fail-closed su un trigger montato con un codice sorgente inesistente: solleva invece di restare inerte. ⚠️ IL LIMITE: il conteggio gira sotto ROW SECURITY (commesse_attivita ha la RLS per emittente), quindi chi chiude un documento senza vedere le righe che ne sono nate NON viene fermato da questo freno. (Rev 2026-10-11: le righe NON_EMESSA le conta invece l''avviso dell''annullo con un lettore DEFINER, vendite.fn_documento_legami, che non subisce la RLS.) E'' il comportamento di oggi e non un peggioramento, ma qui NON c''e'' nessuna chiave esterna a fare da rete, quindi va scritto invece che dedotto; il caso resta stretto perche'' la commessa eredita l''emittente dal documento. Piano: brief-db-lavoro-che-non-torna-indietro, L7 / Q-5'' strada A. rev 2026-10-11 (20261011-89, brief-db-annullo-documento-con-legami D-5): il motore del ritiro automatico (_z90_) si ritira; le righe NON_EMESSA sono legami di consumo, l''annullo che le ha davanti chiede conferma (guard _m10_ vendite.trgfn_doc_guard_annullo_con_legami) e le ritira il verbo. Questo freno sulle EMESSA resta com''era, e parla prima dell''avviso (fascia _a10_).';
```

</div>

---
{% include-markdown "signature-core.md" %}
