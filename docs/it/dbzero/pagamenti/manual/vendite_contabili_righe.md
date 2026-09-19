## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili_righe`** contiene il dettaglio delle
righe importate/gestite nella testata contabile vendite, con stato di lavorazione
e riferimenti di abbinamento (fattura, billing account).

---

### Campi chiave (semantica)

* `contabile_id`: FK alla testata `pagamenti.vendite_contabili`.
* `riferimento_ente`: riferimento esterno del flusso (CRO/TRN/UID operazione).
* `importo`: importo riga (vincolo `<> 0`).
* `fattura_id`: fattura eventualmente abbinata.
* `billing_account_id`: billing account eventualmente abbinato.
* `stato_id`: stato di lavorazione riga.
* `motivo_sospeso`: dettaglio diagnostico in caso di sospensione.
* `fondo_source_id`: l'**atto di fondo fattura** da cui la riga nasce
  (`vendite.fatture_fondi_fattura_source`). `NULL` su ogni riga che non viene da
  un fondo, cioè sulla maggior parte.
* `scadenza_id`: la **rata** a cui questo denaro è imputato
  (`vendite.fatture_scadenze`). ⭐ L'abbinamento vive **qui**, e non in una
  tabella N:N: la riga è già l'unità di allocazione, e chi paga due rate con un
  bonifico solo fa **due righe** — che è anche il modo in cui la banca lo
  racconta.
* `forzata` / `motivo_forzatura`: la riga è stata registrata **fuori dalla
  capienza**, e qualcuno l'ha confermato. Il motivo è facoltativo.

> ⚠️ **`scadenza_id` è facoltativo di proposito**, e non è una dimenticanza: ci
> sono righe che saldano un documento **senza riferirsi a una rata**. La riga del
> fondo fattura è esattamente quella — è un saldo per trasferimento, ha fattura
> sì e rata no. Il guard sui dati dello stato **non la pretende**, ed è scritto
> così da prima che la colonna esistesse: chi lo legge non deve pensare a una
> svista.
>
> ⭐ **`forzata` è il prezzo di una decisione**: che un cliente paghi più del
> dovuto, o paghi due volte, è un **fatto del mondo** e il database non lo
> dichiara impossibile — lo **segnala**, e se qualcuno conferma registra e lascia
> scritto. Senza traccia, una forzatura è un modo di *nascondere* denaro, non di
> registrarlo. L'elenco a valle è
> [vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza).
>
> ⚠️ Da non confondere `motivo_forzatura` con `motivo_sospeso`: il secondo dice
> perché una riga **non** è stata lavorata, il primo perché è stata lavorata **lo
> stesso**.
>
> ⭐ **`fondo_source_id` è nuova del 21-08-2026, e prima era una stringa dentro
> un JSON** (`meta ->> 'fondo_source_id'`). Non era una relazione: nessuna
> integrità, nessun indice, nessuna garanzia che il valore fosse un id
> esistente — e la leggevano già **tre** funzioni. Quando il progetto ci ha
> appeso sopra una macchina a stati (l'atto passa a `ESEGUITO` leggendo questo
> legame) è diventata portante, e un legame portante si scrive come tale.
>
> ⚠️ La FK è **`NO ACTION`** di proposito: cancellare un atto pretende di aver
> prima cancellato le sue righe. È l'ordine che `vendite.fn_reset_fondi_fattura`
> rispetta spezzando il lavoro in più statement — una FK differita avrebbe
> *nascosto* l'ordine invece di dichiararlo.
>
> ℹ️ Da non confondere con `meta ->> 'origine' = 'FONDO_FATTURA'`, che resta:
> quello dice **da quale processo** nasce la riga, questo **a quale atto**
> appartiene.

---

### Regole principali

* La riga appartiene sempre a una testata (`contabile_id` obbligatorio).
* `stato_id` usa il lookup `pagamenti.vendite_contabili_righe_stati`.
* `importo` non puo` essere zero.
* Centro riscossione/ente di provenienza sono definiti in testata, non in riga.
* Uno stato che pretende l'abbinamento vuole **fattura e cliente** valorizzati
  (bandiera `richiede_abbinamento` sul catalogo degli stati).
* Portando la riga in uno stato **registrato**, l'eventuale atto di fondo
  citato da `fondo_source_id` passa a `ESEGUITO` — lo fa un trigger, non il
  chiamante (`trgfn_vendite_contabili_righe_marca_fondo_eseguito`).

---

### ✂️ Eliminare una riga, e quando il contenuto si ferma (dal 14-09-2026)

Una riga si **elimina** con `attivo = false` — e dallo stesso giorno anche il
`DELETE` fisico passa dalla stessa regola — **solo** se la sua distinta è
**`MANUALE` in `BOZZA`** (D17). Non è uno stato: `SCARTATA` resta, ma dice
un'altra cosa — *denaro arrivato, non nostro* — e **conta nella quadratura**;
una riga digitata male su una bozza non è un fatto, e si toglie.

Sotto una `MANUALE` **validata** il contenuto è **fermo** (D18): niente righe
nuove, niente modifiche ai **fatti** (importo, le tre date, riferimento),
niente eliminazioni né spostamenti, finché non torna in bozza. Le
**decisioni** — stato, abbinamento, forzatura, motivi — restano libere: non
toccano la quadratura, e il posting muove lo stato a distinta ancora validata.

Il predicato dell'eliminazione ha **una sede sola**,
[script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile)
(tre motivi ordinati: distinta finale, non manuale, validata), e il guard che la
chiama è
[trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto)
— che porta anche il congelamento. Il backend legge lo stesso elenco per
spegnere il cestino col perché: tooltip e rifiuto non possono divergere.

> ⚠️ Il `DELETE` ha **un** passaggio legittimo: il giro dei fondi
> (`vendite.fn_cancella_fondo_fattura`) cancella le righe del suo atto sotto una
> `GENERATA`, e lo dichiara con la GUC transazionale
> `zeroerp.allow_contabile_riga_delete_override`. Non è un permesso: è la madre
> che dice «sono io», dopo aver letto il suo criterio. Il resto sta nella scheda
> del guard.

---

### 🔒 Chi la vede — la RLS del perimetro incassi (2026-08-22)

Policy `rls_vendite_contabili_righe_perimetro_incasso`, **`FOR ALL`**, gate
`OPERATORE` fail-closed, con **tre strade in OR** e nessuna ridondante.

| | Strada | Copre |
| --- | --- | --- |
| **1** | il **canale** della distinta (`fn_scope_ef_whitelist_via_contabile`) | la riga `DA_ABBINARE` di un flusso bancario, che fattura non ha |
| **2** | la **fattura** della riga, quando c'è | le righe delle distinte **interne**, e la riga sul proprio documento finita sulla distinta di un altro |
| **3** | **né documento né canale** | la riga `DA_ABBINARE` sul lotto di lavoro di un operatore |

⭐ **La prima è la ragione per cui il perimetro dal conto esiste**: con la sola
fattura, la coda «da abbinare» sarebbe invisibile a tutti. Su una distinta
**interna** risponde `false` apposta — la sua testata è di tutti, le sue righe no.

⚠️ **La seconda serve a due casi, e uno è strutturale.** Dà il perimetro alle
righe delle distinte interne (fondo fattura, compensazione), e fa vedere la
**riga sul proprio documento finita sulla distinta di un altro**, cioè un
abbinamento sbagliato: senza, il saldo direbbe che quel denaro non è arrivato **e
non ci sarebbe modo di scoprire perché**. ⭐ E serve anche alla **bilancia**: una
riga che sparisse dalla propria distinta romperebbe la quadratura col totale
dichiarato, e la verifica darebbe un allarme falso ogni volta.

⚠️ La seconda strada legge `vendite.fatture` **sotto** la row security, e **qui è
giusto**: non vedere la fattura *è già* la risposta. Nel guard di **scrittura** la
stessa lettura era un difetto, perché lì la domanda è «di chi è» e va saputa per
intero — vedi
[fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id).

> 🔴 **La terza strada è una correzione in avanti** (`20260822-24`), ed è nata da
> un difetto vero: le prime due non coprivano la riga `DA_ABBINARE` su una
> distinta **`MANUALE` senza canale** — cioè un operatore che sta digitando
> incassi (D12-a) — e il `WITH CHECK` la **rifiutava** con `42501`. Un perimetro
> che impedisce la lavorazione invece di proteggerla.
>
> ⭐ Una riga senza documento su una distinta senza canale **non porta nessuna
> attribuzione**: non c'è niente in essa che dica di chi sia, e nasconderla a
> tutti non protegge nessuno. ⛔ Resta stretta: appena la riga prende una
> `fattura_id`, la terza strada si spegne e decide la fattura.
>
> 🔵 Resta aperta la decisione se rendere il canale **obbligatorio** anche sulle
> distinte manuali — la lettura più fedele a D5 — oggi impraticabile perché
> `enti_incasso` è a zero righe finché non si configurano i conti dei due
> emittenti.

⭐ **La policy nasconde, i trigger rifiutano.** Due guard di scrittura, perché
nessuno dei due copre l'altro: `('fattura','fattura_id')` — mirror di quello che
`vendite_movimenti` ha già — e `('contabile','contabile_id')`, l'unico che copre
la coda «da abbinare». Col solo primo il presidio si accenderebbe *dopo* che il
lavoro è finito; col solo secondo si potrebbe abbinare denaro **proprio** alla
fattura **di un altro**.

---

### Esempio d’uso

```sql
SELECT r.id, r.contabile_id, r.importo, r.stato_id, r.fattura_id
FROM pagamenti.vendite_contabili_righe r
WHERE r.attivo IS TRUE
ORDER BY r.id DESC
LIMIT 50;
```

---

{% include-markdown "signature-core.md" %}
