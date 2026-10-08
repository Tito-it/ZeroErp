# ⚙️ Funzione `fn_check_soggetto_ruolo_visibile`

```sql
CREATE FUNCTION fn_check_soggetto_ruolo_visibile(p_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_soggetto_ruolo_visibile(p_soggetto_ruolo_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Convenzione fn_check_*: pura, boolean, nessun raise.
    -- ⚠️ Il perimetro dei clienti NON e' scritto qui: lo applica la
    --   RLS di anagrafiche.clienti (rls_clienti_ef_whitelist per
    --   l'operatore, le due vesti cliente per portale e shop).
    --   Questa funzione chiede solo «ne resta almeno uno?».
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.soggetti_ruoli sr
          JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
         WHERE sr.id = p_soggetto_ruolo_id
           AND (tr.codice_interno <> 'CL'
                OR EXISTS (SELECT 1
                             FROM anagrafiche.clienti cl
                            WHERE cl.soggetto_ruolo_id = sr.id)))
$function$

COMMENT ON FUNCTION script.fn_check_soggetto_ruolo_visibile(p_soggetto_ruolo_id bigint)
IS 'Check pura (boolean, nessun raise): il soggetto-ruolo si mostra a chi guarda nella ricerca universale? Ruolo CL: si'' se ha almeno un cliente che la RLS di anagrafiche.clienti gli restituisce — il perimetro dell''emittente sta nella policy, qui non si ripete. Altri ruoli: si'' se il soggetto-ruolo esiste — soggetti, soggetti_ruoli e fornitori non portano un emittente nel modello, quindi non c''e'' un perimetro da applicare (scelta di modello, non residuo). Soggetto-ruolo inesistente o NULL: false. SECURITY INVOKER: la RLS vale con l''identita'' di chi chiama. Lettori: script.fn_search_soggetti_universale (filtro di riga) e script.fn_get_search_detail (verifica d''esistenza): lista e dettaglio non possono dissentire su chi si vede. ⚠️ Effetto voluto: un soggetto-ruolo CL senza nessun cliente non compare per nessuno, nemmeno per il super admin. Nasce il 2026-10-08, brief-db-codici-non-trovato-email-e-permessi §5 (R-4, decisione di Tid).';
```

---
{% include-markdown "signature-core.md" %}
