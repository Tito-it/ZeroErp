{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_ritira_commessa_attivita.md" %}
# ⚙️ Funzione `trgfn_doc_ritira_commessa_attivita`

```sql
CREATE FUNCTION trgfn_doc_ritira_commessa_attivita()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_ritira_commessa_attivita()
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
    v_etichetta        text;
    v_ritirate         integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   IL MOTORE del ritiro: quando un documento entra in uno
    --   stato ABORTITO, riprende le righe di commessa che aveva
    --   spinto e che nessuno ha ancora emesso.
    --
    -- ⭐ Trigger e non chiamata nei servizi (Q-10): lo stato di
    --   una testata si cambia da molti posti, e ne basta UNO
    --   distratto perche' il buco torni. E' lo stesso argomento
    --   del difetto di L1 — la regola viveva come disciplina
    --   dentro una funzione, ed e' saltata senza un errore.
    --
    -- ⛔ Le righe EMESSA non arrivano qui: le ferma il guard
    --   _a10_ (trgfn_doc_guard_chiusura_sorgente) impedendo la
    --   chiusura. La primitiva comunque non le toccherebbe.
    -- ⚠️ Le SOURCELESS (ONERE, RETTIFICA) non sono raggiungibili
    --   dal ritiro per sorgente, ed e' corretto.
    -- =========================================================
    v_stato_new := (to_jsonb(NEW) ->> v_colonna_stato)::bigint;
    v_stato_old := (to_jsonb(OLD) ->> v_colonna_stato)::bigint;

    IF v_stato_new IS NOT DISTINCT FROM v_stato_old THEN
        RETURN NULL;
    END IF;

    -- ⭐ `is_abortito` dal vocabolario, non 'ANNULLATO' cablato:
    --   un secondo stato abortito sara' coperto da solo.
    EXECUTE format(
        'SELECT COALESCE(bool_or(s.is_abortito) FILTER (WHERE s.id = $1), false),'
        '       COALESCE(bool_or(s.is_abortito) FILTER (WHERE s.id = $2), false)'
        '  FROM %s s WHERE s.id IN ($1, $2)', v_vocabolario)
       INTO v_chiude_new, v_chiude_old
      USING v_stato_new, v_stato_old;

    -- Solo l'INGRESSO in uno stato abortito e' una chiusura.
    IF NOT v_chiude_new OR v_chiude_old THEN
        RETURN NULL;
    END IF;

    SELECT s.id INTO v_sorgente_tipo_id
      FROM config.sorgenti s
     WHERE s.codice_interno = v_sorgente_codice;

    IF v_sorgente_tipo_id IS NULL THEN
        -- ⛔ Fail-closed: un trigger montato male deve gridare,
        --    non restare inerte. Un ritiro che non ritira e' la
        --    forma di difetto che questo cantiere chiude.
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text,
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'TG_ARGV[0]',
                               'valore',    v_sorgente_codice),
            NULL::uuid, 'TG_ARGV[0]');
    END IF;

    -- Il motivo che finira' nel registro, riga per riga. Nomina
    -- il DOCUMENTO, perche' e' la cosa che chi indaga cerchera'.
    v_etichetta := format('Ritiro automatico alla chiusura del documento di origine (%s %s)',
                          v_sorgente_codice,
                          COALESCE(to_jsonb(NEW) ->> 'numero',
                                   to_jsonb(NEW) ->> 'codice',
                                   to_jsonb(NEW) ->> 'id',
                                   '?'));

    -- ⛔ LA CHIAVE e' `uid::text` (quella di commesse_attivita),
    --    non quella di commesse_sorgenti che varia per sorgente.
    v_ritirate := vendite.fn_ritira_commessa_attivita_da_sorgente(
                      v_sorgente_tipo_id,
                      (to_jsonb(NEW) ->> 'uid'),
                      v_etichetta);

    -- ℹ️ Zero righe non e' un errore: un documento puo' non aver
    --    mai spinto niente. Il fatto che sia successo qualcosa,
    --    e cosa, vive nel registro delle righe ritirate.
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_ritira_commessa_attivita()
IS 'MOTORE generico del ritiro: quando un documento entra in uno stato ABORTITO, riprende le righe di vendite.commesse_attivita che aveva spinto e che nessuno ha ancora emesso (le porta ad ANNULLATA via vendite.fn_ritira_commessa_attivita_da_sorgente, con una riga di registro per ciascuna). ⭐ TRIGGER e non chiamata nei servizi (decisione Q-10): lo stato di una testata si cambia da MOLTI posti — funzioni DB e UPDATE diretti dal backend — e sono destinati a crescere; con la chiamata esplicita basta UNO distratto e il buco torna, silenzioso identico a quello da cui nasce questo cantiere. ⭐ E l''argomento e'' nel cantiere stesso: il difetto di L1 era nato cosi'', con la regola «prima riallinea, poi cancella» che viveva come ORDINE DEI PASSI dentro una funzione, cioe'' come disciplina — ed e'' bastata una chiave esterna nuova per farla saltare senza un errore, per quattro settimane. Il muro va nella STRUTTURA, ed e'' la stessa lezione applicata in L3a. ⭐ Secondo argomento, sul modello: la transizione di stato e'' gia'' data-driven (config.transizioni_stati_*), quindi il progetto ha gia'' deciso che «cosa puo'' diventare cosa» e'' una proprieta'' del dato e non del chiamante; il ritiro e'' la CONSEGUENZA di quella transizione, e metterlo nel chiamante lo separerebbe dalla causa. ⚠️ IL PREZZO: un trigger che annulla lavoro e'' AZIONE A DISTANZA — chi chiude l''ordine non vede che sta annullando anche righe di commessa. Si paga con il registro riga per riga, che la primitiva scrive sempre: senza, «il lavoro e'' sparito» diventerebbe indistinguibile da un difetto. ⭐ Si aggancia a is_abortito letto dal vocabolario degli stati e NON a un codice_interno cablato: un secondo stato abortito sara'' coperto da solo. Parametrizzata su (TG_ARGV[0] = codice_interno della sorgente, TG_ARGV[1] = colonna di stato, TG_ARGV[2] = tabella del vocabolario): una funzione, non quattro copie. ⚠️ Fase _z90_ e AFTER, e non e'' un dettaglio: il freno (_a10_, trgfn_doc_guard_chiusura_sorgente) e il motore restano DUE oggetti — la cosa che blocca e la cosa che agisce non si mescolano — e in BEFORE il ritiro girerebbe anche su una transizione che un guard successivo rifiuta. ⛔ Le righe EMESSA non arrivano qui: le ferma il guard impedendo la chiusura. ⚠️ Le SOURCELESS (ONERE, RETTIFICA) non sono raggiungibili dal ritiro per sorgente, ed e'' corretto: la loro via e'' fn_annulla_commessa_attivita e fn_annulla_accredito_riga_reso. ⛔ Fail-closed su un trigger montato con un codice sorgente inesistente. ℹ️ Zero righe ritirate non e'' un errore: un documento puo'' non aver mai spinto niente. Piano: brief-db-lavoro-che-non-torna-indietro, L7 / Q-10.';
```

---
{% include-markdown "signature-core.md" %}
