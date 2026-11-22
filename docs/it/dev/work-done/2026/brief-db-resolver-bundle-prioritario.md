# Brief DB — Resolver bundle prioritario su standalone

> **Data**: 2026-05-13 sera
>
> **Branch**: `dev/db-tid`
>
> **Tipo**: bug logico modello — **priorita' MASSIMA** (bloccante per workflow listino composito → preventivo)
>
> **Funzione da modificare**: `vendite.fn_resolve_prezzo_listino_v2` (rev 2026-05-13, file 20260513-22).

---

## Sintomo

Workflow utente reale (testato 2026-05-13):

1. Listino "sadasdfa" mappato alla categoria cliente BASE via `categorie_clienti_listini`.
2. Versione listino ATTIVA con prezzi bundle definiti in `listini_righe_componenti`
   per i componenti dell'articolo composito `art-comp-001`.
3. **Nessuna riga standalone** su `listini_righe` per i componenti (perche' i prezzi
   componenti vivono solo in contesto bundle — caso d'uso legittimo del modello unificato).
4. Preventivo per cliente BAC/0000053 (categoria BASE) con riga `art-comp-001` →
   `fn_preventivo_riga_componenti_init` chiama `fn_resolve_prezzo_listino_v2`
   per ogni componente con `p_articolo_padre_contesto = art-comp-001`.
5. **Errore**: `E_PREZZO_LISTINO_RIGA_NON_TROVATA` con `origine_stadio='CATEGORIA'`,
   payload `{articolo_id: componente_uuid, uom_id, listino_id}`.

## Causa

`fn_resolve_prezzo_listino_v2` cerca **prima** la riga standalone `listini_righe`
per il componente, e solleva `E_PREZZO_LISTINO_RIGA_NON_TROVATA` quando non la trova.
Solo **dopo** quel check tenta lo STADIO BUNDLE su `listini_righe_componenti`.

Estratto attuale STADIO 2 — categoria (file 20260513-22, righe 388-444):

```sql
-- STADIO 2: cerca listini_righe standalone del componente
SELECT lv.id, lr.id, lr.prezzo
  INTO v_listino_versione_id, v_listino_riga_id, v_prezzo_base
  FROM vendite.listini_versioni lv
  JOIN vendite.listini_righe lr
    ON lr.listino_versione_id = lv.id
 WHERE lv.listino_id    = v_matrice_listino_id
   AND lv.validita     @> p_data_riferimento
   AND lv.attivo        = TRUE
   AND lr.articolo_id   = p_articolo_id  -- ← componente, non padre
   AND lr.uom_id        = p_uom_id
   AND lr.attivo        = TRUE
 LIMIT 1;

IF v_listino_riga_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(   -- ← FALLISCE QUI
        'vendite',
        'fn_resolve_prezzo_listino_v2',
        'E_PREZZO_LISTINO_RIGA_NON_TROVATA',
        ...
    );
END IF;

v_listino_id := v_matrice_listino_id;

-- STADIO BUNDLE: mai raggiunto se sopra ha fallito ← BUG
IF p_articolo_padre_contesto IS NOT NULL AND NOT v_bundle_used THEN
    SELECT lrc.id, lrc.prezzo ...
    FROM vendite.listini_righe_componenti lrc
    WHERE ...
    IF FOUND THEN
        v_origine := 'LISTINO_BUNDLE';
        v_bundle_used := TRUE;
    END IF;
END IF;
```

Lo stesso pattern e' replicato in STADIO 1 — contratto (righe 255-309): il check
`v_listino_riga_id IS NULL` solleva `E_PREZZO_LISTINO_RIGA_NON_TROVATA` con
`origine_stadio='CONTRATTO_LISTINO'` PRIMA del lookup bundle.

## Conseguenza per l'utente

L'admin e' costretto a definire **sia** una riga standalone in `listini_righe`
**sia** una riga bundle in `listini_righe_componenti` per ogni componente —
duplicazione obbligata. Il modello unificato BoM 2026-05-13 prevede esplicitamente
che i prezzi bundle siano l'unica sorgente per componenti che vivono solo
all'interno di compositi; la duplicazione contraddice la decisione di modello.

## Correzione richiesta

**Quando `p_articolo_padre_contesto IS NOT NULL`**, il resolver deve:

1. Determinare `v_listino_versione_id` (versione listino ATTIVA del listino eletto
   dal contratto o dalla categoria) **senza** richiedere una riga standalone.
2. Tentare lo STADIO BUNDLE su `listini_righe_componenti` per la coppia
   `(padre_contesto, articolo)` nella versione determinata.
3. Se BUNDLE trova → usa quel prezzo, `v_origine='LISTINO_BUNDLE'`, esce.
4. Se BUNDLE non trova → **solo allora** fallback su `listini_righe` standalone
   del componente (caso di componente che ha sia bundle override sia un prezzo
   standalone d'eccezione — raro ma legittimo).
5. Se nemmeno standalone → solleva `E_PREZZO_LISTINO_RIGA_NON_TROVATA` come oggi,
   ma con `detail` che indica entrambi i path falliti.

**Quando `p_articolo_padre_contesto IS NULL`** (resolver standalone tradizionale):
nessun cambio, comportamento attuale invariato.

### Schema della logica corretta (STADIO 2 — categoria)

```sql
-- 1. Determina v_listino_versione_id dalla matrice categoria
SELECT lv.id
  INTO v_listino_versione_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = v_matrice_listino_id
   AND lv.validita  @> p_data_riferimento
   AND lv.attivo    = TRUE
 LIMIT 1;

IF v_listino_versione_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_resolve_prezzo_listino_v2',
        'E_LISTINO_VERSIONE_NON_ATTIVA',  -- nuovo codice o riusare esistente
        jsonb_build_object(
            'listino_id', v_matrice_listino_id,
            'data_riferimento', p_data_riferimento,
            'origine_stadio', 'CATEGORIA'
        )
    );
END IF;

v_listino_id := v_matrice_listino_id;

-- 2. STADIO BUNDLE prioritario (se padre_contesto)
IF p_articolo_padre_contesto IS NOT NULL THEN
    SELECT lrc.id, lrc.prezzo
      INTO v_bundle_riga_id, v_bundle_prezzo
      FROM vendite.listini_righe_componenti lrc
     WHERE lrc.listino_versione_id   = v_listino_versione_id
       AND lrc.articolo_padre_id     = p_articolo_padre_contesto
       AND lrc.articolo_figlio_id    = p_articolo_id
       AND lrc.validita             @> p_data_riferimento
       AND lrc.attivo                = TRUE
     LIMIT 1;
    IF FOUND THEN
        v_prezzo_base   := v_bundle_prezzo;
        v_prezzo_finale := v_bundle_prezzo;
        v_origine       := 'LISTINO_BUNDLE';
        v_bundle_used   := TRUE;
        -- esce dallo STADIO 2, non cerca standalone
    END IF;
END IF;

-- 3. Fallback STANDALONE (se non bundle, o senza padre_contesto)
IF NOT v_bundle_used THEN
    SELECT lr.id, lr.prezzo
      INTO v_listino_riga_id, v_prezzo_base
      FROM vendite.listini_righe lr
     WHERE lr.listino_versione_id = v_listino_versione_id
       AND lr.articolo_id         = p_articolo_id
       AND lr.uom_id              = p_uom_id
       AND lr.attivo              = TRUE
     LIMIT 1;

    IF v_listino_riga_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_resolve_prezzo_listino_v2',
            'E_PREZZO_LISTINO_RIGA_NON_TROVATA',
            jsonb_build_object(
                'origine_stadio', 'CATEGORIA',
                'bundle_tentato', p_articolo_padre_contesto IS NOT NULL,
                'articolo_padre_contesto', p_articolo_padre_contesto,
                ...
            )
        );
    END IF;
    -- ... applicazione variazione categoria come oggi ...
END IF;
```

Specchio identico in STADIO 1 — contratto (riga 255-309 originale).

## Test attesi (pgTAP)

Casi da coprire dopo la migration di fix:

1. Solo bundle definito, niente standalone, padre_contesto fornito → `v_origine='LISTINO_BUNDLE'`, nessun errore.
2. Solo standalone definito, padre_contesto NULL → comportamento attuale (standalone trovato, origine `CATEGORIA`/`CONTRATTO_LISTINO`).
3. Solo standalone definito, padre_contesto fornito ma BUNDLE non trovato → fallback standalone, origine `CATEGORIA`/`CONTRATTO_LISTINO`.
4. Niente ne' bundle ne' standalone → `E_PREZZO_LISTINO_RIGA_NON_TROVATA` con `bundle_tentato=true` nel detail.
5. Versione listino non ATTIVA alla data → nuovo errore `E_LISTINO_VERSIONE_NON_ATTIVA` (o riusare esistente).

## Migration file

Proposta nome: `20260514-NN-update-fn-resolve-prezzo-listino-v2-bundle-prioritario-mctit.yaml`
con `runOnChange: true`, sostituisce il body di `fn_resolve_prezzo_listino_v2`
mantenendo la stessa signature.

## Riferimenti

- File attuale: `db/changelog/migrations_v2/20_code/vendite/20260513-22-update-fn-resolve-prezzo-listino-v2-bundle-aware-mctit.yaml`
- Modello: `docs/it/dev/manual/modello-componenti-bom.md` §8 (listino bundle)
- Decisione: `docs/it/dev/manual/changelog-decisioni-componenti.md` (sezione "BoM contratto immutabile" e modello unificato)
