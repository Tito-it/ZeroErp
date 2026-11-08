## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_set_periodo`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la tabella su cui il periodo si deriva
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_calcoli_tempo_set_periodo](/dbzero/pratiche/funzioni/trgfn_calcoli_tempo_set_periodo) — la stessa derivazione sui calcoli di tempo
> * [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins) — il giornale della sospensione

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_set_periodo` mantiene `periodo_sospensione` come
proiezione derivata delle due date `data_inizio` e `data_fine` di una sospensione.

Le date restano la fonte di verità; il range esiste perché su un range PostgreSQL sa fare ciò che su
due colonne separate non fa: sovrapposizioni, contenimento, indici GiST.

---

### ⭐ È la colonna su cui poggia l'anti-overlap

Il vincolo `ex_sospensioni_no_overlap` impedisce due sospensioni sovrapposte sulla stessa pratica e
sullo stesso flusso (o sulla pratica intera, quando il flusso manca), e ragiona su
`periodo_sospensione`. Se il range smettesse di riflettere le date, l'anti-overlap smetterebbe di
difendere il dato vero, senza che niente lo segnali.

---

### Le regole

* `data_inizio` è obbligatoria: l'estremo inferiore c'è sempre.
* `data_fine` vuota vuol dire sospensione ancora attiva: l'estremo superiore è l'infinito.
* Inizio incluso, fine esclusa: due periodi consecutivi si toccano senza sovrapporsi.
* Il valore eventualmente passato dal chiamante in `periodo_sospensione` viene sempre sovrascritto: la
  colonna è derivata, non impostabile.

Il trigger scatta all'inserimento e quando cambiano `data_inizio` o `data_fine`.

---

### ⚠️ Le date rovesciate falliscono qui, con un errore tecnico

Il trigger gira prima dei `CHECK` di tabella, e i due modi di sbagliare le date danno errori diversi:

| Caso | Chi parla | Errore |
| --- | --- | --- |
| La fine precede l'inizio | il trigger | PostgreSQL rifiuta il range (SQLSTATE `22000`, estremo inferiore maggiore del superiore) |
| La fine coincide con l'inizio | il `CHECK` | `chk_sospensioni_data_fine`, che vuole la fine strettamente dopo l'inizio |

Nel primo caso il `CHECK` non arriva a esprimersi: l'utente riceve un messaggio interno sui range, che
non nomina né la sospensione né le date, e chi parte dal messaggio non trova il vincolo di dominio.

---

### ⚠️ La sola colonna derivata non si risincronizza

Il trigger scatta sulle date, non su `periodo_sospensione`. Un aggiornamento che tocca soltanto il
periodo non lo fa scattare: il range scritto a mano resta, e da quel momento date e periodo divergono
(l'anti-overlap ragiona sul range falso, le query di dominio sulle date vere). In una bonifica manuale
si aggiornano le date, e il periodo si ricalcola da sé.

---

### Codici errore

Nessuno di dominio: la funzione non chiama `script.fn_log_and_raise_error`. Gli errori possibili sono
di PostgreSQL: il range rifiutato, il `CHECK` sulle date, l'anti-overlap.

---

### Test

* `pratiche/test-sospensioni-anti-overlap-data-futura` — il periodo derivato e l'anti-overlap che ci
  poggia sopra.

---

{% include-markdown "signature-core.md" %}
