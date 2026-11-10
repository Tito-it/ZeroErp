{% include-markdown "it/dbzero/dbops/manual/fn_conta_presidio_per_variante.md" %}
# ⚙️ Funzione `fn_conta_presidio_per_variante`

```sql
CREATE FUNCTION fn_conta_presidio_per_variante(p_vista text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_conta_presidio_per_variante(p_vista text)
 RETURNS TABLE(variante text, conteggio bigint)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_riga     dbops.presidi%ROWTYPE;
    v_schema   text;
    v_relname  text;
    v_filtro   text;
    v_sql      text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Contare le righe che CHIEDONO UN INTERVENTO su una vista
    --   di presidio, per gruppo della colonna che il catalogo
    --   dichiara come variante (la causa della riga),
    --   attraversando la row level security dove serve, e senza
    --   mai restituire le righe.
    --
    -- ⭐ E' la SEDE UNICA del conteggio dei presidi: perimetro,
    --   rifiuto e filtro di stato stanno qui e solo qui.
    --   dbops.fn_conta_presidio e' la somma di questi gruppi.
    --
    -- ⛔ Il perimetro e' il CATALOGO: una vista non dichiarata
    --   non si conta. E' cio' che impedisce a questa funzione di
    --   diventare una porta per contare qualunque relazione del
    --   database aggirando la row level security.
    -- =========================================================

    -- ⚠️ Il NULL cade nello stesso ramo del nome sconosciuto, ed
    --   e' voluto: `vista = NULL` non trova niente. UN SOLO SITO
    --   CHE SOLLEVA.
    SELECT * INTO v_riga
      FROM dbops.presidi
     WHERE vista = p_vista
       AND attivo
       AND obsoleto_dal IS NULL;

    -- ⚠️ SELECT INTO senza righe NON solleva: il controllo va
    --   scritto, o si prosegue su un catalogo che non ha risposto.
    IF NOT FOUND THEN
        -- ⛔ Nel VARIADIC il NOME DELLA VISTA CHIESTA, la cosa
        --   che una persona riconosce; il ripiego serve al NULL.
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'fn_conta_presidio_per_variante',
            'E_PRESIDIO_NON_A_CATALOGO',
            jsonb_build_object('vista', p_vista),
            NULL::uuid,
            coalesce(nullif(btrim(p_vista), ''), '(nessuna vista indicata)'));
    END IF;

    v_schema  := split_part(v_riga.vista, '.', 1);
    v_relname := split_part(v_riga.vista, '.', 2);

    -- ⭐ Il filtro di stato, scritto UNA volta per i due rami.
    --   ⛔ Si conta «DIVERSO DALLO STATO ATTESO», non «uguale a
    --   uno degli stati di allarme»: uno stato NUOVO aggiunto
    --   domani alla vista cade cosi' nell'allarme invece che nel
    --   silenzio.
    --   ⚠️ IS DISTINCT FROM e non <>: un NULL nella colonna di
    --   stato e' «non atteso», e con <> la riga uscirebbe dal
    --   conteggio in silenzio.
    --   ⚠️ Senza colonna_stato il $1 resta inusato: EXECUTE …
    --   USING ne prende il tipo dal valore, non lo deduce.
    v_filtro := CASE
                    WHEN v_riga.colonna_stato IS NULL THEN ''
                    ELSE format(' WHERE %I IS DISTINCT FROM $1',
                                v_riga.colonna_stato)
                END;

    -- ⛔ SQL dinamico con %I, mai per concatenazione di nomi: i
    --   nomi vengono da una tabella, e una tabella si scrive.
    IF v_riga.colonna_variante IS NULL THEN
        -- Presidio senza variante: SENZA GROUP BY l'aggregato
        -- torna sempre UNA riga, anche a zero (contratto 3).
        v_sql := format('SELECT NULL::text, count(*) FROM %I.%I',
                        v_schema, v_relname)
                 || v_filtro;
    ELSE
        -- ⚠️ ::text perche' la colonna della vista puo' avere un
        --   tipo suo, e la variante a catalogo e' testo.
        -- ⭐ GROUP BY tiene il NULL come gruppo a se' (contratto
        --   4): non si fonde e non si perde.
        -- ⚠️ ORDER BY per una risposta stabile; il NULL in coda.
        v_sql := format('SELECT %I::text, count(*) FROM %I.%I',
                        v_riga.colonna_variante, v_schema, v_relname)
                 || v_filtro
                 || ' GROUP BY 1 ORDER BY 1 NULLS LAST';
    END IF;

    RETURN QUERY EXECUTE v_sql USING v_riga.stato_atteso;
END
$function$

COMMENT ON FUNCTION dbops.fn_conta_presidio_per_variante(p_vista text)
IS 'Conta le righe che CHIEDONO UN INTERVENTO su una vista di presidio dichiarata in dbops.presidi, raggruppate per il valore della colonna nominata da dbops.presidi.colonna_variante (la causa della riga): una riga per valore presente, il NULL come gruppo a se''. Presidio senza colonna_variante: una riga sola, variante NULL, il conteggio intero anche a zero. E'' la sede unica del conteggio dei presidi: perimetro (catalogo, altrimenti E_PRESIDIO_NON_A_CATALOGO) e filtro di stato (colonna_stato IS DISTINCT FROM stato_atteso) stanno qui; dbops.fn_conta_presidio ne e'' la somma, cosi'' le due risposte non possono divergere. SECURITY DEFINER del proprietario, non di un superuser, con search_path pg_catalog, pg_temp: le viste security_invoker su tabelle in row level security, lette da un percorso senza GUC di sessione (un management command), tornerebbero zero per cecita''. E'' l''unico punto che attraversa la RLS: dbops.fn_conta_presidio e'' INVOKER e passa da qui. ⛔ Torna NUMERI per gruppo e mai le righe; il valore del gruppo e'' un codice di catalogo (dbops.presidi_cause), non un dato di dominio. Lettori: il digest (raggruppa per chi agisce della causa) e il pannello (conteggio accanto a ogni causa).';
```

</div>

---
{% include-markdown "signature-core.md" %}
