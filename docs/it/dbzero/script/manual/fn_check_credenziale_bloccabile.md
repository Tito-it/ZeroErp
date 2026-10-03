## 📘 Documentazione Concettuale – Funzione `script.fn_check_credenziale_bloccabile()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [fn_blocca_credenziale](/dbzero/script/funzioni/fn_blocca_credenziale)
>
> **Le due regole che compone:** [fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) ·
> [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo)
>
> **La regola di casa:** [linee guida SQL §12.5](/linee-guida-sql)

---

### 🎯 Scopo Principale
(scritta il 03-10-2026)

Dice **perché una credenziale non si può bloccare**. Se si può, risponde con un
elenco vuoto.

La stessa risposta serve a due lettori:

* il **pannello della credenziale**, che spegne «Blocca accesso» e mostra il
  motivo invece di lasciar premere un pulsante che verrebbe rifiutato;
* il **verbo del blocco**, che la chiama e rifiuta con il primo motivo.

Così il pulsante spento e il rifiuto non possono dire due cose diverse: la
regola sta scritta in un posto solo.

---

### I motivi, in ordine

| Ordine | Motivo | Quando |
| --- | --- | --- |
| 1 | `CREDENZIALE_DI_SISTEMA` | è l'accesso di un processo automatico o di un sistema esterno: bloccarlo fermerebbe il suo lavoro |
| 2 | `ULTIMO_SUPER_ADMIN` | è l'ultimo amministratore che può ancora entrare: bloccarlo lascerebbe il sistema senza nessuno che lo governi |

L'ordine conta: il primo motivo è quello che il pulsante mostra e che il verbo
usa per rifiutare.

---

### Regole

* Non rifiuta niente da sola: **elenca**. A rifiutare è il verbo.
* Il motivo «di sistema» **non vale per chi lavora sul server** come
  amministratore del database: è la strada d'emergenza per fermare una
  credenziale di sistema compromessa. La regola non cambia: è il verbo che,
  in quel caso, la scavalca.

---

### Storia

* 2026-10-03 — nasce (`20261003-01`). Brief: brief-db-credenziale-verbi-amministratore.

{% include-markdown "signature-core.md" %}
