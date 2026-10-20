{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_sorgenti_guard_emittente.md" %}
# ⚙️ Funzione `trgfn_commesse_sorgenti_guard_emittente`

```sql
CREATE FUNCTION trgfn_commesse_sorgenti_guard_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_sorgenti_guard_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Trigger sottile: delega e basta. Il DEFINER sta nel guard,
    -- perche' e' li' che si legge sotto RLS.
    PERFORM vendite.fn_guard_commessa_sorgente_emittente(
        NEW.commessa_id, NEW.sorgente_tipo_id, NEW.sorgente_uid);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_sorgenti_guard_emittente()
IS 'Trigger BEFORE INSERT / UPDATE OF (commessa_id, sorgente_tipo_id, sorgente_uid) su vendite.commesse_sorgenti: delega a vendite.fn_guard_commessa_sorgente_emittente. SECURITY INVOKER, sottile per scelta — il DEFINER sta nel guard, che e'' dove si legge sotto RLS. ⛔ Il nome del TRIGGER e'' scelto per l''ORDINE e non per l''estetica: sulla tabella c''e'' gia'' trg_commesse_sorgenti_a10_guard_sorgente_ins_upd (il guard polimorfo, che verifica che il documento ESISTA), i BEFORE ROW scattano in ordine alfabetico e «...guard_sorgente_omogeneita_...» viene dopo «...guard_sorgente_...». Al contrario, questo girerebbe per primo e proverebbe a risolvere il billing account di un documento fantasma, restituendo il proprio errore al posto di uno piu'' preciso. ⛔ Il guard sta qui e non dentro vendite.fn_link_commessa_sorgente — che non e'' stata toccata — per la stessa ragione del guard sulla commessa: la funzione e'' UNO scrittore, il trigger e'' il vincolo. Piano: brief-db-emittente-commessa-invariante, L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
