## 📘 Documentazione Concettuale – Funzione `script.fn_credenziale_ha_vesti()`

> 👀 **Vedi anche**
>
> **Chi la legge:** [vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) ·
> [fn_check_credenziale_eliminabile](/dbzero/script/funzioni/fn_check_credenziale_eliminabile)

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

Risponde a una domanda sola: **questa credenziale ha almeno una veste?** Conta
anche una veste spenta.

È la regola che decide due cose, e per questo sta in un posto solo:

* quali credenziali la scheda «Altri accessi» e il presidio delle credenziali da
  sanare mostrano come **senza nessun accesso**;
* quali credenziali **non si possono eliminare**.

---

### Storia

* 2026-10-06 — nasce (`20261006-11`). Brief: brief-db-elimina-credenziale-senza-veste.

{% include-markdown "signature-core.md" %}
