## 📘 Documentazione Concettuale – Funzione `script.fn_azzera_tentativi_credenziale()`

> 👀 **Vedi anche**
>
> **Il modello (cosa azzera cosa):** [config.credenziali](/dbzero/config/tabelle/credenziali)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Azzera i **tentativi sbagliati** di una credenziale. Una regola sola, con due
chiamanti che differiscono solo per quanto toccano:

| Chi la chiama | Come | Cosa azzera |
| --- | --- | --- |
| l'**accesso riuscito** (dentro `fn_registra_tentativo_login`) | con la provenienza | i fallimenti di fila e il freno sulla **sola** macchina da cui si è entrati |
| il **reset della password** riuscito (backend) | senza provenienza | i fallimenti di fila e il freno su **tutte** le macchine: la password è cambiata, i tentativi sulla vecchia non contano più |

⛔ **Non tocca il blocco dell'amministratore** (lo toglie solo
[fn_sblocca_credenziale](/dbzero/script/funzioni/fn_sblocca_credenziale)) né il
cambio password obbligatorio.

Una credenziale che non ha mai sbagliato non ha niente da azzerare: nessun errore.

---

### Storia

* 2026-09-25 — nasce (`20260925-09`). Brief: brief-db-blocco-login-per-credenziale.

{% include-markdown "signature-core.md" %}
