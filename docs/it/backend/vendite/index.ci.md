# Area 'vendite' (Backend)

## API
- [api_listini](manual/api_listini.md) — Esporre via HTTP la gestione completa dei listini vendite: anagrafica, versioni, righe prezzo, associazioni e test del resolver.
- [api_run_lotto_pipeline](manual/api_run_lotto_pipeline.md) — Esporre via HTTP l'avvio della pipeline lotto vendite.
- [api_reset_lotto_draft](manual/api_reset_lotto_draft.md) — Esporre via HTTP il reset tecnico di un lotto MASSIVO in DRAFT.

## Funzioni
- [fn_execute_pipeline_step](funzioni/fn_execute_pipeline_step.md) — Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.
- [run_lotto_pipeline](funzioni/run_lotto_pipeline.md) — Orchestrare l'esecuzione della pipeline di fatturazione per un lotto.

## Altri contenuti
- [fn_generate_fatture_righe](manual/fn_generate_fatture_righe.md) — Generare in Django le righe fattura a partire da attivita_fatturabili lockate sul lotto.
- [fn_group_attivita_fatturabili](manual/fn_group_attivita_fatturabili.md) — Costruire in Django la chiave di aggregazione delle attivita fatturabili.
- [fn_prepare_sdi_payload_lotto](manual/fn_prepare_sdi_payload_lotto.md) — Reperire il dataset SDI del lotto dal DB con apertura/riuso tentativi.
- [fn_reset_lotto_draft](manual/fn_reset_lotto_draft.md) — Reset tecnico lotto DRAFT tramite wrapper Django.
- [fn_reset_lotto_fattura_draft](manual/fn_reset_lotto_fattura_draft.md) — Reset tecnico singola fattura in lotto DRAFT tramite wrapper Django.
- [api_reset_lotto_fattura_draft](manual/api_reset_lotto_fattura_draft.md) — Endpoint reset singola fattura in lotto DRAFT.
- [template_contratto_iniziale](manual/template_contratto_iniziale.md) — Template HTML iniziale per la generazione PDF di un contratto commerciale tramite context builder CONTRATTO.
