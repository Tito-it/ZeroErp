## 📘 Documentazione Concettuale – Tabella `dbops.presidi_testi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, e chi li spegne
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — le cause a cui un testo di variante si aggancia
> * [config.lingue](/dbzero/config/tabelle/lingue) — le lingue ammesse
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — il precedente: testo per l'operatore, a database e per lingua
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/views/vw_processi_programmazione_da_guardare) — un presidio con un testo per causa
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — l'altro presidio con un testo per causa
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — il meccanismo dei presidi

---

### 🎯 Scopo Principale

Il testo di un presidio per chi deve agire, per lingua: che cosa vuol dire una sua riga e che
cosa fare per spegnerlo, con le parole di chi usa l'applicazione.

Di ogni presidio esistono già due testi scritti per chi lo **mantiene**: il `COMMENT` della vista
e la `nota` del catalogo. Spiegano perché il presidio esiste, citano i documenti di progetto,
dichiarano perimetro e cadenza. Chi deve **agire** ha due domande sole, e questa tabella risponde
a quelle. I due testi per chi mantiene restano com'erano.

---

### Le due colonne

| Colonna | Risponde a | Come si scrive |
| --- | --- | --- |
| `significato` | *che cosa vuol dire una riga?* | una o due frasi; niente nomi di tabelle o di funzioni; le schermate come si chiamano nel menu |
| `azione` | *che cosa devo fare?* | all'imperativo, e dice **dove** si fa. Se il rimedio è capire chi ha scritto un dato, dice anche che cosa **non** fare (correggerlo a mano). Se tocca a qualcun altro, dice a chi inoltrare e che cosa riferire |

Nessuna delle due può essere vuota. **Chi** spegne il presidio non sta qui: è `chi_agisce` di
[dbops.presidi](/dbzero/dbops/tabelle/presidi), un dato su cui pannello e digest decidono.

---

### Un testo per causa, quando le righe sono guasti diversi

Di solito un presidio ha un testo solo. Quando invece le sue righe sono guasti diversi, con
rimedi diversi, un testo unico dà a qualcuno il rimedio sbagliato. Per questi presidi il testo si
sceglie riga per riga, dalla causa:

| Dove | Che cosa dice |
| --- | --- |
| `colonna_variante` del catalogo | da quale colonna della vista si legge la causa di ogni riga (vuota = un testo solo) |
| `variante` di questa tabella | vuota = il testo del presidio; valorizzata = il testo delle righe con quella causa |

Ogni causa è prima di tutto una riga di [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause):
un testo di variante senza la sua causa lì il database lo rifiuta. La chiave è (vista, lingua,
variante) con i vuoti considerati uguali, quindi un presidio ha un solo testo generale per lingua.

⛔ Il testo generale **non** fa da ripiego per una causa senza testo: darebbe di nuovo il rimedio
sbagliato, e senza avvisare. Una lingua che manca ripiega sull'italiano **della stessa causa**.

Oggi hanno un testo per causa il presidio dei processi automatici e quello dei lavori del
database.

---

### Perché a database e non nei testi del frontend

Il testo serve anche al digest, che parte per email dal backend e non ha i testi tradotti del
frontend. È la stessa scelta del catalogo dei messaggi d'errore. L'italiano è obbligatorio.

---

### Le regole che la tengono completa

| Regola | Dove vive |
| --- | --- |
| Ogni presidio attivo, non ritirato e non `INVENTARIO` ha il testo generale in italiano | pgTAP (un vincolo non guarda un'altra tabella) |
| Nessun testo punta a un presidio ritirato | pgTAP |
| Una frase non è mai vuota, una variante non è mai una stringa vuota | vincolo del database |
| Un solo testo generale per presidio e lingua | vincolo del database |
| Ogni testo in una lingua ha la versione italiana della stessa variante | pgTAP |
| Le cause stanno solo sui presidi che le dichiarano, e ogni causa ha il suo testo italiano | pgTAP |
| Ogni causa che un presidio può produrre ha il suo testo | il pgTAP di quel presidio |

Il presidio si nomina con il nome qualificato della sua vista, come nel catalogo: mai con un
numero interno, che vale su una macchina sola.

---

### Come si aggiunge o si cambia un testo

Si edita `80_data/sql/dbops/presidi_testi.csv` (e, per una causa nuova, `presidi_cause.csv` nello
stesso giro): il seed rilegge i due file quando cambiano, prima le cause e poi i testi, così una
causa nuova e il suo testo entrano insieme. Per **togliere** una riga non basta cancellarla dal
file — il seed aggiunge e aggiorna, non cancella: serve anche una modifica al database che la
tolga.

---

### Test

* `db/pgtap/dbops/test-presidi-testi-v1.sql` — completezza del testo italiano e ritiro, i vincoli
  su `chi_agisce`, la lettura da parte dell'applicazione, le varianti (colonna che esiste nella
  vista, cause solo dove dichiarate, ripiego per lingua dentro la causa, chiave con i vuoti
  uguali, variante non vuota, FK verso le cause, ogni causa con il suo testo).
* `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` — ogni causa del presidio dei
  processi ha il suo testo.

---

### Note di migrazione

* 2026-10-06 — nasce con `brief-db-presidi-cosa-significa-cosa-fare`: nel collaudo del
  2026-09-19 due presidi accesi erano «complicati da capire», e detti in due righe si sono spenti
  in pochi minuti.
* 2026-10-09 — nasce `variante` (`brief-db-presidio-processi-testo-per-causa`): quel giorno il
  pannello diceva «Esegui ora» a un servizio sempre acceso che aveva perso la connessione.
* 2026-11-04 — esce il testo di `dbops.vw_run_senza_attore`, cancellato prima della riga del
  presidio quando la vista è stata tolta dal database (`brief-db-revisione-dbops`).
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
