{% include-markdown "it/dbzero/vendite/manual/fn_popola_fatture_rettifiche.md" %}
# ⚙️ Funzione `fn_popola_fatture_rettifiche`

```sql
CREATE FUNCTION fn_popola_fatture_rettifiche(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_popola_fatture_rettifiche(p_fattura_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: proietta sul legame documento-a-documento
--   (vendite.fatture_rettifiche) cio' che le righe gia' dicono
--   (fatture_righe.riga_rettificata_id). Ritorna il numero di
--   coppie effettivamente aggiunte.
-- Idempotente: ON CONFLICT DO NOTHING sulla coppia. Rieseguibile
--   su un documento gia' proiettato senza effetti.
-- ⚠️ Non cancella mai: una proiezione che cancella diventa un
--   secondo scrittore, ed e' li' che nascono le due verita'.
DECLARE
    v_inserite integer;
    v_storni   integer;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_popola_fatture_rettifiche','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','fattura_id','valore',p_fattura_id),
            NULL::uuid, 'fattura_id obbligatorio (>0)');
    END IF;

    INSERT INTO vendite.fatture_rettifiche (fattura_id, rettificata_id)
    SELECT DISTINCT r.fattura_id, orig.fattura_id
      FROM vendite.fatture_righe r
      JOIN vendite.fatture_righe orig ON orig.id = r.riga_rettificata_id
     WHERE r.fattura_id = p_fattura_id
       AND r.riga_rettificata_id IS NOT NULL
       -- Una fattura non rettifica se stessa: sarebbe una coppia
       -- che non dice nulla, e la FK la ammetterebbe.
       AND orig.fattura_id <> r.fattura_id
    ON CONFLICT ON CONSTRAINT uq_fatture_rettifiche_pair DO NOTHING;

    GET DIAGNOSTICS v_inserite = ROW_COUNT;

    -- rev 2026-10-31 (20261031-48, D-1-ter): la nota di credito cita le
    -- fatture dei pezzi di canone che storna (meta.storno_di_attivita_id
    -- della riga di commessa dello storno -> il pezzo -> la sua fattura).
    INSERT INTO vendite.fatture_rettifiche (fattura_id, rettificata_id)
    SELECT DISTINCT r.fattura_id, fo.fattura_id
      FROM vendite.fatture f
      JOIN vendite.fatture_righe r ON r.fattura_id = f.id
      JOIN vendite.attivita_fatturabili af ON af.fattura_riga_id = r.id
      JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
      JOIN vendite.attivita_fatturabili afo
        ON afo.commessa_attivita_id = CASE WHEN (ca.meta ->> 'storno_di_attivita_id') ~ '^[0-9]+$'
                                      THEN (ca.meta ->> 'storno_di_attivita_id')::bigint END
      JOIN vendite.fatture_righe fo ON fo.id = afo.fattura_riga_id
     WHERE f.id = p_fattura_id
       AND f.natura_doc_id = config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')
       AND fo.fattura_id <> r.fattura_id
    ON CONFLICT ON CONSTRAINT uq_fatture_rettifiche_pair DO NOTHING;

    GET DIAGNOSTICS v_storni = ROW_COUNT;
    v_inserite := v_inserite + v_storni;
    RETURN v_inserite;
END
$function$

COMMENT ON FUNCTION vendite.fn_popola_fatture_rettifiche(p_fattura_id bigint)
IS 'Proietta sul legame documento-a-documento (vendite.fatture_rettifiche, una tabella che esisteva dal primo giorno con ZERO righe) cio'' che le righe gia'' dicono tramite fatture_righe.riga_rettificata_id. ⭐ Le righe sono il FATTO, la tabella-ponte e'' l''INDICE: non ci sono due verita'', c''e'' una verita'' e una sua proiezione ricostruibile in qualunque momento. Serve al blocco DatiFattureCollegate di una TD04, che vuole numero e data del documento rettificato: senza, il builder XML dovrebbe risalire riga per riga e de-duplicare da solo, cioe'' rifare questo lavoro in un posto dove un errore diventa un file trasmesso. Funzione e NON trigger: dentro la transazione che genera le righe girerebbe una volta per riga sul punto piu'' caldo del giro di fatturazione, e la proiezione non ha bisogno di essere immediata — serve a chi LEGGE il documento, non a chi lo scrive. La consuma un task di pipeline (richiesta BE-8). Idempotente (ON CONFLICT DO NOTHING); non cancella mai, perche'' una proiezione che cancella diventa un secondo scrittore. brief-design-note-credito-resi N10. rev 2026-08-18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
