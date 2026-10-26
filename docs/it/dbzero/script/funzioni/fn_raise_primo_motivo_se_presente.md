# ⚙️ Funzione `fn_raise_primo_motivo_se_presente`

```sql
CREATE FUNCTION fn_raise_primo_motivo_se_presente(p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_raise_primo_motivo_se_presente(p_area text, p_funzione text, p_motivi jsonb, p_campo text DEFAULT NULL::text, p_tx_id uuid DEFAULT NULL::uuid, p_context_extra jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    -- ⛔ I primi due NUDI: `v_primo` e' un elemento di `p_motivi` e
    --   `v_valori` una sua chiave — entrambi pezzi di un jsonb che
    --   viene da una funzione, non da una tabella.
    v_primo   jsonb;
    v_valori  jsonb;
    -- ⭐ Questo invece E' il contesto, e la colonna che lo ospita
    --   esiste: si ancora.
    v_context dbops.error_log.context%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Sollevare il codice del PRIMO motivo di una fn_check_*,
    --   in un posto solo. Chi chiama passa l'array come gli e'
    --   tornato dalla check e non tocca ne' l'indice, ne' lo
    --   spacchettamento dei valori, ne' la forma del contesto.
    --
    -- ⭐ TACE SU UN ARRAY VUOTO, e non e' fail-open: «nessun
    --   motivo» e' esattamente la risposta che dice *passa*.
    --   Cosi' il sito chiamante perde anche l'IF e diventa una
    --   riga sola. Il suffisso `_se_presente` nel nome esiste
    --   per questo: linee-guida-sql §5 vieta un `raise` che a
    --   volte non solleva senza dirlo dal nome.
    --
    -- ⛔ NON NORMALIZZA IL MOTIVO. Prende il primo elemento e lo
    --   passa. Se un giorno servisse sollevarne un altro, la
    --   regola da cambiare e' l'ORDINE DELL'ARRAY NELLA CHECK,
    --   che e' dove il contratto vive (§12.5.2).
    -- =========================================================

    -- ⚠️ DUE uscite, non tre, e la terza e' stata TOLTA di
    --   proposito. NULL e array vuoto sono «nessun motivo»: e'
    --   la risposta che dice *passa*, ed e' cio' che i ventitre'
    --   siti facevano gia'.
    -- ⛔ Un NON-array invece e' un CONTRATTO ROTTO della check, e
    --   deve restare RUMOROSO: jsonb_array_length gli alza 22023
    --   da solo, esattamente come succedeva prima di questa
    --   estrazione. Una riga `jsonb_typeof(...) <> 'array'` in
    --   piu' l'avrebbe reso SILENZIOSO — cioe' avrebbe scambiato
    --   un guasto per un «passa», togliendo un rifiuto senza far
    --   fallire niente. E' la stessa classe di difetto che questo
    --   cantiere esiste per chiudere: un guard non si allarga
    --   «per igiene».
    IF p_motivi IS NULL OR jsonb_array_length(p_motivi) = 0 THEN
        RETURN;
    END IF;

    v_primo := p_motivi -> 0;

    -- ⛔ Normalizzazione sul TIPO e non con COALESCE, ed e' la
    --   differenza che conta: `-> 'valori'` su una chiave
    --   ASSENTE torna SQL NULL (e COALESCE lo vede), ma su una
    --   chiave che porta `null` JSON torna 'null'::jsonb — che
    --   COALESCE NON vede e che fa alzare a
    --   jsonb_array_elements_text un 22023 «cannot extract
    --   elements from a scalar». Quell'errore scatterebbe QUI
    --   dentro, quindi il RAISE di dominio non verrebbe mai
    --   eseguito: si perderebbe il rifiuto, non solo la frase.
    v_valori := CASE
        WHEN jsonb_typeof(v_primo -> 'valori') = 'array'
            THEN v_primo -> 'valori'
        ELSE '[]'::jsonb
    END;

    -- ⭐ L'ORDINE DI FUSIONE E' UNA DECISIONE, non un accidente:
    --   in jsonb `||` vince la DESTRA. Qui vince `p_campo`, poi
    --   `motivi`, poi il `dettaglio` della check, poi le chiavi
    --   di dominio del chiamante.
    -- ⚠️ Nei siti vivi convivevano i due ordini opposti: due
    --   guard mettevano `campo` a sinistra (quindi a vincere era
    --   `dettaglio`) e otto a destra. Non falliva mai, e si
    --   sarebbe visto solo il giorno in cui un `dettaglio` porta
    --   una chiave `campo`. Si chiude qui, dichiarandolo.
    -- ⚠️ `p_context_extra` in fondo a sinistra e' anche il
    --   canale con cui passano `reason` (il motivo macchina che
    --   il frontend legge sulle azioni di riga), `bersaglio`
    --   (canale DATATYPE) e `parametro` (il ripiego del canale
    --   COLUMN in fn_log_and_raise_error).
    v_context := COALESCE(p_context_extra, '{}'::jsonb)
        || CASE
               WHEN jsonb_typeof(v_primo -> 'dettaglio') = 'object'
                   THEN v_primo -> 'dettaglio'
               ELSE '{}'::jsonb
           END
        -- ⭐ L'ELENCO COMPLETO viaggia SEMPRE, anche quando la
        --   frase ne nomina uno: e' cio' che permette al backend
        --   di mostrarli tutti. Quindici dei ventitre' siti lo
        --   portavano gia'; qui smette di essere una scelta per
        --   sito e diventa il contratto dell'helper.
        || jsonb_build_object('motivi', p_motivi);

    -- ⚠️ `campo` entra SOLO se il chiamante lo passa. Su un
    --   errore di classe TECNICO non c'e' nessun campo da
    --   accendere, e promettere al frontend un input che non
    --   esiste e' peggio che non dirgli niente.
    IF p_campo IS NOT NULL THEN
        v_context := v_context || jsonb_build_object('campo', p_campo);
    END IF;

    -- ⚠️ Il VARIADIC si passa SEMPRE, anche vuoto: chiamata a
    --   cinque argomenti, fn_log_and_raise_error non risolve.
    PERFORM script.fn_log_and_raise_error(
        p_area,
        p_funzione,
        v_primo ->> 'codice',
        v_context,
        p_tx_id,
        VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_valori)));
END;
$function$

COMMENT ON FUNCTION script.fn_raise_primo_motivo_se_presente(p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb)
IS 'Solleva il codice del PRIMO motivo di una fn_check_*, in un posto solo. Tace - e non e'' fail-open - se p_motivi e'' NULL, non e'' un array o e'' vuoto: «nessun motivo» e'' la risposta che dice passa, e il suffisso _se_presente lo dichiara dal nome (linee-guida-sql §5). Estratta il 2026-09-08 da ventitre'' punti di chiamata che ripetevano la stessa coda: le righe risparmiate sono un effetto collaterale, il motivo sono le tre convenzioni che sbagliate non fanno fallire niente - quale elemento si solleva (l''ordine dell''array e'' il contratto, §12.5.2), quale tx_id si passa (dipende dalla fase E dal nome del trigger) e come si spacchetta il VARIADIC (arita'' giusta, frase falsa). Contesto composto in ordine DICHIARATO, e in jsonb || vince la destra: p_context_extra || dettaglio || motivi || campo. `motivi` viaggia SEMPRE (il backend puo'' mostrarli tutti anche se la frase ne nomina uno); `campo` solo se passato (su un TECNICO non c''e'' nessun campo da accendere). `valori` normalizzato sul TIPO e non con COALESCE: una chiave con null JSON non e'' SQL NULL e farebbe alzare 22023 a jsonb_array_elements_text DENTRO il percorso d''errore, perdendo il rifiuto e non solo la frase. ⛔ NON difende dall''ordine dei valori dentro la check, che e'' l''incidente del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA: quella difesa e'' un throws_like sulla frase resa. Brief: brief-db-coda-primo-motivo-in-un-posto-solo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
