# ⚙️ Funzione `trgfn_famiglie_documento_guard_disattivazione`

```sql
CREATE FUNCTION trgfn_famiglie_documento_guard_disattivazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_guard_disattivazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare lo spegnimento di una famiglia di documento
    --   che ha ancora registri accesi o documenti numerati.
    --
    -- ⛔ Perche': anagrafiche.fn_ba_ha_storia_emittente itera
    --   `WHERE fd.attivo`. Spegnere la famiglia non nasconde una
    --   voce di catalogo: toglie i suoi documenti dal presidio
    --   sul cambio emittente del billing account. Nessun errore,
    --   nessun log — il controllo guarda in un posto in meno.
    --
    -- ⭐ §12.5.2: QUI NON C'E' IL PREDICATO. Il guard chiama
    --   script.fn_check_famiglia_documento_disattivabile e
    --   solleva il codice del PRIMO motivo, cosi' il rifiuto e
    --   il cestino spento della lista non possono divergere.
    -- =========================================================

    -- ⭐ IL NO-OP PASSA, ed e' la riga che tiene in piedi il
    --   migrate: `UPDATE OF` scatta quando lo statement NOMINA la
    --   colonna, anche a valore invariato, e il mirror CSV
    --   20260830-14 riscrive `attivo` a OGNI migrate.
    -- ⛔ E si guarda la TRANSIZIONE, non lo stato: riaccendere
    --   una famiglia rimette in gioco un presidio, non lo toglie.
    IF NOT (OLD.attivo AND NOT NEW.attivo) THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_famiglia_documento_disattivabile(OLD.id);

    -- Nessun motivo: la famiglia non e' piu' la regola di
    -- nessuno e si puo' ritirare.
    IF v_motivi IS NULL OR jsonb_array_length(v_motivi) = 0 THEN
        RETURN NEW;
    END IF;

    v_primo := v_motivi -> 0;

    -- ⚠️ Niente `campo` nel contesto: non c'e' un input da
    --   correggere: l'operatore ha premuto un interruttore, e
    --   quello che non va e' la situazione. Il verbo e' `attivo`,
    --   e il frontend spegne il pulsante, non accende un campo.
    -- ⚠️ tx_id NULL e non NEW.tx_id: questo guard e' `_a10_` e
    --   scatta PRIMA di trg_famiglie_documento_gen_tx_id_ins_upd
    --   (ordine alfabetico: 'a10' < 'gen'), quindi NEW.tx_id qui
    --   porta ancora il valore vecchio.
    PERFORM script.fn_log_and_raise_error(
        'vendite',
        'trgfn_famiglie_documento_guard_disattivazione',
        v_primo ->> 'codice',
        COALESCE(v_primo -> 'dettaglio', '{}'::jsonb),
        NULL::uuid,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));

    -- Irraggiungibile: la riga sopra solleva sempre.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_disattivazione()
IS 'Guard `_a10_` su vendite.famiglie_documento: rifiuta lo spegnimento di una famiglia che ha ancora registri accesi o documenti numerati. ⛔ PERCHE'': non si difende la coerenza di un catalogo, si difende un PRESIDIO — anagrafiche.fn_ba_ha_storia_emittente e fn_get_storia_emittente_ba iterano `WHERE fd.attivo`, quindi una famiglia spenta esce dal giro e i suoi documenti smettono di trattenere il billing account presso l''emittente che li ha numerati. Nessun errore e nessun log: il controllo guarda semplicemente in un posto in meno. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: si chiama script.fn_check_famiglia_documento_disattivabile e si solleva il codice del PRIMO motivo, cosi'' il rifiuto e il cestino spento della lista non possono divergere. ⛔ SOLO LA TRANSIZIONE VERSO SPENTO (`OLD.attivo AND NOT NEW.attivo`): riaccendere rimette in gioco un presidio, non lo toglie. ⭐ L''USCITA SUL NO-OP E'' OBBLIGATORIA: `UPDATE OF` scatta quando lo statement NOMINA la colonna anche a valore invariato, e il mirror CSV 20260830-14 riscrive `attivo` a ogni migrate — senza il confronto ogni migrate fallirebbe. ⚠️ Niente `campo` nel contesto: l''operatore ha premuto un interruttore, non compilato un input; il frontend spegne il pulsante col motivo. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima del trigger che lo genera. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.4 (DB-2).';
```

---
{% include-markdown "signature-core.md" %}
