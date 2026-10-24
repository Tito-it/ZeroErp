## 📘 Documentazione Concettuale – Vista `script.vw_stati_doc_ddt_merce_partita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
>
**Chi la legge:**
>
• [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce)
> • [vendite.fn_ordine_riga_spedita](/dbzero/vendite/funzioni/fn_ordine_riga_spedita)
> • [dbops.vw_ddt_emessi_senza_scarico](/dbzero/dbops/views/vw_ddt_emessi_senza_scarico)

---

### 🎯 Scopo Principale
(latest review 2026-10-12)

Risponde a una sola domanda: **un DDT in questo stato ha fatto partire la
merce?** Una riga per ogni stato del DDT, con il booleano `merce_partita`.

La merce è partita quando il DDT è **uscito dalla bozza** e **non è
abortito**:

| Stato | `merce_partita` | Perché |
| --- | --- | --- |
| Bozza | no | il DDT non è ancora emesso |
| Emesso, Spedito, Consegnato | sì | dall'emissione in poi la merce è uscita |
| Reso | sì | la merce è tornata, ma il documento è vissuto: era partita |
| Annullato | no | un documento annullato non ha fatto partire niente |

La regola è letta dal catalogo degli stati (la posizione `ordine` rispetto a
quella di Emesso, e il flag `is_abortito`), non da un elenco di codici: uno
stato nuovo fra Emesso e Consegnato entra da solo.

⛔ **Non risponde mai NULL.** Uno stato senza posizione (`ordine` vuoto), o un
catalogo senza Emesso, dice «non partita».

---

### Perché esiste

Fino al 2026-10-12 la stessa regola stava in **quattro** punti, scritta in due
forme diverse: due volte dentro `vendite.fn_partite_merce`, una in
`vendite.fn_ordine_riga_spedita` (la data di consegna di una riga già spedita
non si cambia più), e una nel presidio `dbops.vw_ddt_emessi_senza_scarico`,
che la scriveva come elenco di codici. Oggi coincidono; al primo stato nuovo
avrebbero risposto in modi diversi, senza che nessun test se ne accorgesse.
Ora la regola sta qui, e i quattro punti la leggono (regola del 2, changeSet
`20261012-30` … `-33`, brief `brief-db-date-consegna-righe-in-blocco` §4.1).

---

### Come si usa

* **Per filtrare** (solo i DDT con merce partita):
  `JOIN script.vw_stati_doc_ddt_merce_partita s ON s.id = d.stato_doc_ddt_id
  WHERE s.merce_partita`.
* **Per distinguere** (partito / non ancora): si proietta `s.merce_partita`.

È una vista e non una funzione: si incorpora nella query di chi la legge, e
non aggiunge chiamate per riga. `security_invoker`.

---

### Presidio

`db/pgtap/script/test-vw-stati-doc-ddt-merce-partita-v1.sql`: i casi della
tabella sopra, il fail-closed su uno stato senza posizione, e che i tre
consumatori leggano questa vista e non portino più una copia della regola.

---

{% include-markdown "signature-core.md" %}
