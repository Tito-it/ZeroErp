{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_titoli_iva_guard_coerenza.md" %}
# ⚙️ Funzione `trgfn_soggetti_titoli_iva_guard_coerenza`

```sql
CREATE FUNCTION trgfn_soggetti_titoli_iva_guard_coerenza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: tenere le due regole del titolo IVA che un CHECK di
--   colonna non puo' esprimere, perche' guardano fuori dalla riga.
--   (1) il plafond esiste se e solo se config.tipi_titolo_iva
--       dichiara ha_plafond per il tipo del titolo;
--   (2) un titolo con ambito TUTTO non porta righe di ambito.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I7 / D10.
-- ⚠️ SECURITY INVOKER e non DEFINER: le righe contate sono le
--   figlie della riga stessa, e la loro policy passa dallo stesso
--   emittente del padre — chi scrive il padre le vede tutte.
DECLARE
    v_ha_plafond   config.tipi_titolo_iva.ha_plafond%TYPE;
    v_tipo_descr   config.tipi_titolo_iva.descrizione%TYPE;
    v_n_ambiti     bigint;
BEGIN
    SELECT t.ha_plafond, t.descrizione
      INTO v_ha_plafond, v_tipo_descr
      FROM config.tipi_titolo_iva t
     WHERE t.id = NEW.tipo_titolo_iva_id;

    -- ⚠️ Se il tipo non c'e' la FK lo dira' con la sua voce: qui
    --   non si inventa un secondo errore per la stessa causa.
    --   ⭐ E il SELECT INTO senza righe AZZERA le variabili, quindi
    --   senza questa uscita i due rami sotto leggerebbero NULL e
    --   non scatterebbero mai — un guard verde per sottrazione.
    IF v_ha_plafond IS NULL THEN
        RETURN NEW;
    END IF;

    -- ── REGOLA 1a — il tetto dichiarato dal tipo dev'esserci.
    IF v_ha_plafond IS TRUE AND NEW.plafond IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'trgfn_soggetti_titoli_iva_guard_coerenza',
            'E_TITOLO_IVA_PLAFOND_MANCANTE',
            jsonb_build_object('campo', 'plafond',
                               'titolo_iva_id', NEW.id,
                               'tipo_titolo_iva_id', NEW.tipo_titolo_iva_id),
            NEW.tx_id,
            v_tipo_descr);
    END IF;

    -- ── REGOLA 1b — il verso che si dimentica: un tetto su un
    --    titolo che non ne ha e' un numero che nessuno consuma, e
    --    chi lo legge crede che quel titolo abbia un limite.
    IF v_ha_plafond IS FALSE AND NEW.plafond IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'trgfn_soggetti_titoli_iva_guard_coerenza',
            'E_TITOLO_IVA_PLAFOND_NON_AMMESSO',
            jsonb_build_object('campo', 'plafond',
                               'titolo_iva_id', NEW.id,
                               'tipo_titolo_iva_id', NEW.tipo_titolo_iva_id),
            NEW.tx_id,
            v_tipo_descr);
    END IF;

    -- ── REGOLA 2 — «vale per tutto» e «vale per queste voci» non
    --    stanno insieme. Il caso non si crea solo inserendo una
    --    riga di ambito (quello lo ferma il guard delle figlie):
    --    si crea anche RIPORTANDO A 'TUTTO' un titolo che le righe
    --    ce l'ha gia'. Senza questo ramo, l'ambito resterebbe
    --    scritto e il risolutore leggerebbe «vale per tutto»
    --    mentre la tabella dice un'altra cosa.
    IF NEW.ambito = 'TUTTO' AND TG_OP = 'UPDATE' THEN
        SELECT count(*)
          INTO v_n_ambiti
          FROM anagrafiche.soggetti_titoli_iva_ambiti a
         WHERE a.titolo_iva_id = NEW.id;

        IF v_n_ambiti > 0 THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'trgfn_soggetti_titoli_iva_guard_coerenza',
                'E_TITOLO_IVA_AMBITO_NON_AMMESSO',
                jsonb_build_object('campo', 'ambito',
                                   'titolo_iva_id', NEW.id,
                                   'righe_ambito', v_n_ambiti),
                NEW.tx_id,
                v_tipo_descr);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza()
IS 'Le due regole di anagrafiche.soggetti_titoli_iva che un CHECK di colonna non puo'' scrivere, perche'' guardano fuori dalla riga. (1) IL PLAFOND ESISTE SE E SOLO SE IL TIPO NE PREVEDE UNO: legge config.tipi_titolo_iva.ha_plafond, e vale sui DUE versi — un tetto assente dove serve lascia la primitiva di consumo senza capienza da confrontare, un tetto presente dove non serve e'' un numero che nessuno consuma e che chi legge scambia per un limite (E_TITOLO_IVA_PLAFOND_MANCANTE / E_TITOLO_IVA_PLAFOND_NON_AMMESSO). (2) UN TITOLO CHE VALE PER TUTTO NON HA RIGHE DI AMBITO: il ramo qui dentro copre il verso che il guard delle figlie non vede — riportare a TUTTO un titolo che le righe ce l''ha gia'' (E_TITOLO_IVA_AMBITO_NON_AMMESSO). ⚠️ SECURITY INVOKER e non DEFINER, ed e'' motivato: le righe contate sono le figlie della riga stessa e la loro policy passa dallo stesso emittente del padre, quindi chi puo'' scrivere il padre le vede tutte — non esiste il caso «ce n''e'' una che non vedo» che rende cieco un guard sotto RLS. ⚠️ Il nome del trigger sceglie l''ORDINE: i BEFORE ROW scattano in ordine alfabetico, e le FK verso config.iva e config.tipi_titolo_iva faranno nascere dalle automazioni dei guard *_require_attivo_*; `guard_coerenza` viene prima, quindi il messaggio che l''operatore legge e'' quello di dominio. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
