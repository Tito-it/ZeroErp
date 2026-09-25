## 📘 Documentazione Concettuale – Funzione `script.fn_login_parametri()`

> 👀 **Vedi anche**
>
> **Il modello:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **La formula dell'attesa:** [fn_login_attesa_secondi](/dbzero/script/funzioni/fn_login_attesa_secondi)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Legge in una volta sola i **cinque numeri** della protezione del login:

| Parametro | Cosa decide |
| --- | --- |
| `login_max_tentativi_falliti` | quanti errori di fila da una macchina prima del freno |
| `login_blocco_minuti` | quanto dura il freno su quella macchina |
| `login_tetto_credenziale` | dopo quanti errori di fila, da qualunque macchina, parte l'attesa |
| `login_attesa_base_secondi` | l'attesa al primo passo; poi raddoppia |
| `login_attesa_max_secondi` | l'attesa massima |

Sono valori **globali**: la protezione non cambia da un utente all'altro.

⛔ Se uno manca, è vuoto o non è un numero intero positivo, la funzione si ferma
con `E_CONFIG_MANCANTE`: meglio un login che dice perché di una protezione tarata
a caso.

---

### Storia

* 2026-09-25 — nasce (`20260925-04`); i tre parametri dell'attesa arrivano con
  `20260925-20`.

{% include-markdown "signature-core.md" %}
