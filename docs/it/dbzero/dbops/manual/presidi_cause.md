## 📘 Documentazione Concettuale – Tabella `dbops.presidi_cause`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.presidi](/dbzero/dbops/manual/presidi) — *il catalogo dei presidi, e chi li spegne*
>
• [dbops.presidi_testi](/dbzero/dbops/manual/presidi_testi) — *le parole per chi agisce*
>
**Approfondimento viste:**
>
• [dbops.vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione) — *le cause dei processi automatici*

### 🎯 Scopo Principale
(latest review 09-10-2026)

Alcuni presidi elencano guasti **diversi**: lo stesso elenco può contenere un
timer fermo e un difetto di programmazione. Per questi presidi ogni riga ha una
**causa**, e questa tabella dice, per ogni causa, **a chi tocca** intervenire.

Prima l'informazione «a chi tocca» c'era solo per l'intero presidio. Il presidio
dei processi automatici era assegnato a chi gestisce il server, ma due delle sue
cause richiedono una modifica del programma: il pannello le presentava come cosa
del sistemista, e il digest le mandava a lui.

---

### Come si legge

| Colonna | Che cosa dice |
| --- | --- |
| `vista` | il presidio |
| `causa` | il valore che la colonna della causa assume nelle righe di quel presidio (quale colonna, lo dice `colonna_variante` del catalogo) |
| `chi_agisce` | chi interviene: `AMMINISTRATORE` (dall'applicazione), `SISTEMISTA` (server, servizi, database), `SVILUPPO` (serve una modifica al programma) |

I **testi** di ogni causa — cosa vuol dire, cosa fare — stanno in
[`dbops.presidi_testi`](/dbzero/dbops/manual/presidi_testi), uno per lingua. Un
testo di causa può esistere solo se la causa è in questa tabella: lo impone il
database.

---

### Le regole che la tengono completa

| Regola | Dove vive |
| --- | --- |
| Le cause stanno solo sui presidi che dichiarano la colonna della causa | test `db/pgtap/dbops/test-presidi-testi-v1.sql` (test 9) |
| Ogni causa ha il suo testo in italiano | stesso test (test 16) |
| Un presidio che dichiara la colonna della causa ha almeno una causa | stesso test (test 17) |
| I valori ammessi per «a chi tocca» sono gli stessi del catalogo dei presidi | stesso test (test 15) |
| Le cause del presidio dei processi sono **esattamente** quelle che la vista può produrre | test `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` |
| Le cause del presidio dei lavori (`maintenance.vw_job_run_da_guardare`) sono **esattamente** il vocabolario [`dbops.cause_fallimento`](/dbzero/dbops/manual/cause_fallimento) *(dal 2026-10-16)* | test `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql` (test 1) |

---

### Come si aggiunge o si cambia una causa

Si edita `80_data/sql/dbops/presidi_cause.csv` e, nello stesso giro, il testo in
`presidi_testi.csv`. Le cause vengono caricate **prima** dei testi dallo stesso
passaggio, così una causa nuova e il suo testo entrano insieme. Per **togliere**
una causa non basta cancellarla dal file: serve una modifica al database che la
tolga, insieme ai suoi testi.

---

*Brief: `brief-db-presidio-processi-testo-per-causa.md` §5.5.*
