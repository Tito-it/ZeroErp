# ⚙️ Funzione `trgfn_registri_fatturazione_guard_forma_numero`

```sql
CREATE FUNCTION trgfn_registri_fatturazione_guard_forma_numero()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_registri_fatturazione_guard_forma_numero()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
    v_campo  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare il cambio della FORMA DEL NUMERO — prefisso,
    --   suffisso, lunghezza_numero — su un registro che ha gia'
    --   consegnato almeno un numero.
    --
    -- ⛔ Perche': il contatore NON riparte quando cambia la
    --   forma, prosegue. Il documento successivo esce con una
    --   forma nuova e un numero che continua la serie vecchia, e
    --   nessun vincolo se ne accorge — la coppia (forma, numero)
    --   non e' vincolata da nessuna parte.
    --
    -- ⭐ §12.5.2: QUI NON C'E' IL PREDICATO. Il guard chiama
    --   script.fn_check_registro_forma_modificabile e solleva il
    --   codice del PRIMO motivo. Cosi' il rifiuto e il tooltip
    --   della maschera non «coincidono oggi»: non POSSONO
    --   divergere, perche' la regola sta scritta in un posto
    --   solo.
    -- =========================================================

    -- ⭐ Il no-op passa: `UPDATE OF` scatta quando lo statement
    --   NOMINA la colonna, anche a valore invariato. Confrontare
    --   i valori e' cio' che tiene il guard fuori dai piedi di un
    --   mirror CSV che riscrivesse queste colonne.
    IF NEW.prefisso         IS NOT DISTINCT FROM OLD.prefisso
       AND NEW.suffisso     IS NOT DISTINCT FROM OLD.suffisso
       AND NEW.lunghezza_numero IS NOT DISTINCT FROM OLD.lunghezza_numero THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_registro_forma_modificabile(OLD.id);

    -- Nessun motivo: il registro non ha ancora numerato, la forma
    -- si cambia liberamente.
    IF v_motivi IS NULL OR jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    v_primo := v_motivi -> 0;

    -- ⚠️ Il campo da accendere nel form e' il PRIMO che e'
    --   cambiato davvero, non uno fisso: l'operatore ne ha
    --   toccato uno, e mandarlo a correggerne un altro e' peggio
    --   che non dirglielo.
    v_campo := CASE
        WHEN NEW.prefisso IS DISTINCT FROM OLD.prefisso THEN 'prefisso'
        WHEN NEW.suffisso IS DISTINCT FROM OLD.suffisso THEN 'suffisso'
        ELSE 'lunghezza_numero'
    END;

    -- ⚠️ tx_id NULL e non NEW.tx_id: questo guard e' `_a10_` e
    --   scatta PRIMA di trg_registri_fatturazione_gen_tx_id_ins_upd
    --   (ordine alfabetico: 'a10' < 'gen'), quindi NEW.tx_id qui
    --   porta ancora il valore vecchio.
    PERFORM script.fn_log_and_raise_error(
        'vendite',
        'trgfn_registri_fatturazione_guard_forma_numero',
        v_primo ->> 'codice',
        COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
            || jsonb_build_object('campo', v_campo),
        NULL::uuid,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));

    -- Irraggiungibile: la riga sopra solleva sempre.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_registri_fatturazione_guard_forma_numero()
IS 'Guard `_a10_` su vendite.registri_fatturazione: rifiuta il cambio della FORMA DEL NUMERO — prefisso, suffisso, lunghezza_numero — su un registro che ha gia'' consegnato almeno un numero. ⛔ PERCHE'': il contatore non riparte quando cambia la forma, PROSEGUE — quindi sullo stesso sezionale convivrebbero due forme con numeri consecutivi, e nessun vincolo se ne accorge perche'' la coppia (forma, numero) non e'' vincolata da nessuna parte. E'' la stessa specie di difetto riparato dal cantiere del prefisso il 2026-08-31 (difetto A: forma identica, contatore ripartito da 1) presa dal verso opposto. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: il guard CHIAMA script.fn_check_registro_forma_modificabile e solleva il codice del primo motivo, cosi'' il rifiuto e il tooltip della maschera non possono divergere. Sulla DISATTIVAZIONE lo stesso presidio non era raggiungibile, perche'' la'' a rifiutare e'' dbops.trgfn_prevent_deactivate_if_children, un trigger generico guidato da TG_ARGV e condiviso da un centinaio di tabelle. ⭐ CONFRONTA I VALORI, NON LE COLONNE: `UPDATE OF` scatta quando lo statement NOMINA la colonna anche a valore invariato, quindi il primo IF lascia passare il no-op — ed e'' cio'' che tiene il guard immune al giorno in cui il mirror CSV 80_data/sql/vendite/registri_fatturazione.csv guadagnasse queste colonne. ⛔ E'' anche il motivo per cui serie_default NON e'' fra le colonne presidiate: quel mirror la riscrive gia'' a ogni migrate, e un BEFORE UPDATE OF serie_default farebbe fallire il migrate; in piu'' serie entra nella chiave del contatore, quindi cambiarla apre una serie nuova che distingue i documenti — che e'' legittimo. ⛔ SOLO UPDATE, MAI INSERT: un guard BEFORE ROW montato anche in INSERT oscurerebbe i CHECK della tabella (SQLSTATE da 23514 a P0001), e alla nascita del registro non c''e'' niente da proteggere. ⚠️ Il context porta `campo` = la PRIMA delle tre colonne cambiata davvero: e'' il canale che diventa error.fields e accende l''input giusto nel form. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima di trg_registri_fatturazione_gen_tx_id_ins_upd (ordine alfabetico), quindi NEW.tx_id porta ancora il valore vecchio. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 8 (D-3).';
```

---
{% include-markdown "signature-core.md" %}
