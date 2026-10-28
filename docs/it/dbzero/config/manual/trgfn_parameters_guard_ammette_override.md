## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameters_guard_ammette_override()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
>
Approfondimento funzioni:
> [config.trgfn_parameter_overrides_guard_ammette_override](/dbzero/config/funzioni/trgfn_parameter_overrides_guard_ammette_override) — il gemello
>
Guida:
> [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri) — le due famiglie di parametri

### 🎯 Scopo Principale

(scritta il 25-10-2026)

Un parametro con override non diventa «uguale per tutti» (`ammette_override` da `true` a `false`)
finché ne ha, accesi o spenti: resterebbero righe che nessuno legge più. Il rifiuto è
`E_PARAMETER_OVERRIDE_PRESENTI`, con il numero degli override. Il verso `false` → `true` passa
sempre: aprire una famiglia non lascia orfani.

La applica il trigger `trg_parameters_a10_guard_ammette_override_upd`
(`BEFORE UPDATE OF ammette_override`).

### Chi lo attraversa

I mirror dei CSV dei parametri scrivono la colonna a ogni risveglio. Se un parametro dichiarato
senza override nel CSV ha ancora override sul database, il migrate si ferma qui: il rimedio è
togliere gli override (erano già ignorati), non il guard.

### Storia

* 2026-10-25 — nasce (`20261025-85`), brief-db-parametri-senza-override.

{% include-markdown "signature-core.md" %}
