## 📘 Documentazione Concettuale – Funzione `script.fn_check_rinuncia_reversibile`

> 👀 **Vedi anche**
>
**Consumatore (madre, solleva il primo motivo):**
>
• [vendite.fn_riapri_riconsegna_reso](/dbzero/vendite/funzioni/fn_riapri_riconsegna_reso)
>
**Contesto:**
>
• [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce)
> • [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare)
> • pattern gemello: [script.fn_check_ddt_emittibile](/dbzero/script/funzioni/fn_check_ddt_emittibile)

### 🎯 Scopo Principale

(creata 2026-07-26 — brief-db-chiusura-riconsegna-reso-definitivo §5.1)

**Single source dei motivi che impediscono di RIAPRIRE una rinuncia di ri-consegna**,
cioè di annullare la dichiarazione «questa merce non tornerà al cliente».
Ritorna `[]` se reversibile, altrimenti l'array ordinato dei motivi ostativi:
`[{codice, reason, reason_key, dettaglio}, ...]`.

### ⭐ Il gate SI È SVEGLIATO (2026-08-19)

> ⚠️ **Superata la sezione «è un gate dormiente»**, che è rimasta vera dal 2026-07-26
> al 2026-08-19 e si legge qui sotto, sotto «Perché allora esiste»: è il ragionamento
> che ha fatto esistere il punto di innesto, non lavoro da fare.

Da `20260819-02` la funzione produce **due** motivi:

| reason | codice | quando |
| --- | --- | --- |
| `RIGA_INESISTENTE` | `E_RESO_NOT_FOUND` | l'id passato non è una riga di reso |
| `ACCREDITO_ESEGUITO` | `E_RESO_RINUNCIA_ACCREDITO_ESEGUITO` | esiste almeno una riga in `vendite.resi_righe_accrediti` per quella riga |

⚠️ **La condizione è «accreditata», non «nota di credito emessa».** Il piano di luglio
immaginava il gate sul *documento*; la finestra pericolosa si apre invece **al verbo**:
fra l'accredito e la fattura la quota è già impegnata e la riga è già uscita dalla coda,
quindi aspettare l'emissione lascerebbe scoperta la parte più lunga del giro.

Il ramo nuovo sta **dopo** «riga inesistente», che ritorna subito: quello è l'*identità*
della riga, non una sua condizione. Dire «già accreditata» a chi ha passato un id
inventato lo manderebbe a cercare un accredito che non esiste.

⭐ E la madre **non è stata toccata**: `fn_riapri_riconsegna_reso` solleva già il primo
motivo prodotto. Era il pregio del disegno di luglio, ed è stato incassato.

### ⭐ Vincolo reciproco, su TRE posti (rev 2026-08-19)

Questo gate, [vendite.fn_annulla_accredito_riga_reso](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso)
e — dal 2026-08-19 — la guardia `E_RESO_ANNULLO_CON_ACCREDITO` di
[vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) **si auto-riparano**
tutti e tre per la stessa ragione: l'annullo dell'accredito **cancella** le righe di
ponte, e non le marca. Annullato l'accredito, la rinuncia torna riapribile e il reso
torna annullabile, senza che nessuno dei due sappia nulla di quella funzione.

⛔ È un pregio **fragile**: se un giorno l'annullo diventasse un *soft-delete*, questi
rami continuerebbero a vedere la riga e vieterebbero **per sempre** una rinuncia ormai
reversibile e un annullo ormai ammesso — **in silenzio**, perché nessuno dei lati sarebbe
sbagliato da solo. I tre posti si cambiano **insieme**.

### Perché esisteva già prima di servire *(storico — luglio 2026)*

Perché il **punto di innesto** deve esistere *prima* del bisogno. L'alternativa scartata
era lasciare la conseguenza in un commento dentro la funzione madre: un commento non è un
punto di innesto — la slice NC dovrebbe *cercare* dove intervenire, e nel frattempo una
riapertura potrebbe sfalsare una NC già emessa senza che nulla lo segnali.

Così invece: **quando la slice NC arriverà, riempirà questa funzione** aggiungendo il
motivo, e il divieto si attiverà da sé — `fn_riapri_riconsegna_reso` solleva già il primo
motivo prodotto. Nessuna modifica alla madre, nessuna conseguenza da ricordare.

È lo stesso principio dei `fn_check_*` esistenti: il guard si **progetta** per
l'espansione, non si rinvia.

### 🚫 Non rimuovere questa funzione

Era la trappola prevedibile finché il gate era dormiente: una funzione che non vieta nulla
sembra codice morto. ⭐ **La previsione si è avverata al contrario** — il gate ha
funzionato esattamente come progettato — ed è il motivo per cui questa sezione resta:
rimuovere il punto di innesto riporta la conseguenza a essere una nota in un commento che
nessuno cercherà.

### Regole chiave

- Funzione **pura** (`fn_check_*`): non solleva per condizioni di dominio, non scrive. È
  la madre a decidere se sollevare. L'unico raise è il guard di parametro.
- La riga inesistente è segnalata come **motivo** (riusando `E_RESO_NOT_FOUND`, già a
  catalogo) e non come eccezione, per restare coerenti col contratto della famiglia.
- `STABLE`, sola lettura.
- Il `reason_key` è pensato per il frontend, ma ⚠️ **oggi nessuna superficie lo rende**:
  la madre solleva con il *codice* e i motivi finiscono nel `context`, che si ferma in
  `dbops.error_log`. L'operatore legge quindi il messaggio di catalogo, che è corretto e
  completo. Le chiavi i18n ci sono e non costano nulla: il giro si chiuderà il giorno in
  cui una **capability** del reso esporrà i motivi.

Verifica: `db/pgtap/vendite/test-rinuncia-gate-accredito-v1.sql` (8 asserzioni, incluso
il round-trip dell'auto-riparazione).
