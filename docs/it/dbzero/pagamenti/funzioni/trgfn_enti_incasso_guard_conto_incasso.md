{% include-markdown "it/dbzero/pagamenti/manual/trgfn_enti_incasso_guard_conto_incasso.md" %}
# ⚙️ Funzione `trgfn_enti_incasso_guard_conto_incasso`

```sql
CREATE FUNCTION trgfn_enti_incasso_guard_conto_incasso()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_enti_incasso_guard_conto_incasso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_uso anagrafiche.soggetti_ruoli_conti_bancari.uso%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il conto agganciato a un canale di incasso deve essere un
    --   conto di INCASSO. La FK garantisce che la riga esista,
    --   non che cosa sia.
    --
    -- Perche' conta (D5): l'unicita'
    --   ex_src_bancari_conto_incasso_un_solo_soggetto vive SOLO
    --   sulle righe con uso = 'INCASSO'. Un ente appeso a una
    --   riga PAGAMENTO o GENERICO sarebbe fuori da quella
    --   garanzia, e il perimetro «un conto -> un solo emittente»
    --   tornerebbe a essere un'assunzione.
    --
    -- ⚠️ Lettura sotto RLS: anagrafiche.soggetti_ruoli_conti_bancari
    --   ha la row security SPENTA, quindi SECURITY INVOKER va
    --   bene. Se un giorno entra sotto RLS, questa funzione va
    --   portata su una SECURITY DEFINER: altrimenti confonderebbe
    --   «non e' di incasso» con «non lo vedo».
    -- =========================================================

    -- Su UPDATE si guarda solo se la colonna cambia: altrimenti
    -- una modifica alla descrizione verrebbe rifiutata per una
    -- configurazione decisa mesi prima.
    IF TG_OP = 'UPDATE'
       AND NEW.soggetto_ruolo_conto_bancario_id
           IS NOT DISTINCT FROM OLD.soggetto_ruolo_conto_bancario_id THEN
        RETURN NEW;
    END IF;

    SELECT src.uso
      INTO v_uso
      FROM anagrafiche.soggetti_ruoli_conti_bancari src
     WHERE src.id = NEW.soggetto_ruolo_conto_bancario_id;

    -- v_uso NULL = riga inesistente: non e' affare di questo
    -- guard, la FK la rifiuta da se' e con il suo messaggio.
    IF v_uso IS NOT NULL AND v_uso <> 'INCASSO' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_enti_incasso_guard_conto_incasso',
            'E_ENTE_INCASSO_CONTO_NON_DI_INCASSO',
            jsonb_build_object(
                'detail', 'Il conto agganciato al canale non ha uso INCASSO',
                'campo',  'soggetto_ruolo_conto_bancario_id',
                'soggetto_ruolo_conto_bancario_id', NEW.soggetto_ruolo_conto_bancario_id,
                'uso',    v_uso,
                'codice', NEW.codice
            ),
            NULL::uuid,
            v_uso::text
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION pagamenti.trgfn_enti_incasso_guard_conto_incasso()
IS 'Guard di configurazione: il conto agganciato a un canale di incasso deve avere uso = ''INCASSO''. ⭐ Serve perche'' l''unicita'' che regge il perimetro (ex_src_bancari_conto_incasso_un_solo_soggetto) vive SOLO sulle righe INCASSO: un ente appeso al conto dei pagamenti starebbe fuori da quella garanzia e nessuno se ne accorgerebbe. ⛔ NON guarda bloccato ne'' valido_al di proposito: sono stati che cambiano per ragioni che non riguardano questo ente, e rifiutare il blocco di un conto perche'' «c''e'' un ente che lo cita» sposterebbe l''errore sul gesto sbagliato. ⚠️ Legge sotto RLS ma la tabella puntata ce l''ha spenta: se un giorno entra sotto row security, va portata su SECURITY DEFINER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
