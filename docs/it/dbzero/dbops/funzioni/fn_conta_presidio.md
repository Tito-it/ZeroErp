{% include-markdown "it/dbzero/dbops/manual/fn_conta_presidio.md" %}
# ⚙️ Funzione `fn_conta_presidio`

```sql
CREATE FUNCTION fn_conta_presidio(p_vista text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_conta_presidio(p_vista text)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_riga     dbops.presidi%ROWTYPE;
    v_schema   text;
    v_relname  text;
    v_sql      text;
    v_conta    bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Contare le righe che CHIEDONO UN INTERVENTO su una vista
    --   di presidio, attraversando la row level security dove
    --   serve, e senza mai restituire le righe.
    --
    -- ⛔ Il perimetro e' il CATALOGO: una vista non dichiarata
    --   non si conta. Non e' prudenza — e' cio' che impedisce a
    --   questa funzione di diventare una porta per leggere il
    --   conteggio di qualunque relazione del database aggirando
    --   la row level security.
    -- =========================================================

    -- ⚠️ Il NULL cade nello stesso ramo del nome sconosciuto, ed
    --   e' voluto: `vista = NULL` non trova niente, quindi un
    --   rifiuto a parte direbbe la stessa cosa in un punto in
    --   piu'. UN SOLO SITO CHE SOLLEVA.
    SELECT * INTO v_riga
      FROM dbops.presidi
     WHERE vista = p_vista
       AND attivo
       AND obsoleto_dal IS NULL;

    -- ⚠️ SELECT INTO senza righe NON solleva: lascia il record a
    --   NULL. Il controllo va scritto, o si prosegue su un
    --   catalogo che non ha risposto.
    IF NOT FOUND THEN
        -- ⛔ Nel VARIADIC va il NOME DELLA VISTA CHIESTA — la
        --   cosa che una persona riconosce — mai `p_vista`, che
        --   e' il nome del parametro e produrrebbe un messaggio
        --   di qualita' E_GENERICO passando tutti i cancelli.
        --   Il ripiego serve al caso NULL: un `%s` vuoto e' una
        --   frase che non dice niente.
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'fn_conta_presidio',
            'E_PRESIDIO_NON_A_CATALOGO',
            jsonb_build_object('vista', p_vista),
            NULL::uuid,
            coalesce(nullif(btrim(p_vista), ''), '(nessuna vista indicata)'));
    END IF;

    v_schema  := split_part(v_riga.vista, '.', 1);
    v_relname := split_part(v_riga.vista, '.', 2);

    -- ⛔ SQL dinamico con %I, mai per concatenazione: il nome
    --   viene da una tabella, e una tabella si scrive.
    IF v_riga.colonna_stato IS NULL THEN
        v_sql := format('SELECT count(*) FROM %I.%I',
                        v_schema, v_relname);
        EXECUTE v_sql INTO v_conta;
    ELSE
        -- ⭐ Il filtro NON e' un dettaglio: su quattro viste
        --   l'invariante scritto nel COMMENT e' «nessuna riga
        --   NON_DICHIARATO», non «la vista e' vuota». Contare
        --   tutto suonerebbe su un debito gia' dichiarato, e un
        --   digest che suona su cio' che e' gia' deciso viene
        --   ignorato al secondo invio.
        --
        -- ⛔ E si conta «DIVERSO DALLO STATO ATTESO», non «uguale
        --   a uno degli stati di allarme»: uno stato NUOVO
        --   aggiunto domani alla vista cade cosi' nell'allarme
        --   invece che nel silenzio. Il verso opposto e' quello
        --   in cui un presidio si spegne da solo.
        -- ⚠️ IS DISTINCT FROM e non <>: un NULL nella colonna di
        --   stato e' «non atteso», e con <> il confronto darebbe
        --   NULL, cioe' la riga uscirebbe dal conteggio in
        --   silenzio.
        v_sql := format(
            'SELECT count(*) FROM %I.%I WHERE %I IS DISTINCT FROM $1',
            v_schema, v_relname, v_riga.colonna_stato);
        EXECUTE v_sql INTO v_conta USING v_riga.stato_atteso;
    END IF;

    RETURN v_conta;
END
$function$

COMMENT ON FUNCTION dbops.fn_conta_presidio(p_vista text)
IS 'Conta le righe che CHIEDONO UN INTERVENTO su una vista di presidio dichiarata in dbops.presidi, applicando il filtro (colonna_stato, stato_atteso) letto dal catalogo. ⭐ SECURITY DEFINER del PROPRIETARIO, non di un superuser: tre viste sono security_invoker su tabelle in row level security, e da un percorso senza le GUC di sessione — un management command — tornerebbero ZERO per cecita''. Su una vista di natura ZERO «zero righe» e «non ho potuto vedere» si scrivono uguale, quindi il digest riporterebbe «tutto a posto» proprio perche'' e'' cieco. La row level security e'' ENABLE senza FORCE, quindi l''owner la attraversa: e'' lo stesso meccanismo di config.fn_accoda_email_sistema. ⛔ Torna un bigint e MAI le righe: attraversa i perimetri per dire QUANTI, non QUALI, cosi'' in una email non finisce niente fuori scope. ⛔ E il perimetro e'' il catalogo: una vista non dichiarata non si conta — sa contare solo cio'' che e'' a catalogo, ed e'' tutto il suo valore. ⚠️ Il conteggio passa da qui per TUTTE le viste, non solo per le tre: la colonna dbops.presidi.perimetro dice un''altra cosa, cioe'' se il chiamante puo'' anche ELENCARE le righe. Brief: brief-db-un-destinatario-per-i-presidi §4.1.';
```

---
{% include-markdown "signature-core.md" %}
