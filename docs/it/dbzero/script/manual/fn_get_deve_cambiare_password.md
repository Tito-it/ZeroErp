## 📘 Documentazione Concettuale – Funzione `script.fn_get_deve_cambiare_password()`

> 👀 **Vedi anche**
>
> **Chi lo scrive:** [fn_imposta_deve_cambiare_password](/dbzero/script/funzioni/fn_imposta_deve_cambiare_password)
>
> **Dove sta:** [config.credenziali](/dbzero/config/tabelle/credenziali)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Dice se una credenziale **deve cambiare la password** al prossimo accesso.

È della credenziale e non della porta: la password è una sola. Una credenziale
che non ha una riga in `config.credenziali` risponde **no**, e questa funzione è
l'unico posto dove quel «no» è scritto. La chiamano il profilo utente
(`fn_get_user_profile`), il dettaglio operatore (`fn_get_operatore_detail`) e il
backend.

---

### Storia

* 2026-09-25 — nasce (`20260925-07`); prima il flag stava su ogni riga di
  `identita_digitali`.

{% include-markdown "signature-core.md" %}
