{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_movimenti_accumulatore.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_movimenti_accumulatore`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_movimenti_accumulatore()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: riportare anagrafiche.soggetti_titoli_iva.imponibile_utilizzato
--   alla SOMMA del registro dei movimenti, dopo ogni scrittura sul
--   registro. E' cio' che rende vera la promessa di D5 — il valore
--   e' memorizzato (P3) ma non puo' mentire, perche' nessuno lo
--   scrive a mano. Rifiuta il conto sotto zero, che nessuna lettura
--   del dominio ammette.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I7 / D5.
DECLARE
    -- ⚠️ Array e non due scalari: un UPDATE che sposta un movimento
    --   da un titolo a un altro deve ricalcolarli ENTRAMBI, o il
    --   titolo abbandonato resta con la somma di prima — un plafond
    --   consumato da un movimento che non e' piu' suo.
    -- ⚠️ `bigint[]` esplicito: `colonna%TYPE[]` non esiste in
    --   PostgreSQL, ed e' l'unico posto di questa funzione dove
    --   il tipo non si puo' ancorare alla colonna.
    v_titoli   bigint[] := ARRAY[]::bigint[];
    v_titolo_id anagrafiche.soggetti_titoli_iva_movimenti.titolo_iva_id%TYPE;
    v_somma     anagrafiche.soggetti_titoli_iva.imponibile_utilizzato%TYPE;
    v_tipo_descr config.tipi_titolo_iva.descrizione%TYPE;
    v_tx_id     anagrafiche.soggetti_titoli_iva_movimenti.tx_id%TYPE;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        v_titoli := v_titoli || OLD.titolo_iva_id;
        v_tx_id  := OLD.tx_id;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        v_titoli := v_titoli || NEW.titolo_iva_id;
        v_tx_id  := NEW.tx_id;
    END IF;

    -- Un UPDATE che NON cambia il titolo mette due volte lo stesso
    -- id: senza questa riga il ricalcolo girerebbe due volte con
    -- lo stesso esito, che non e' un errore ma e' lavoro buttato.
    v_titoli := ARRAY(SELECT DISTINCT unnest(v_titoli));

    FOREACH v_titolo_id IN ARRAY v_titoli
    LOOP
        -- ⚠️ COALESCE: senza movimenti la somma e' NULL, e la
        --   colonna e' NOT NULL. L'ultimo movimento cancellato
        --   deve riportare il titolo a zero, non farlo esplodere.
        SELECT COALESCE(SUM(m.imponibile), 0)
          INTO v_somma
          FROM anagrafiche.soggetti_titoli_iva_movimenti m
         WHERE m.titolo_iva_id = v_titolo_id;

        IF v_somma < 0 THEN
            SELECT tt.descrizione
              INTO v_tipo_descr
              FROM anagrafiche.soggetti_titoli_iva t
              JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
             WHERE t.id = v_titolo_id;

            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'trgfn_soggetti_titoli_iva_movimenti_accumulatore',
                'E_TITOLO_IVA_UTILIZZATO_NEGATIVO',
                jsonb_build_object('campo', 'imponibile',
                                   'titolo_iva_id', v_titolo_id,
                                   'somma', v_somma),
                v_tx_id,
                -- ⚠️ Nel VARIADIC il tipo di titolo e l'importo che
                --   una persona legge, mai il nome della colonna.
                COALESCE(v_tipo_descr, ''),
                to_char(v_somma, 'FM999G999G990D00'));
        END IF;

        UPDATE anagrafiche.soggetti_titoli_iva t
           SET imponibile_utilizzato = v_somma
         WHERE t.id = v_titolo_id
           AND t.imponibile_utilizzato IS DISTINCT FROM v_somma;
    END LOOP;

    RETURN NULL;   -- AFTER trigger: il valore di ritorno e' ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore()
IS 'Riporta anagrafiche.soggetti_titoli_iva.imponibile_utilizzato alla SOMMA del registro dei movimenti dopo ogni scrittura sul registro. ⭐ E'' cio'' che rende vera la promessa di D5: il valore e'' memorizzato come chiede P3, ma non puo'' mentire perche'' nessuno lo scrive a mano — una forzatura e'' una RIGA con motivo, autore e data, invece di un numero sovrascritto sopra a un altro. ⚠️ RICALCOLA dalla somma invece di sommare un delta: un accumulatore incrementale va fuori sincrono al primo UPDATE dell''importo, al primo DELETE, al primo movimento spostato — il ricalcolo non ha casi. 🔴 E ricalcola DUE titoli quando un UPDATE sposta un movimento: con OLD e NEW letti distrattamente il titolo abbandonato resterebbe con la somma di prima, cioe'' un plafond consumato da un movimento che non e'' piu'' suo. ⛔ Il conto sotto zero si rifiuta QUI con E_TITOLO_IVA_UTILIZZATO_NEGATIVO e non con un CHECK sulla colonna: la colonna la scrive questo trigger, quindi un 23514 sarebbe un errore muto sollevato dentro un trigger su una tabella diversa da quella che l''operatore stava toccando. ⛔ Il TETTO invece non si controlla qui, ed e'' una decisione: sulle fatture il caso non si presenta (la spezzatura di P2 la calcola fn_consuma_plafond_titolo_iva, che e'' anche l''unica a prendere il lock), e sulle forzature un superamento e'' un''informazione sul mondo — impedire di scriverlo impedirebbe di accorgersene. Il presidio giusto per quel caso e'' una lista di titoli sfondati che qualcuno guarda, e non fa parte di I7. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
