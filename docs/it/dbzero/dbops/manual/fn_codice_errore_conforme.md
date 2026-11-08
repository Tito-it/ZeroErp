## 📘 Documentazione Concettuale – Funzione `dbops.fn_codice_errore_conforme`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.messaggi_errore_codici_legacy](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy) — il registro dei codici fuori convenzione, il cui CHECK chiama questa funzione
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — il catalogo dei codici che il guardrail misura con questa regola
>
> Guide:
>
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — la convenzione `E_` / `W_`

---

### 🎯 Scopo Principale

La convenzione dei nomi dei codici d'errore: dice se un codice comincia con `E_` (un errore, che
si solleva) o con `W_` (un avviso, che si scrive solo nel log) e prosegue con lettere maiuscole,
cifre e trattini bassi. Per un codice vuoto (`NULL`) risponde vuoto.

---

### ⭐ Una regola, una sede

È l'unico posto in cui la convenzione è scritta. La leggono due controlli, che così parlano dello
stesso insieme di codici per costruzione:

* il CHECK `chk_messaggi_errore_codici_legacy_non_conforme` di
  `dbops.messaggi_errore_codici_legacy`, che accetta nel registro solo i codici che la regola
  **non** rispetta: un codice conforme non è debito;
* il guardrail di CI `scripts/sql/guardrail_codice_errore_strutturato.sql`, che pretende che ogni
  codice vivo del catalogo fuori convenzione stia nel registro.

Cambiare la convenzione (per esempio allargarla a una famiglia nuova) vuol dire cambiare questa
funzione, e i due controlli la seguono insieme.

È `IMMUTABLE` perché entra in un CHECK: la risposta dipende solo dal testo del codice.

---

{% include-markdown "signature-core.md" %}
