## 📘 Documentazione Concettuale – Tabella `dbops.presidi_cause`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo, che dichiara la colonna della causa
> * [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi) — le parole per chi agisce, per causa
> * [dbops.cause_fallimento](/dbzero/dbops/tabelle/cause_fallimento) — il vocabolario delle cause del presidio dei lavori
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/views/vw_processi_programmazione_da_guardare) — le cause dei processi automatici
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — le cause dei lavori del database
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio_per_variante](/dbzero/dbops/funzioni/fn_conta_presidio_per_variante) — quante righe ha ogni causa

---

### 🎯 Scopo Principale

Le cause di un presidio le cui righe sono guasti diversi, ognuna con chi la spegne.

Alcuni presidi elencano nella stessa vista guasti di natura diversa: un timer fermo e un difetto
di programmazione, un disco pieno e una credenziale sbagliata. Un solo «a chi tocca» per tutto il
presidio è sbagliato per alcune righe esattamente come lo era un testo unico, e il digest le
manderebbe alla persona sbagliata.

---

### ⭐ La causa è un'entità

| Colonna | Che cosa dice |
| --- | --- |
| `vista` | il presidio |
| `causa` | il valore che la colonna della causa assume nelle righe di quel presidio (quale colonna, lo dice `colonna_variante` del catalogo) |
| `chi_agisce` | chi interviene: `AMMINISTRATORE` (dall'applicazione), `SISTEMISTA` (server, servizi, database), `SVILUPPO` (serve una modifica al programma) |

La causa ha il suo «a chi tocca» e i suoi testi per lingua in
[dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi), agganciati con una FK su (vista,
causa): un testo di causa esiste solo se la causa è qui. `chi_agisce` del catalogo resta il valore
del presidio nel suo insieme.

---

### Le regole che la tengono completa

| Regola | Dove vive |
| --- | --- |
| Una causa non è mai vuota, e una sola riga per (vista, causa) | vincolo del database |
| I valori ammessi per «a chi tocca» sono gli stessi del catalogo dei presidi | vincolo del database, e un pgTAP che confronta i due domini |
| Le cause stanno solo sui presidi che dichiarano la colonna della causa | pgTAP |
| Ogni causa ha il suo testo in italiano, e un presidio con la colonna della causa ha almeno una causa | pgTAP |
| Le cause del presidio dei processi sono esattamente quelle che la vista può produrre | il pgTAP di quel presidio |
| Le cause del presidio dei lavori sono esattamente il vocabolario di [dbops.cause_fallimento](/dbzero/dbops/tabelle/cause_fallimento) | il pgTAP di quel presidio |

---

### Come si aggiunge o si cambia una causa

Si edita `80_data/sql/dbops/presidi_cause.csv` e, nello stesso giro, il testo in
`presidi_testi.csv`. Lo stesso seed carica le cause **prima** dei testi, così una causa nuova e il
suo testo entrano insieme. Per **togliere** una causa non basta cancellarla dal file: serve una
modifica al database che la tolga, insieme ai suoi testi.

---

### Test

* `db/pgtap/dbops/test-presidi-testi-v1.sql` — cause solo sui presidi che le dichiarano, stesso
  dominio di `chi_agisce` nelle due tabelle, ogni causa con il suo testo italiano, almeno una
  causa dove la colonna è dichiarata, FK dei testi verso le cause, lettura da parte
  dell'applicazione.
* `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` — le cause dei processi
  coincidono con quelle che la vista produce.
* `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql` — le cause dei lavori
  coincidono con il vocabolario, e ogni causa prodotta ha chi la spegne.

---

### Note di migrazione

* 2026-10-09 — nasce con `brief-db-presidio-processi-testo-per-causa` §5.5: il presidio dei
  processi era assegnato a chi gestisce il server, ma due delle sue cause richiedono una modifica
  del programma.
* 2026-10-16 — si aggiungono le cause del presidio dei lavori (`brief-db-presidio-job-run-a-chi-tocca`).

---

{% include-markdown "signature-core.md" %}
