## 📘 Documentazione Concettuale – Funzione `script.fn_tabelle_che_trattengono(p_tabella, p_ids, p_escluse)`

> 👀 **Vedi anche**
>
> [script.fn_check_credenziale_eliminabile](/dbzero/script/funzioni/fn_check_credenziale_eliminabile) ·
> [script.fn_check_versione_listino_eliminabile](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16.11, E-3)

**Quali tabelle impediscono di cancellare delle righe.** Date una tabella e alcune sue righe (per
chiave primaria), restituisce le tabelle che le tengono con un legame che rifiuta la
cancellazione (FK `RESTRICT` o `NO ACTION`), in ordine di nome, una volta ciascuna. Elenco
vuoto = nessuna.

È il building block comune di chi deve dire «non si elimina perché è già usato»: la credenziale
(motivo `CON_STORIA`) e la versione di listino (motivo `CITATA`). Prima la ricerca stava scritta
dentro la check della credenziale.

### Regole

* **L'elenco non è scritto**: si legge dai legami del database. Una tabella nuova entra da sola.
* Contano solo i legami a una colonna verso la chiave primaria. Quelli in `CASCADE` o `SET NULL`
  non trattengono.
* `p_escluse`: le tabelle che chi chiama cancella prima lui, o giudica con un altro motivo.
* Le righe della stessa tabella che se ne vanno in `CASCADE` con la riga non contano.
* ⛔ Un nipote (un legame `RESTRICT` verso una tabella che segue in `CASCADE`) non si vede.
* Risponde allo stesso modo **chiunque la chieda**: cerca anche dove chi guarda non vedrebbe le
  righe (`SECURITY DEFINER`). Restituisce solo nomi di tabelle. `EXECUTE` solo all'applicazione.

---

{% include-markdown "signature-core.md" %}
