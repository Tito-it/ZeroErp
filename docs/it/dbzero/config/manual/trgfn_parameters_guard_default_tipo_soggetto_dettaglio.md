# Funzione `config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()` (DEPRECATA)

## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()`

> ⚠️ **DEPRECATA dal 2026-05-02** — DROP applicato in migration
> `20260502-07`. Sostituita dal framework FK-surrogata parametrico:
>
> * Registry: [config.parameter_fk_surrogate](/dbzero/config/manual/parameter_fk_surrogate)
> * Dispatcher su parameters: [config.trgfn_parameters_fk_surrogate_dispatch](/dbzero/config/manual/trgfn_parameters_fk_surrogate_dispatch)
> * Dispatcher su parameter_overrides: [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/manual/trgfn_parameter_overrides_fk_surrogate_dispatch)
>
> Pagina mantenuta come **pointer storico**: documenta il guard ad-hoc che ha
> introdotto il vincolo (sessione 2026-04-27, brief BE opzione B). Il vincolo
> sui parametri `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>` e' ora applicato dal
> dispatcher generico letto dal registry (riga seed con
> `code_pattern = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` e
> `match_mode = 'LIKE'` -> `config.tipi_soggetto_dettaglio.codice_interno`).
>
> **Codice errore**: passato da `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID`
> (id 399, deprecato ma mantenuto in `config.messaggi_errore` per non
> rompere chi lo referenzia) a `E_PARAMETER_DEFAULT_VALUE_INVALID` (id 422,
> generico con `target` nel context JSONB).
>
> Il principio architetturale "FK-surrogata via codice_interno" e' ora
> formalizzato in
> [linee-guida-sql §6b](/it/linee-guida-sql.md#6b-riferimenti-esterni-a-tabelle-di-catalogo-chiave-naturale-stabile).

### Storia

(creata 2026-04-27, deprecata 2026-05-02)

Primo guard ad-hoc per il pattern `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>`.
Aveva clausola WHEN hard-coded sul prefisso e non scattava sugli override in
`config.parameter_overrides` (lacuna nota documentata).

Quando si e' presentato il secondo caso d'uso (DEFAULT_UTILITY, sessione
2026-05-02) si e' colta l'occasione per generalizzare anziche' duplicare:
e' nato il framework parametrico che assorbe questo guard come riga di
configurazione.

### Equivalenza funzionale

| Aspetto | Guard ad-hoc (dropped) | Dispatcher framework (current) |
| --- | --- | --- |
| Trigger | `trg_parameters_a10_guard_default_tipo_soggetto_dettaglio_ins_upd` | `trg_parameters_a10_fk_surrogate_dispatch_ins_upd` |
| Function | `config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio` | `config.trgfn_parameters_fk_surrogate_dispatch` |
| Filtro pattern | WHEN hard-coded `LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'` | Lookup runtime su `parameter_fk_surrogate` (riga LIKE) |
| Lookup target | Hard-coded `tipi_soggetto_dettaglio.codice_interno` | Letto da registry |
| Override `parameter_overrides` | Non gestito | Coperto da dispatcher speculare |
| Codice errore | `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` (399) | `E_PARAMETER_DEFAULT_VALUE_INVALID` (422) |

---

{% include-markdown "signature-core.md" %}

---
