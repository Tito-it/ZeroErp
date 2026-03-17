## 📘 Documentazione Concettuale – Tabella `vendite.attivita_consumi`

> ⚠️ **Work in progress**
>
Questa tabella e` in evoluzione: i dettagli varieranno per utility (gas, energia, acqua).
>
👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)  
>
🎯 Scopo Principale

(latest review 24-01-2026)
`vendite.attivita_consumi` rappresenta la **testata consumi** per utilities,
con totalizzatori e periodi di riferimento. E` il punto di aggregazione
per dettagli futuri (fasce, minimi, tipologie energia, ecc.) e puo` essere
collegata alla fattura in emissione.

---

### Campi chiave (semantica)

* **Identita`**: `id`, `uid` (per idempotenza/sorgente).
* **Legami**: `lotto_attivita_id`, `fattura_id`, `billing_account_id`.
* **Periodo**: `competenza_mese`, `periodo_dal`, `periodo_al`.
* **Consumi**: `consumo_totale`, `uom_id`.
* **Esito calcolo**: `stato_calcolo` (OK | WARNING | ERRORE).
* **Governance**: `meta`, `storicizza`, `tx_id`, audit.

---

### Note operative

* Le righe `attivita_fatturabili` possono collegarsi a questa testata tramite `attivita_consumi_id`.
* In futuro verranno aggiunte tabelle di dettaglio per utility specifiche.

---

{% include-markdown "signature-core.md" %}
