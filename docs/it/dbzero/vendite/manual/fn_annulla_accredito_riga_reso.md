## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_accredito_riga_reso()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti)
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
>
Approfondimento funzioni:
> • [vendite.fn_accredita_riga_reso](/dbzero/vendite/funzioni/fn_accredita_riga_reso)
> • [script.fn_check_rinuncia_reversibile](/dbzero/script/funzioni/fn_check_rinuncia_reversibile)
> • [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione del 2026-08-18)

**Madre DB del verbo «annulla accredito»**, specchio esatto di `fn_accredita_riga_reso`:
toglie le coppie dal ponte `vendite.resi_righe_accrediti` e porta le rettifiche di commessa a
`stato_emissione = 'ANNULLATA'`.

Restituisce le coppie rimosse **nella stessa forma con cui la madre le aveva create**, così il
chiamante può dire esattamente che cosa ha disfatto.

⭐ L'unità atomica è **l'accredito intero**, non la singola coppia: o si disfa tutto, o niente.

---

### ⛔ Non è l'annullo del documento

Il documento si annulla con il **reset del lotto** — e dopo un reset la nota di credito
**rigenera** al giro successivo, perché la coda accrediti è ancora piena.

Qui no: **si torna prima del verbo**. La riga del reso rientra in coda, e il prossimo giro
non produrrà nulla finché qualcuno non riaccredita.

Sono due operazioni diverse con esiti opposti, e confonderle è il modo per ritrovarsi la nota
di credito che si voleva eliminare.

---

### 🔴 Vincolo reciproco su **tre** posti — il punto più delicato

Che questa funzione **cancelli** le righe di ponte invece di marcarle non è un dettaglio
implementativo: è ciò che fa **auto-riparare** altri due controlli.

| Chi | Che cosa torna a permettere |
|---|---|
| `script.fn_check_rinuncia_reversibile` | la rinuncia torna reversibile |
| `vendite.fn_annulla_reso` (guardia `E_RESO_ANNULLO_CON_ACCREDITO`, dal 2026-08-19) | l'annullo del reso torna ammesso |

**Nessuno dei due sa niente di questa funzione.** Tornano permissivi solo perché la riga
*sparisce davvero*.

⛔ **Se un giorno l'annullo diventasse un soft-delete** — una colonna `annullato` invece di un
`DELETE` — quei due rami vieterebbero **per sempre** una rinuncia ormai reversibile e un
annullo di reso ormai ammesso, **in silenzio**. E nessuno dei tre lati sarebbe sbagliato preso
da solo: è la combinazione a rompersi.

**I tre posti si cambiano insieme.** È l'unica avvertenza di questa pagina che vale la pena
ricordare a memoria.

---

### Il presidio permessi non è qui

Vive sul backend (`post_permission`), deliberatamente: la madre deve restare usabile da un
processo autorizzato — un job, una riparazione — senza dover simulare un utente.

---

### Nota di stile che il codice dichiara

`bigint[]` esplicito invece di `colonna%TYPE[]`, che **PostgreSQL non supporta**: è l'unica
eccezione all'ancoraggio `%TYPE` nel `DECLARE`, ed è annotata nel corpo. I conteggi sono
`integer` espliciti perché non c'è nessuna colonna da ancorare — detto invece di sembrare una
dimenticanza.

---

{% include-markdown "signature-core.md" %}
