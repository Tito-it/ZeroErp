# Brief DB — Contratti: simmetria emittente fiscale con preventivi/offerte

> **Status**: 🆕 WIP — 2026-05-26
> **Target team**: DB (`dev/db-tid`)
> **Origine**: allineamento UI drawer contratti (sezione emittente + utility) a `OffertaDrawer` / `PreventiviForm`
> **No produzione**: breaking change ammessi (memoria `project_no_produzione_solo_sviluppo`)

---

## Richiesta

Portare `vendite.contratti` allo stesso modello emittente fiscale di `vendite.preventivi` e `vendite.offerte`:

- Aggiungere colonna **`emittente_fiscale_id`** su `vendite.contratti`, NOT NULL, FK ad `anagrafiche.emittenti_fiscali`.
- Valorizzazione a INSERT-time via trigger (stesso pattern preventivi/offerte: GUC `app.current_user_id` → `fn_resolve_emittente_for_user`, con fallback derivato dal BA via `anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)`).
- Guard di coerenza BA ↔ emittente fiscale (l'emittente del contratto deve coincidere con quello derivabile dal BA scelto).
- Scope permessi: il filtro lista contratti per emittente passa da derivato a diretto (semplificazione vista/select repo, simmetrico a `vw_preventivi_list`).
- Backfill record esistenti (ZeroErp non in produzione, ok update massivo via `fn_get_emittente_fiscale_pk`).

## Motivazione

Oggi sulla testata contratto l'emittente non è persistito né esposto in API. La UI drawer non lo mostra → asimmetria rispetto a preventivi/offerte che già lo trattano come colonna nativa + scope diretto. La simmetria piena evita la deviazione "campo display-only derivato" sulla UI e azzera il fork nello scope permessi.

## Fuori scope

Modifiche a `vendite.contratti_righe`, `contratti_utilities`, `contratti_righe_componenti`: l'emittente sta solo in testata.

---

*Brief DB sintetico — il dettaglio implementativo (nome migration, trigger, test pgTAP, ordine apply) è a discrezione del team DB.*
