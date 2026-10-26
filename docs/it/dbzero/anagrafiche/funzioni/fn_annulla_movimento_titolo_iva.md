{% include-markdown "it/dbzero/anagrafiche/manual/fn_annulla_movimento_titolo_iva.md" %}
# ⚙️ Funzione `fn_annulla_movimento_titolo_iva`

```sql
CREATE FUNCTION fn_annulla_movimento_titolo_iva(p_movimento_id bigint, p_motivo character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_annulla_movimento_titolo_iva(p_movimento_id bigint, p_motivo character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: annullare una FORZATURA del registro plafond IVA
--   scrivendo il CONTRO-MOVIMENTO di segno opposto. Il registro
--   resta append-only, l'accumulatore riporta
--   imponibile_utilizzato al valore giusto da se' (somma senza
--   filtri), e a video restano entrambe le righe: l'errore, la
--   correzione, e la data di ciascuna.
--   Ritorna l'id della riga di annullo.
--   Piano: brief-db-titoli-iva-movimenti-annullo, Fase C.
--
-- ⭐ IMPORTO E TITOLO SI DERIVANO, non si ricevono: il chiamante
--    passa QUALE riga e PERCHE'. E' cio' che rende i due controlli
--    di coerenza del guard una difesa contro la scrittura diretta
--    invece che un errore che l'operatore puo' fare.
--
-- ⭐ L'ammissibilita' la decide la CHECK, che e' la stessa che
--    spegne il pulsante nel read-side: qui non si riscrive il
--    predicato. Cosi' i due non «coincidono oggi», non possono
--    divergere.
DECLARE
    v_mov     RECORD;
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi  jsonb;
    v_new_id  anagrafiche.soggetti_titoli_iva_movimenti.id%TYPE;
BEGIN
    -- 1) Guard di parametro. Un id assente o non positivo e un
    --    motivo vuoto non escono da nessuna interfaccia: li
    --    produce un chiamante rotto, quindi TECNICO.
    IF p_movimento_id IS NULL OR p_movimento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche','fn_annulla_movimento_titolo_iva',
            'E_TITOLO_IVA_ANNULLO_INCOERENTE',
            jsonb_build_object('parametro','p_movimento_id',
                               'valore', p_movimento_id),
            NULL::uuid,
            COALESCE(p_movimento_id::text, 'assente'),
            'identificativo del movimento non valido');
    END IF;

    IF p_motivo IS NULL OR btrim(p_motivo) = '' THEN
        -- ⚠️ Il motivo lo pretende gia'
        --   chk_stiva_movimenti_motivo_forzatura, ma la' uscirebbe
        --   come violazione di CHECK (23514): un errore muto per
        --   chi legge. Qui esce come rifiuto di dominio.
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche','fn_annulla_movimento_titolo_iva',
            'E_TITOLO_IVA_ANNULLO_INCOERENTE',
            jsonb_build_object('parametro','p_motivo'),
            NULL::uuid,
            p_movimento_id::text,
            'il motivo dell''annullo e'' obbligatorio');
    END IF;

    -- 2) Ammissibilita': si CHIAMA la check, non si riscrive.
    v_motivi := script.fn_check_annullo_movimento_titolo_iva(p_movimento_id);

    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⭐ `motivi` non si passa piu': lo mette l'helper, sempre. Nel contesto
    --   resta la sola chiave di dominio.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'anagrafiche', 'fn_annulla_movimento_titolo_iva',
        v_motivi,
        NULL,
        NULL::uuid,
        jsonb_build_object('movimento_id', p_movimento_id));

    -- 3) La riga da annullare, per derivarne titolo e importo.
    -- ⚠️ Questa lettura e' INVOKER: se la riga fosse fuori
    --    perimetro non si vedrebbe. Non e' un buco — la check
    --    (DEFINER) l'ha gia' dichiarata annullabile, quindi
    --    arrivare qui e non trovarla significa che chi opera non
    --    ha il perimetro per farlo, ed e' giusto che si fermi.
    SELECT m.titolo_iva_id, m.imponibile
      INTO v_mov
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.id = p_movimento_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche','fn_annulla_movimento_titolo_iva',
            'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',
            jsonb_build_object('movimento_id', p_movimento_id,
                               'motivo_tecnico','fuori perimetro'),
            NULL::uuid, '', '');
    END IF;

    -- 4) Il contro-movimento. Segno opposto, stesso titolo,
    --    tipo FORZATURA, nessun documento (lo impone gia'
    --    chk_stiva_movimenti_documento) e la data di OGGI, che e'
    --    la data dell'ANNULLO — l'informazione che un flag avrebbe
    --    perso.
    INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti (
        titolo_iva_id, tipo_movimento, imponibile, data_movimento,
        motivo, annulla_movimento_id)
    VALUES (
        v_mov.titolo_iva_id, 'FORZATURA', - v_mov.imponibile,
        (SELECT script.fn_data_operativa()), p_motivo, p_movimento_id)
    RETURNING id INTO v_new_id;

    RETURN v_new_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_annulla_movimento_titolo_iva(p_movimento_id bigint, p_motivo character varying)
IS 'Madre: annulla una FORZATURA del registro plafond IVA scrivendo il CONTRO-MOVIMENTO di segno opposto, e ne ritorna l''id. Il registro resta append-only e l''accumulatore riporta imponibile_utilizzato al valore giusto da se'', perche'' somma senza filtri; a video restano entrambe le righe, l''errore e la correzione, ognuna con la sua data e il suo motivo. ⭐ Il chiamante passa DUE cose: quale riga e perche''. Importo e titolo si DERIVANO dalla riga annullata — ed e'' cio'' che rende i due controlli di coerenza del guard una difesa contro la scrittura diretta invece che un errore che l''operatore puo'' fare. ⭐ L''ammissibilita'' la decide script.fn_check_annullo_movimento_titolo_iva, la stessa che spegne il pulsante nel read-side: la madre la CHIAMA e solleva il codice del primo motivo, non riscrive il predicato — cosi'' i due non possono divergere. SECURITY INVOKER esplicito: RLS e scope emittente restano applicati sulla scrittura (sono la check e il guard a essere DEFINER, e solo per le letture di coerenza). Atomica per costruzione: una sola istruzione, e qualunque eccezione annulla tutto. ⚠️ data_movimento e'' la data dell''ANNULLO, non della forzatura. Piano: brief-db-titoli-iva-movimenti-annullo, Fase C.';
```

</div>

---
{% include-markdown "signature-core.md" %}
