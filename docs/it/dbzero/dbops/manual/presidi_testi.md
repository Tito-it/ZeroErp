## 📘 Documentazione Concettuale – Tabella `dbops.presidi_testi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.presidi](/dbzero/dbops/manual/presidi) — *il catalogo dei presidi, e chi li spegne*
>
**Approfondimento guide:**
>
• [Presidi e registri del debito](/guide/presidi-e-registri-del-debito)
>

### 🎯 Scopo Principale
(latest review 06-10-2026)

Dice, per ogni presidio e per ogni lingua, **cosa vuol dire** una sua riga e
**cosa fare** per spegnerlo — con le parole di chi usa l'applicazione.

Di ogni presidio esistevano già due testi, tutti e due scritti per chi lo
**mantiene**: il commento della vista e la `nota` del catalogo. Spiegano perché
il presidio esiste, citano i documenti di progetto, dichiarano perimetro e
cadenza. Il pannello **Processi automatici** e il digest li mostravano però a chi
deve **agire**, che ha due domande sole. Nel collaudo del 19-09-2026 due presidi
accesi erano *«complicati da capire»*; detti in due righe, si sono spenti in
pochi minuti.

---

### Le due colonne

| Colonna | Risponde a | Come si scrive |
| --- | --- | --- |
| `significato` | *cosa vuol dire una riga?* | una o due frasi; niente nomi di tabelle o di funzioni; le schermate come si chiamano nel menu |
| `azione` | *cosa devo fare?* | all'imperativo, e dice **dove** si fa. Se il rimedio è capire chi ha scritto un dato, dice anche cosa **non** fare (correggerlo a mano). Se tocca a qualcun altro, dice a chi inoltrare e cosa riferire |

**Chi** lo spegne non sta qui: è la colonna `chi_agisce` di
[`dbops.presidi`](/dbzero/dbops/manual/presidi), perché è un dato su cui il
pannello e il digest devono poter decidere, non una frase.

---

### Perché a database e non nei testi del frontend

Il testo serve anche al **digest**, che parte per email dal backend e non ha i
testi tradotti del frontend. Il precedente è il catalogo dei messaggi d'errore,
che tiene a database, per lingua, il testo per l'operatore. L'italiano è
obbligatorio; un lettore che non trova la sua lingua ripiega sull'italiano.

---

### Le due regole che lo tengono completo

| Regola | Dove vive |
| --- | --- |
| Ogni presidio attivo, non ritirato e non `INVENTARIO` ha la riga in italiano | test `db/pgtap/dbops/test-presidi-testi-v1.sql` (test 2) — un vincolo del database non può guardare un'altra tabella |
| Un presidio ritirato non porta più testi | stesso test (test 3) |
| Una frase non è mai vuota | vincolo del database |

Il presidio si nomina con il nome della sua vista, come nel catalogo: mai con un
numero interno, che vale su una macchina sola.

---

### Come si aggiunge o si cambia un testo

Si edita `80_data/sql/dbops/presidi_testi.csv`: il seed lo rilegge a ogni
aggiornamento del database. Per **togliere** una riga (il presidio è stato
ritirato) non basta cancellarla dal file — il seed aggiunge e aggiorna, non
cancella: serve anche una modifica al database che la tolga.

---

*Brief: `docs/it/dev/work-in-progress/brief-db-presidi-cosa-significa-cosa-fare.md`.*
