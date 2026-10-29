## 📘 Documentazione Concettuale – Funzione `script.fn_check_credenziale_eliminabile()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [fn_elimina_credenziale](/dbzero/script/funzioni/fn_elimina_credenziale)
>
> **La regola delle vesti:** [fn_credenziale_ha_vesti](/dbzero/script/funzioni/fn_credenziale_ha_vesti)
>
> **La gemella del blocco:** [fn_check_credenziale_bloccabile](/dbzero/script/funzioni/fn_check_credenziale_bloccabile)
>
> **La regola di casa:** [linee guida SQL §12.5](/linee-guida-sql)

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

Dice **perché una credenziale non si può eliminare**. Se si può, risponde con un
elenco vuoto.

La stessa risposta serve a due lettori:

* la scheda **«Altri accessi»**, che spegne «Elimina accesso» e mostra il motivo;
* il **verbo dell'eliminazione**, che la chiama e rifiuta con il primo motivo.

Il pulsante spento e il rifiuto non possono dire due cose diverse: la regola sta
scritta in un posto solo.

---

### I motivi, in ordine

| Ordine | Motivo | Quando |
| --- | --- | --- |
| 1 | `CON_VESTI` | la credenziale ha almeno una veste, anche spenta: appartiene a una persona o a un processo, e la sua storia è sua |
| 2 | `STORIA_NON_VERIFICABILE` | il database non ha i legami fra le credenziali e il resto dei dati (succede su un'installazione nuova): senza, non si sa dove sia la sua storia |
| 3 | `CON_STORIA` | la credenziale non ha vesti ma compare già fra i dati registrati (documenti, email, eventi…): il motivo dice dove |

L'ordine conta: il primo motivo è quello che il pulsante mostra e che il verbo
usa per rifiutare. Se la credenziale ha vesti, la storia non si cerca nemmeno.

---

### Regole

* Non rifiuta niente da sola: **elenca**. A rifiutare è il verbo.
* **Dove sta la storia non è scritto a mano**: la funzione lo legge dai legami del
  database, con il building block comune
  [fn_tabelle_che_trattengono](/dbzero/script/funzioni/fn_tabelle_che_trattengono). Una tabella
  nuova che nomina una credenziale entra da sola.
* Risponde allo stesso modo **chiunque la chieda**: la storia si cerca anche
  dove chi guarda non vedrebbe le righe. Restituisce solo i nomi delle tabelle.

---

### Storia

* 2026-10-06 — nasce (`20261006-13`). Brief: brief-db-elimina-credenziale-senza-veste.
* 2026-10-28 — la ricerca della storia passa al building block comune
  `script.fn_tabelle_che_trattengono`, che serve anche all'eliminazione di una versione di
  listino (`20261028-35`). La regola non cambia.

{% include-markdown "signature-core.md" %}
