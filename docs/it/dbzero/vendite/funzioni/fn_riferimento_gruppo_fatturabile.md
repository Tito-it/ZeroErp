{% include-markdown "it/dbzero/vendite/manual/fn_riferimento_gruppo_fatturabile.md" %}
# ⚙️ Funzione `fn_riferimento_gruppo_fatturabile`

```sql
CREATE FUNCTION fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il RIFERIMENTO leggibile di un gruppo fatturabile — cioe'
--        cio' che una persona riconosce al posto della chiave.
--        'ORDINE_VENDITA:01a06ce4-…' -> 'ORD0036004'.
-- Ritorna: il numero del documento; se non c'e', il codice della
--        commessa; se non c'e' nemmeno quello, la CHIAVE GREZZA.
-- ⚠️ NON SOLLEVA MAI: la chiama una lista.
DECLARE
    v_key    text := NULLIF(btrim(COALESCE(p_gruppo_key, '')), '');
    v_src    record;
    v_numero text;
    v_codice vendite.commesse.codice%TYPE;
BEGIN
    -- ⚠️ NULL entra e NULL esce: sulla scheda Critiche una chiave
    --    assente vuol dire «la segnalazione e' del GIRO», e li' non
    --    c'e' nessun documento da nominare. Inventare un'etichetta
    --    direbbe una cosa falsa.
    IF v_key IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT * INTO v_src
      FROM vendite.fn_split_gruppo_fatturabile_key(v_key);

    -- Il numero del documento, dalla sede unica della risoluzione
    -- polimorfa. Non risolve niente da se': legge il
    -- `label_selector` che la sorgente dichiara a catalogo.
    SELECT d.documento_numero
      INTO v_numero
      FROM vendite.fn_get_sorgente_documento_ref(
               v_src.sorgente_tipo_id, v_src.sorgente_uid) d;

    -- Il codice della commessa serve alla forma sourceless
    -- ('MAN:<commessa_id>'), dove un documento non c'e' per
    -- progetto: li' il contenitore E' la commessa.
    IF v_src.commessa_id IS NOT NULL THEN
        SELECT c.codice INTO v_codice
          FROM vendite.commesse c WHERE c.id = v_src.commessa_id;
    END IF;

    -- ⭐ IL RIPIEGO A TRE LIVELLI, e l'ultimo non e' una resa: la
    --    chiave grezza e' esattamente cio' che l'operatore vedeva
    --    prima di questa funzione. Peggiorare e' impossibile.
    -- ⚠️ Stessa scala di vw_dash_competenza_gruppi.riferimento. La
    --    vista non la chiama, per non risolvere due volte per riga
    --    (le serve anche documento_id dallo stesso LATERAL): la
    --    seconda scrittura e' DICHIARATA e presidiata da un pgTAP
    --    che chiede alle due la stessa stringa.
    RETURN COALESCE(
        NULLIF(btrim(COALESCE(v_numero, '')), ''),
        NULLIF(btrim(COALESCE(v_codice, '')), ''),
        v_key);
END;
$function$

COMMENT ON FUNCTION vendite.fn_riferimento_gruppo_fatturabile(p_gruppo_key text)
IS 'Il RIFERIMENTO leggibile di un gruppo fatturabile: cio'' che una persona riconosce al posto della chiave — ''ORDINE_VENDITA:01a06ce4-…'' diventa ''ORD0036004''. ⭐ Nasce per la scheda Critiche del lotto, dove il documento di una segnalazione si leggeva come uuid: la gruppo_key e'' la chiave che serve al PULSANTE (fn_escludi_documento_da_giro la vuole), non all''occhio. Compone vendite.fn_split_gruppo_fatturabile_key e vendite.fn_get_sorgente_documento_ref, che risolve il numero leggendo il label_selector dichiarato dalla sorgente a catalogo. ⭐ Ripiego a TRE livelli: numero del documento, poi codice della commessa (la forma sourceless ''MAN:<id>'', dove un documento non c''e'' per progetto), poi la CHIAVE GREZZA — e l''ultimo non e'' una resa: e'' esattamente cio'' che si vedeva prima, quindi peggiorare e'' impossibile. ⚠️ NULL entra e NULL esce: una chiave assente vuol dire «la segnalazione e'' del GIRO», e li'' non c''e'' nessun documento da nominare — inventare un''etichetta direbbe il falso. ⚠️ NON SOLLEVA MAI: la chiama una lista. ⚠️ Stessa scala di ripiego di vw_dash_competenza_gruppi.riferimento, che NON la chiama per non risolvere due volte per riga (le serve anche documento_id dallo stesso LATERAL): la seconda scrittura e'' dichiarata e presidiata da un pgTAP che chiede alle due la stessa stringa sulla stessa chiave. STABLE, SECURITY INVOKER. Brief: brief-db-uscita-documento-dal-giro §6.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
