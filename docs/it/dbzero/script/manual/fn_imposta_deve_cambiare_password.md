## 📘 Documentazione Concettuale – Funzione `script.fn_imposta_deve_cambiare_password()`

> 👀 **Vedi anche**
>
> **Chi lo legge:** [fn_get_deve_cambiare_password](/dbzero/script/funzioni/fn_get_deve_cambiare_password)
>
> **Dove sta:** [config.credenziali](/dbzero/config/tabelle/credenziali)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Imposta (o toglie) l'obbligo di **cambiare la password** al prossimo accesso di
una credenziale. Se la credenziale non ha ancora una riga in `config.credenziali`,
la crea.

La chiamano l'invito di un operatore (che imposta l'obbligo) e il cambio
password, il reset e l'attivazione (che lo tolgono). Per questo non chiede un
permesso: alcuni di quei passi avvengono prima che la persona abbia fatto
l'accesso.

Utente inesistente → `E_CREDENZIALE_NON_TROVATA`.

---

### Storia

* 2026-09-25 — nasce (`20260925-08`).

{% include-markdown "signature-core.md" %}
