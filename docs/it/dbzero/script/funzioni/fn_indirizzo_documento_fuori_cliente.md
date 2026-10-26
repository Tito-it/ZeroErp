# ⚙️ Funzione `fn_indirizzo_documento_fuori_cliente`

```sql
CREATE FUNCTION fn_indirizzo_documento_fuori_cliente(p_origine_indirizzo_id bigint, p_origine_soggetto_ruolo_id bigint, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_indirizzo_documento_fuori_cliente(p_origine_indirizzo_id bigint, p_origine_soggetto_ruolo_id bigint, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- ⚠️ RETURNS text nudo DICHIARATO: e' un motivo macchina
--   (ALTRO_CLIENTE | ALTRA_FORNITURA), senza colonna di vocabolario.
DECLARE
    v_ind_ruolo   anagrafiche.indirizzi.soggetto_ruolo_id%TYPE;
    v_ind_istanza anagrafiche.indirizzi.istanza_utility_id%TYPE;
    v_ruolo_riga  anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- Una-tantum: scritto a mano, resta valido col cliente che cambia.
    IF p_origine_indirizzo_id IS NULL AND p_origine_soggetto_ruolo_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Documento senza ruolo: nessuna ancora da confrontare.
    IF p_soggetto_ruolo_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Layer RUOLO: l'indirizzo d'anagrafica, letto vivo. La FK
    -- (NO ACTION) garantisce che ci sia.
    IF p_origine_indirizzo_id IS NOT NULL THEN
        SELECT i.soggetto_ruolo_id, i.istanza_utility_id
          INTO v_ind_ruolo, v_ind_istanza
          FROM anagrafiche.indirizzi i
         WHERE i.id = p_origine_indirizzo_id;
    END IF;

    v_ruolo_riga := COALESCE(p_origine_soggetto_ruolo_id, v_ind_ruolo);

    -- ⚠️ Due confronti, non uno: un'origine del ruolo che dice il
    --   cliente giusto accanto a un indirizzo d'anagrafica di un
    --   altro ruolo e' una riga incoerente, e non e' del cliente.
    IF v_ruolo_riga IS DISTINCT FROM p_soggetto_ruolo_id
       OR (v_ind_ruolo IS NOT NULL AND v_ind_ruolo <> p_soggetto_ruolo_id) THEN
        RETURN 'ALTRO_CLIENTE';
    END IF;

    IF v_ind_istanza IS NOT NULL
       AND v_ind_istanza IS DISTINCT FROM p_istanza_utility_id THEN
        RETURN 'ALTRA_FORNITURA';
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.fn_indirizzo_documento_fuori_cliente(p_origine_indirizzo_id bigint, p_origine_soggetto_ruolo_id bigint, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint)
IS 'Il predicato «l''indirizzo del documento e'' del suo cliente?», sui valori: origine della riga (origine_indirizzo_id, origine_soggetto_ruolo_id) e cliente del documento (ruolo, istanza: script.fn_get_cliente_testata_documento). NULL = del cliente; altrimenti il motivo: ALTRO_CLIENTE (il ruolo della riga, o quello dell''indirizzo d''anagrafica, non e'' il ruolo del documento) o ALTRA_FORNITURA (l''indirizzo d''anagrafica e'' legato a un''istanza diversa da quella del documento, anche quando il documento non ne ha una: e'' la scelta di script.fn_resolve_indirizzo_documento, che con l''istanza NULL prende solo i generici). Una-tantum (le due origini NULL) e documento senza ruolo: sempre NULL. ⚠️ L''istanza dell''indirizzo d''anagrafica si legge viva. La usano vendite.trgfn_doc_indirizzi_guard_cliente, vendite.trgfn_doc_indirizzi_seguono_cliente e script.fn_check_indirizzi_documento_cliente: guard, cambio di cliente e motivo d''emissione non possono rispondere in due modi. Brief: brief-db-indirizzi-documento-seguono-il-cliente (D-1, §7.2 c).';
```

</div>

---
{% include-markdown "signature-core.md" %}
