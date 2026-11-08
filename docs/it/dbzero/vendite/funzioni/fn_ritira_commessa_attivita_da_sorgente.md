{% include-markdown "it/dbzero/vendite/manual/fn_ritira_commessa_attivita_da_sorgente.md" %}
# ⚙️ Funzione `fn_ritira_commessa_attivita_da_sorgente`

```sql
CREATE FUNCTION fn_ritira_commessa_attivita_da_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid, p_motivo text, p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ritira_commessa_attivita_da_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid, p_motivo text, p_commessa_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivo   text;
    v_prima    jsonb;
    v_ritirate integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il documento riprende cio' che aveva spinto: porta ad
    --   ANNULLATA le sole righe di commessa NON_EMESSA della
    --   sorgente indicata, e ne lascia traccia riga per riga.
    --
    -- ⭐ rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte,
    --   D-1): p_commessa_id, in coda e DEFAULT NULL. NULL = tutte le
    --   commesse della sorgente (l'annullo del DOCUMENTO: riprende
    --   tutto cio' che ha spinto, ovunque sia). Valorizzato = le sole
    --   righe di QUELLA commessa (l'annullo della COMMESSA: una
    --   sorgente puo' avere righe vive in un'altra commessa, che non
    --   c'entra). Il filtro e' residuo: l'accesso resta dalla coppia
    --   sorgente, quindi l'«IS NULL OR» non toglie l'indice.
    --
    -- ⭐ E' l'oggetto di una promessa che il modello faceva gia'
    --   per iscritto. Il guard 4 di fn_annulla_commessa_attivita
    --   dice «per una riga da push il rimedio e' SEMPRE a monte,
    --   sul documento» — e a monte non c'era nessun rimedio.
    --   ⭐ Le due funzioni sono COMPLEMENTARI: quella rifiuta le
    --   righe CON sorgente e lavora sulle sourceless, questa
    --   lavora SOLO su quelle con sorgente.
    --
    -- ⛔ NON tocca le EMESSA: sono in volo verso una fattura. A
    --   fermare la chiusura ci pensa
    --   script.fn_check_sorgente_chiudibile, e la via d'uscita
    --   per l'operatore e' «Riporta da emettere» (L5).
    -- ⛔ NON tocca le ANNULLATA: sono uscite di proposito.
    -- ⚠️ NON raggiunge le SOURCELESS (ONERE, RETTIFICA): non
    --   hanno sorgente. E' corretto — per l'onere la via e'
    --   fn_annulla_commessa_attivita, per la rettifica
    --   fn_annulla_accredito_riga_reso.
    --
    -- ⛔ LA CHIAVE e' quella del modello: tipo + sorgente_id o
    --   sorgente_uid, con la regola d'incontro. Chi ha il
    --   documento passa il suo id e il suo uid (la colonna che il
    --   key_selector non usa e' NULL nella riga e non incontra
    --   niente). Una chiave sbagliata non solleva: ritira ZERO
    --   righe, ed e' per questo che si restituisce il conteggio.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ritira_commessa_attivita_da_sorgente',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id',
                               'valore',    p_sorgente_tipo_id),
            NULL::uuid, 'p_sorgente_tipo_id');
    END IF;

    -- Una chiave almeno; un id, se c'e', positivo.
    IF (p_sorgente_id IS NULL AND p_sorgente_uid IS NULL)
       OR p_sorgente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ritira_commessa_attivita_da_sorgente',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_id',
                               'valore',    p_sorgente_id,
                               'sorgente_uid', p_sorgente_uid),
            NULL::uuid, 'p_sorgente_id / p_sorgente_uid');
    END IF;

    IF p_commessa_id IS NOT NULL AND p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ritira_commessa_attivita_da_sorgente',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_commessa_id',
                               'valore',    p_commessa_id),
            NULL::uuid, 'p_commessa_id');
    END IF;

    -- ⚠️ Motivo obbligatorio, come per l'annullamento manuale.
    --    ANNULLATA e' IRREVERSIBILE e l'unica traccia del perche'
    --    e' l'evento di log. ⭐ Qui vale il doppio: chi chiude il
    --    documento non sta guardando la commessa, e il ritiro e'
    --    per lui un effetto a distanza.
    v_motivo := btrim(COALESCE(p_motivo, ''));
    IF v_motivo = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ritira_commessa_attivita_da_sorgente',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_motivo'),
            NULL::uuid, 'p_motivo');
    END IF;

    -- ── Lo snapshot, PRIMA di annullare ─────────────────────
    -- ⚠️ Lo stato precedente e' cio' che il registro deve
    --    raccontare, e l'UPDATE lo sovrascrive: si fotografa
    --    finche' esiste. Stessa disciplina del riordino di L1 —
    --    si legge il dato finche' e' vivo.
    -- ⚠️ FOR UPDATE serializza i concorrenti; ORDER BY id evita
    --    il deadlock fra due chiusure che si intersecano.
    PERFORM 1
       FROM vendite.commesse_attivita ca
      WHERE ca.sorgente_tipo_id = p_sorgente_tipo_id
        AND (ca.sorgente_id = p_sorgente_id OR ca.sorgente_uid = p_sorgente_uid)
        AND ca.stato_emissione  = 'NON_EMESSA'
        -- rev 2026-10-12: limitato a una commessa, se chiesto (vedi la
        -- testa). Filtro residuo: l'accesso resta dalla sorgente.
        AND (p_commessa_id IS NULL OR ca.commessa_id = p_commessa_id)
      ORDER BY ca.id
        FOR UPDATE;

    SELECT jsonb_agg(jsonb_build_object(
               'commessa_attivita_id', ca.id,
               'commessa_id',          ca.commessa_id,
               'segment_key',          ca.segment_key,
               'prezzo_snapshot',      ca.prezzo_snapshot,
               'tipo_movimento',       ca.tipo_movimento,
               'stato_precedente',     ca.stato_emissione)
               ORDER BY ca.id)
      INTO v_prima
      FROM vendite.commesse_attivita ca
     WHERE ca.sorgente_tipo_id = p_sorgente_tipo_id
       AND (ca.sorgente_id = p_sorgente_id OR ca.sorgente_uid = p_sorgente_uid)
       AND ca.stato_emissione  = 'NON_EMESSA'
       -- rev 2026-10-12: limitato a una commessa, se chiesto (vedi la
       -- testa). Filtro residuo: l'accesso resta dalla sorgente.
       AND (p_commessa_id IS NULL OR ca.commessa_id = p_commessa_id);

    -- ── Il ritiro ───────────────────────────────────────────
    -- Solo NON_EMESSA. Il predicato e' scritto in positivo e non
    -- come «<> EMESSA»: se domani il CHECK ammettesse un quarto
    -- stato, il default resta il NON toccarlo (fail-closed su un
    -- verbo irreversibile).
    -- stato_approvazione resta com'e': sono due assi distinti, e
    -- una riga ritirata conserva la memoria di essere stata
    -- approvata. data_update/user_update/tx_id/storico li mettono
    -- i trigger della tabella.
    UPDATE vendite.commesse_attivita ca
       SET stato_emissione = 'ANNULLATA'
     WHERE ca.sorgente_tipo_id = p_sorgente_tipo_id
       AND (ca.sorgente_id = p_sorgente_id OR ca.sorgente_uid = p_sorgente_uid)
       AND ca.stato_emissione  = 'NON_EMESSA'
       -- rev 2026-10-12: limitato a una commessa, se chiesto (vedi la
       -- testa). Filtro residuo: l'accesso resta dalla sorgente.
       AND (p_commessa_id IS NULL OR ca.commessa_id = p_commessa_id);
    GET DIAGNOSTICS v_ritirate = ROW_COUNT;

    -- ── La traccia, riga per riga ───────────────────────────
    -- ⛔ Un ritiro e' una CASCATA SILENZIOSA: chi chiude il
    --    documento non vede che sta annullando anche righe di
    --    commessa. Si paga con il registro, altrimenti «il lavoro
    --    e' sparito» diventa indistinguibile da un difetto — che
    --    e' il male da cui nasce questo cantiere.
    -- ℹ️ La colonna `evento` non ha CHECK ne' vocabolario:
    --    nessun seed da estendere.
    INSERT INTO vendite.commesse_attivita_log
                (commessa_attivita_id, evento, dettaglio)
    SELECT (e ->> 'commessa_attivita_id')::bigint,
           'RIGA_RITIRATA_DA_SORGENTE',
           jsonb_build_object(
               'motivo',             v_motivo,
               'sorgente_tipo_id',   p_sorgente_tipo_id,
               'sorgente_id',        p_sorgente_id,
               'sorgente_uid',       p_sorgente_uid,
               'stato_precedente',   e -> 'stato_precedente',
               'segment_key',        e -> 'segment_key',
               'prezzo_snapshot',    e -> 'prezzo_snapshot',
               'tipo_movimento',     e -> 'tipo_movimento',
               'commessa_id',        e -> 'commessa_id')
      FROM jsonb_array_elements(COALESCE(v_prima, '[]'::jsonb)) AS e;

    RETURN v_ritirate;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ritira_commessa_attivita_da_sorgente(p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid, p_motivo text, p_commessa_id bigint)
IS 'Il ritiro: il documento riprende cio'' che aveva spinto in commessa. Porta ad ANNULLATA le sole righe di vendite.commesse_attivita in NON_EMESSA che vengono dal documento indicato, e scrive una riga di vendite.commesse_attivita_log (evento RIGA_RITIRATA_DA_SORGENTE) per ciascuna. Restituisce quante ne ha ritirate. Il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid) e si cerca con la regola d''incontro (sorgente_id = p_sorgente_id OR sorgente_uid = p_sorgente_uid): chi ha il documento passa il suo id e il suo uid. Una chiave sbagliata non solleva: ritira zero righe, e il conteggio lo dice. p_commessa_id NULL = tutte le commesse del documento (l''annullo del documento); valorizzato = le sole righe di quella commessa (l''annullo della commessa, vendite.fn_documento_ritira_legami). Non tocca le righe EMESSA (in volo verso una fattura: la chiusura la ferma script.fn_check_sorgente_chiudibile, e la via d''uscita e'' «Riporta da emettere»), ne'' le ANNULLATA, ne'' le righe senza documento (ONERE, RETTIFICA: per loro ci sono vendite.fn_annulla_commessa_attivita e vendite.fn_annulla_accredito_riga_reso), complementare a vendite.fn_annulla_commessa_attivita, che lavora solo su quelle. Il motivo e'' obbligatorio: ANNULLATA e'' irreversibile, e l''evento di log e'' l''unica traccia del perche''. Il predicato e'' in positivo (= NON_EMESSA): uno stato nuovo resta non toccato. Solleva E_RITIRO_SORGENTE_PARAMETRO_MANCANTE su tipo, chiave, motivo o commessa mancanti o <= 0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
