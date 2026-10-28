{% include-markdown "it/dbzero/script/manual/fn_doc_lock_colonna_bloccata.md" %}
# ⚙️ Funzione `fn_doc_lock_colonna_bloccata`

```sql
CREATE FUNCTION fn_doc_lock_colonna_bloccata(p_regola jsonb, p_stato text, p_colonne text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_lock_colonna_bloccata(p_regola jsonb, p_stato text, p_colonne text[])
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE
AS $function$
-- ⚠️ Tipi nudi DICHIARATI: p_regola e' l'uscita di
--   script.fn_doc_lock_regola; p_stato e' il codice_interno di
--   sei vocabolari di stato diversi (polimorfo); p_colonne e il
--   risultato sono nomi di colonna di tabelle diverse.
BEGIN
  -- =========================================================
  -- Scopo:
  --   Con il documento in p_stato, quale delle colonne
  --   p_colonne il montaggio non lascia cambiare? NULL = passa;
  --   altrimenti la prima che ferma, '*' = la riga intera.
  --   E' la decisione dei due building block «si tocca solo
  --   in bozza»: la usano il trigger e la capability, che
  --   cosi' non possono rispondere in due modi.
  -- rev 2026-10-18: sulla TESTATA una colonna «ferma sempre»
  --   (ferma_sempre della regola) non si cambia nemmeno in
  --   bozza. Per questo la bozza non chiude piu' la decisione
  --   prima dei due rami: la chiude ciascun ramo.
  -- =========================================================

  -- Un montaggio sbagliato non lascia passare niente.
  IF p_regola IS NULL OR p_regola ->> 'errore' IS NOT NULL THEN
    RETURN '*';
  END IF;

  IF p_regola ->> 'building_block' = 'RIGHE' THEN
    -- In bozza tutto si tocca. Uno stato NULL non e' la bozza.
    IF p_stato = p_regola ->> 'stato_bozza' THEN
      RETURN NULL;
    END IF;

    -- La riga intera (INSERT, DELETE): nessuna eccezione.
    IF p_colonne IS NULL THEN
      RETURN '*';
    END IF;

    -- Fuori dagli stati dell'eccezione non cambia niente,
    -- nemmeno un UPDATE che non tocca colonne.
    IF p_stato IS NULL
       OR NOT jsonb_exists(p_regola -> 'stati_ammessi', p_stato) THEN
      RETURN COALESCE(
        (SELECT c
           FROM unnest(p_colonne) WITH ORDINALITY AS u(c, k)
          WHERE NOT jsonb_exists(p_regola -> 'colonne_tecniche', c)
          ORDER BY k
          LIMIT 1),
        '*');
    END IF;

    -- Nello stato dell'eccezione: solo le colonne ammesse (e
    -- quelle tecniche, che scrive l'audit).
    RETURN (SELECT c
              FROM unnest(p_colonne) WITH ORDINALITY AS u(c, k)
             WHERE NOT jsonb_exists(p_regola -> 'colonne_ammesse', c)
               AND NOT jsonb_exists(p_regola -> 'colonne_tecniche', c)
             ORDER BY k
             LIMIT 1);
  END IF;

  IF p_regola ->> 'building_block' = 'TESTATA' THEN
    -- Le colonne nominate, nell'ordine del montaggio: la prima
    -- che cambia e che in questo stato non e' aperta. Le altre
    -- colonne della testata sono libere.
    -- Aperta: in bozza, o in uno degli stati della terna; una
    -- colonna ferma sempre non e' aperta in nessuno stato, bozza
    -- compresa. Uno stato NULL non e' la bozza.
    RETURN (SELECT e ->> 'colonna'
              FROM jsonb_array_elements(p_regola -> 'colonne') WITH ORDINALITY AS x(e, k)
             WHERE (p_colonne IS NULL OR (e ->> 'colonna') = ANY (p_colonne))
               AND ((e ->> 'ferma_sempre')::boolean IS TRUE
                    OR (p_stato IS DISTINCT FROM p_regola ->> 'stato_bozza'
                        AND (p_stato IS NULL
                             OR NOT jsonb_exists(e -> 'stati_ammessi', p_stato))))
             ORDER BY k
             LIMIT 1);
  END IF;

  -- Una regola che non sa leggere: non passa niente.
  RETURN '*';
END;
$function$

COMMENT ON FUNCTION script.fn_doc_lock_colonna_bloccata(p_regola jsonb, p_stato text, p_colonne text[])
IS 'Building block (2026-10-10, brief-db-testata-dopo-emissione fase 1, R-1): la DECISIONE dei due building block «si tocca solo in bozza». Con il documento in p_stato (codice_interno), quale delle colonne p_colonne il montaggio p_regola (uscita di script.fn_doc_lock_regola) non lascia cambiare? NULL = passa; altrimenti la prima che ferma, ''*'' = la riga intera. Montaggio sbagliato: ''*''. Stato bozza: NULL. p_stato NULL = fuori bozza in nessuno stato ammesso. RIGHE: p_colonne NULL (INSERT, DELETE) = ''*''; fuori dagli stati ammessi la prima colonna non tecnica, o ''*'' anche se non ne cambia nessuna; negli stati ammessi la prima colonna che non e'' ammessa ne'' tecnica (data_update, user_update, tx_id). TESTATA: la prima colonna nominata dal montaggio (nel suo ordine) che cambia e che nello stato non e'' aperta; le colonne non nominate sono libere; p_colonne NULL = tutte. La chiamano vendite.trgfn_doc_righe_lock_fuori_bozza, vendite.trgfn_doc_testata_lock_fuori_bozza e script.fn_doc_colonna_modificabile: trigger e capability decidono con la stessa funzione. IMMUTABLE. rev 2026-10-18 (brief-db-indirizzi-documento-seguono-il-cliente §8.7): sulla TESTATA una colonna con ferma_sempre (terna con ''-'', script.fn_doc_lock_regola) si ferma in ogni stato, bozza compresa: la bozza non chiude piu'' la decisione prima dei due rami, la chiude ciascun ramo. RIGHE invariato. Lo stato bozza da'' NULL salvo una colonna ferma sempre che cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
