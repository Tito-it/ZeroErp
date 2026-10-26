{% include-markdown "it/dbzero/vendite/manual/trgfn_famiglie_documento_guard_disattivazione.md" %}
# ⚙️ Funzione `trgfn_famiglie_documento_guard_disattivazione`

```sql
CREATE FUNCTION trgfn_famiglie_documento_guard_disattivazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_guard_disattivazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⛔ NUDI, e non per fretta: `v_motivi` e' il valore di ritorno di una
    --   fn_check_* (nessuna colonna dietro). Non c'e' niente da ancorare.
    v_motivi jsonb;
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
    -- ⭐ La coda sta in un posto solo (20260908-17): quale motivo si solleva,
    --   come si spacchettano i valori e come si compone il contesto li decide
    --   l'helper. Qui resta la TESTA — quale check chiamare, su cosa.
    -- ⚠️ Niente `campo`: non c'e' un input da correggere — l'operatore ha
    --   premuto un interruttore, e quello che non va e' la situazione. Il
    --   frontend spegne il pulsante, non accende un campo.
    -- ⚠️ `NULL::uuid` e non NEW.tx_id: questo guard sta su un trigger `_a10_`
    --   che, confrontato per NOME INTERO, precede `..._gen_tx_id_ins_upd`
    --   ('a10' < 'gen'), quindi la transazione non e' ancora assegnata.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'trgfn_famiglie_documento_guard_disattivazione',
        v_motivi,
        NULL,
        NULL::uuid);

    -- ⭐ Ora RAGGIUNGIBILE, ed e' il ramo «passa»: l'helper tace quando la
    --   check non ha trovato nessun motivo.
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_guard_disattivazione()
IS 'Guard `_a10_` su vendite.famiglie_documento: rifiuta lo spegnimento di una famiglia che ha ancora registri accesi o documenti numerati. ⛔ PERCHE'': non si difende la coerenza di un catalogo, si difende un PRESIDIO — anagrafiche.fn_ba_ha_storia_emittente e fn_get_storia_emittente_ba iterano `WHERE fd.attivo`, quindi una famiglia spenta esce dal giro e i suoi documenti smettono di trattenere il billing account presso l''emittente che li ha numerati. Nessun errore e nessun log: il controllo guarda semplicemente in un posto in meno. ⭐ §12.5.2 — QUI NON C''E'' IL PREDICATO: si chiama script.fn_check_famiglia_documento_disattivabile e si solleva il codice del PRIMO motivo, cosi'' il rifiuto e il cestino spento della lista non possono divergere. ⛔ SOLO LA TRANSIZIONE VERSO SPENTO (`OLD.attivo AND NOT NEW.attivo`): riaccendere rimette in gioco un presidio, non lo toglie. ⭐ L''USCITA SUL NO-OP E'' OBBLIGATORIA: `UPDATE OF` scatta quando lo statement NOMINA la colonna anche a valore invariato, e il mirror CSV 20260830-14 riscrive `attivo` a ogni migrate — senza il confronto ogni migrate fallirebbe. ⚠️ Niente `campo` nel contesto: l''operatore ha premuto un interruttore, non compilato un input; il frontend spegne il pulsante col motivo. ⚠️ tx_id NULL e non NEW.tx_id: `_a10_` scatta prima del trigger che lo genera. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.4 (DB-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
