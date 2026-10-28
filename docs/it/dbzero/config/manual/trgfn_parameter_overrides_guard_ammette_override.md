## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameter_overrides_guard_ammette_override()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [config.parameters](/dbzero/config/tabelle/parameters)
>
Approfondimento funzioni:
> [config.trgfn_parameters_guard_ammette_override](/dbzero/config/funzioni/trgfn_parameters_guard_ammette_override) — il gemello inverso
> [config.trgfn_parameter_overrides_fk_surrogate_dispatch](/dbzero/config/funzioni/trgfn_parameter_overrides_fk_surrogate_dispatch)
>
Guida:
> [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri) — le due famiglie di parametri

### 🎯 Scopo Principale

(scritta il 25-10-2026)

Rifiuta un override su un parametro che **vale per tutti**
(`config.parameters.ammette_override = false`), con `E_PARAMETER_OVERRIDE_NON_AMMESSO`.
Prima l'override veniva accettato e poi ignorato: chi legge quei parametri guarda il default, e chi
scriveva l'override credeva di aver cambiato qualcosa.

La applica il trigger `trg_parameter_overrides_a05_guard_ammette_override_ins_upd`
(`BEFORE INSERT OR UPDATE OF parameter_id`).

### Le scelte

* **Qualunque riga, anche spenta.** Un override con `attivo = false` si riaccende con un `UPDATE` di
  `attivo`, che questo trigger non vede: su un parametro senza override non deve esistere nessuna
  riga.
* **Fase `a05`, prima del dispatcher FK-surrogata (`a10`).** Su un parametro del registro con un
  valore che il catalogo non conosce parlerebbero in due. Se il parametro non si personalizza, dire
  «il valore non esiste» manda l'operatore a correggere il valore: parla prima questo guard.
* **Parametro assente**: passa, e lo giudica la FK `fk_overrides_parameter`.

### Storia

* 2026-10-25 — nasce (`20261025-84`), brief-db-parametri-senza-override.

{% include-markdown "signature-core.md" %}
