{% include-markdown "it/dbzero/vendite/manual/fn_reset_fondi_fattura.md" %}
# ⚙️ Funzione `fn_reset_fondi_fattura`

```sql
CREATE FUNCTION fn_reset_fondi_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
 RETURNS TABLE(deleted_source integer, deleted_fondi integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_deleted_source INTEGER := 0;
    v_deleted_fondi  INTEGER := 0;
    v_stato_contabile_chiusa_id pagamenti.vendite_contabili_stati.id%TYPE;
    -- ⚠️ Array: `colonna%TYPE[]` non esiste in PostgreSQL, quindi
    --    qui il tipo resta esplicito. Portano id di
    --    vendite.fatture_fondi_fattura_source.
    v_src_ids      bigint[];
    v_registrate   bigint[];
    v_chiuse       bigint[];
    v_resettabili  bigint[];
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    SELECT s.id INTO v_stato_contabile_chiusa_id
      FROM pagamenti.vendite_contabili_stati s WHERE s.codice_interno = 'CHIUSA' AND s.attivo IS TRUE LIMIT 1;

    IF v_stato_contabile_chiusa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_fondi_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'CHIUSA'), NULL::uuid, 'lo stato CHIUSA delle distinte contabili');
    END IF;

    -- =========================================================
    -- 1) GLI ATTI GIA' ESEGUITI: solo segnalazione.
    --    Non entrano nemmeno nel giro sotto (che filtra
    --    ASSEGNATO): qui si dicono, perche' un reset silenzioso
    --    su una fattura che aveva un fondo eseguito lascerebbe
    --    l'operatore a chiedersi dove sia finito.
    -- =========================================================
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: il trasferimento e'' gia'' stato registrato (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_ESEGUITO_NON_RESETTABILE', 'cause', 'ATTO_ESEGUITO'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.fattura_figlia_id = p_fattura_id
       AND s.stato = 'ESEGUITO';

    -- =========================================================
    -- 2) GLI ATTI IN GIOCO, bloccati in lettura.
    --    ⚠️ FOR UPDATE OF s: si bloccano le sole righe
    --    dell'atto; le JOIN su tipi (filtro) e fatture
    --    (display) non vanno bloccate.
    -- =========================================================
    SELECT array_agg(q.id) INTO v_src_ids
      FROM (
        SELECT s.id
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.tipi_fondi_fattura t ON t.id = s.tipo_fondo_fattura_id
         WHERE s.fattura_figlia_id = p_fattura_id
           AND s.stato = 'ASSEGNATO'
           AND t.codice_interno = 'F_F_ADD_ACC'
           FOR UPDATE OF s
      ) q;

    IF v_src_ids IS NULL THEN
        RETURN QUERY SELECT 0, 0;
        RETURN;
    END IF;

    -- =========================================================
    -- 3) CHI NON SI TOCCA, e per quale delle due ragioni.
    --
    --    (a) l'anomalia: l'atto e' ASSEGNATO ma una sua riga e'
    --        gia' REGISTRATA. L'invariante vuole che in quel
    --        caso l'atto sia ESEGUITO; se non lo e', qualcosa
    --        e' andato storto e non si cancella denaro
    --        registrato per rimettere le cose a posto.
    -- =========================================================
    SELECT array_agg(DISTINCT cr.fondo_source_id) INTO v_registrate
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.fondo_source_id = ANY (v_src_ids)
       AND st.codice_interno = 'POSTATA';

    -- =========================================================
    --    (b) la riga sta in una distinta CHIUSA: il minimo non
    --        e' piu' ripristinabile.
    --    ⚠️ Qui NON si filtra `attivo`, e non e' una svista: una
    --        riga archiviata in una distinta chiusa resta un
    --        fatto, e con la FK nuova impedirebbe comunque la
    --        cancellazione dell'atto. Meglio un blocco che lo
    --        dice che una violazione di vincolo che lo scopre.
    -- =========================================================
    SELECT array_agg(DISTINCT cr.fondo_source_id) INTO v_chiuse
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili c ON c.id = cr.contabile_id
     WHERE cr.fondo_source_id = ANY (v_src_ids)
       AND c.stato_id = v_stato_contabile_chiusa_id
       AND NOT (cr.fondo_source_id = ANY (COALESCE(v_registrate, '{}'::bigint[])));

    SELECT array_agg(x) INTO v_resettabili
      FROM unnest(v_src_ids) AS x
     WHERE NOT (x = ANY (COALESCE(v_registrate, '{}'::bigint[])))
       AND NOT (x = ANY (COALESCE(v_chiuse, '{}'::bigint[])));

    -- =========================================================
    -- 4) Le segnalazioni dei bloccati, e l'annullamento dei soli
    --    bloccati da distinta chiusa.
    --    ⭐ La frase non dice piu' «gia postato»: la condizione
    --       e' che la distinta e' chiusa, cioe' il caso in cui
    --       il denaro NON e' stato registrato.
    -- =========================================================
    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Minimo non ripristinabile: la distinta contabile e'' chiusa (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_MINIMO_NON_RIPRISTINABILE', 'cause', 'CONTABILE_CHIUSA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_chiuse, '{}'::bigint[]));

    INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
    SELECT p_fattura_id, now(),
           format('Fondo non resettabile: una sua riga contabile risulta gia'' registrata (fattura %s del %s)',
                  COALESCE(fs.numero::text, 'N/D'), COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           'W', FALSE,
           jsonb_build_object('source_id', s.id, 'fattura_sorgente_id', s.fattura_sorgente_id,
                              'error_code', 'W_FONDO_ESEGUITO_NON_RESETTABILE', 'cause', 'RIGA_REGISTRATA'),
           now(), current_user, now(), current_user
      FROM vendite.fatture_fondi_fattura_source s
      JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
     WHERE s.id = ANY (COALESCE(v_registrate, '{}'::bigint[]));

    -- ⭐ La ragione dell'annullamento sta SUL DATO, non solo nel
    --    diario: chi legge la riga del fondo sa perche' e'
    --    ANNULLATO senza dover cercare in fatture_log.
    UPDATE vendite.fatture_fondi_fattura_source s
       SET stato = 'ANNULLATO',
           motivo = format('Minimo non ripristinabile: distinta contabile gia CHIUSA (fattura %s del %s)',
                           COALESCE(fs.numero::text, 'N/D'),
                           COALESCE(to_char(fs.data, 'YYYY-MM-DD'), 'N/D')),
           data_update = now(), user_update = current_user
      FROM vendite.fatture fs
     WHERE fs.id = s.fattura_sorgente_id
       AND s.id = ANY (COALESCE(v_chiuse, '{}'::bigint[]));

    -- =========================================================
    -- 5) I RESETTABILI, in tre statement e in quest'ordine.
    --    ⚠️ Prima le righe contabili: la FK verso l'atto e'
    --       NO ACTION, e cancellare l'atto con una figlia viva
    --       fallirebbe.
    --    ℹ️ Nessun filtro sulla distinta: per costruzione un
    --       resettabile non ha righe sotto una distinta CHIUSA
    --       (quelle stanno in v_chiuse). Rimetterlo qui
    --       lascerebbe una figlia viva e la FK lo direbbe con
    --       una violazione di vincolo.
    -- =========================================================
    DELETE FROM pagamenti.vendite_contabili_righe cr
     WHERE cr.fondo_source_id = ANY (COALESCE(v_resettabili, '{}'::bigint[]));

    WITH del_ff AS (
        DELETE FROM vendite.fatture_fondi_fattura ff
         USING vendite.fatture_fondi_fattura_source s
         WHERE s.id = ANY (COALESCE(v_resettabili, '{}'::bigint[]))
           AND ff.fattura_id = p_fattura_id
           AND ff.riferimento_fattura_id = s.fattura_sorgente_id
         RETURNING ff.id
    )
    SELECT COUNT(*)::INTEGER INTO v_deleted_fondi FROM del_ff;

    WITH del_src AS (
        DELETE FROM vendite.fatture_fondi_fattura_source s
         WHERE s.id = ANY (COALESCE(v_resettabili, '{}'::bigint[]))
         RETURNING s.id
    )
    SELECT COUNT(*)::INTEGER INTO v_deleted_source FROM del_src;

    RETURN QUERY SELECT COALESCE(v_deleted_source, 0), COALESCE(v_deleted_fondi, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
IS 'Reset dei fondi applicati a una fattura FIGLIA. ⭐ rev 2026-08-21 (cantiere incassi, lotto 3, passo S1-17, decisione D11): l''atto NON eseguito si CANCELLA invece di tornare DISPONIBILE, e un atto ESEGUITO non si tocca mai — si segnala nel diario e il giro prosegue. La regola in una riga: si cancella solo cio'' che non e'' stato eseguito. ⚠️ Due conseguenze accettate: la tabella non e'' storicizzata, quindi il DELETE e'' definitivo (un atto mai eseguito e'' una PROPOSTA, non un fatto); e cancellare RIAPRE la rigenerazione, perche'' l''«atto unico» di fn_fondo_fattura_proponibile guarda se un atto esiste in qualunque stato — il giro successivo ne rifa'' uno leggendo il residuo di adesso, che e'' il comportamento cercato ma e'' un cambio reale. ⚠️ Non e'' piu'' una CTE sola: la FK fk_vendite_contabili_righe_fondo_source impone di cancellare prima le righe e poi l''atto, e dentro un solo statement quell''ordine non e'' garantito rispetto ai vincoli. Tre esiti: atto ESEGUITO (o ASSEGNATO con una riga gia'' REGISTRATA, che e'' l''anomalia) -> non si tocca, W_FONDO_ESEGUITO_NON_RESETTABILE con due `cause` diverse nel meta; riga in una distinta CHIUSA -> ANNULLATO con la ragione sul dato, W_FONDO_MINIMO_NON_RIPRISTINABILE — 🔴 e la frase non dice piu'' «gia postato», che era falsa proprio nel caso in cui il denaro NON e'' stato registrato; tutto il resto -> cancellato. ⚠️ Il blocco «distinta CHIUSA» guarda anche le righe non attive: una riga archiviata in una distinta chiusa resta un fatto, e con la FK impedirebbe comunque la cancellazione dell''atto. ⚠️ E'' un''operazione TECNICA sul ciclo di vita della figlia (il ritorno di un lotto in bozza) e NON una reazione ai pagamenti: nessun incasso la chiama e nessun incasso deve chiamarla. ⚠️ La firma e'' cambiata: updated_source -> deleted_source, perche'' non si aggiorna piu'' niente (nessun consumatore: il backend non la nomina e fn_cleanup_fatture_by_ids la invoca con PERFORM). D-16 + D-5 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2, superati in parte da D11. rev 2026-08-21 precedente (liste drawer lotto, L1/P-6): le note di avviso dichiarano il loro codice in meta->>''error_code''.';
```

---
{% include-markdown "signature-core.md" %}
