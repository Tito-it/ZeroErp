{% include-markdown "it/dbzero/ui/manual/fn_lista_da_codice.md" %}
# ⚙️ Funzione `fn_lista_da_codice`

```sql
CREATE FUNCTION fn_lista_da_codice(p_lista_codice character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_lista_da_codice(p_lista_codice character varying)
 RETURNS ui.lista_definizione
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la riga della lista con questo codice, se esiste ed e' attiva.
-- Lista assente o spenta: E_UI_LISTA_NON_TROVATA, col codice nella frase.
-- Sede unica della lettura per codice: il risolutore delle liste, la
-- ricerca libera e il backend (soglia della ricerca) passano da qui.
DECLARE
  v_lista ui.lista_definizione%ROWTYPE;
BEGIN
  SELECT ld.*
    INTO v_lista
    FROM ui.lista_definizione ld
   WHERE ld.codice = p_lista_codice
     AND ld.attivo = TRUE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.fn_lista_da_codice',
      'E_UI_LISTA_NON_TROVATA',
      jsonb_build_object('detail', format('codice lista: ''%s''', p_lista_codice)),
      NULL,
      p_lista_codice
    );
  END IF;

  RETURN v_lista;
END;
$function$

COMMENT ON FUNCTION ui.fn_lista_da_codice(p_lista_codice character varying)
IS 'La riga di ui.lista_definizione con questo codice, se esiste ed e'' attiva; altrimenti E_UI_LISTA_NON_TROVATA (il codice nella frase). Building block: sede unica della lettura di una lista per codice. La usano ui.fn_resolve_lista_config (id, multi_emittente, perimetro_emittente, ricerca_min_caratteri, da una lettura sola), ui.fn_lista_colonne_ricerca_full (id) e il building block di ricerca del backend, che ne legge la soglia: SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(codice). Brief: brief-db-be-fe-ricerca-soglia-per-lista.';
```

</div>

---
{% include-markdown "signature-core.md" %}
