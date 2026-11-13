## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_offerta`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) — il vocabolario degli stati: emissione, accettazione, annullo, PDF, nota di stato
> * [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) — la matrice dei passaggi, con i dati del pulsante
>
> Approfondimento funzioni:
>
> * [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — la capability gemella del preventivo
> * [script.fn_doc_azioni_permesse](/dbzero/script/funzioni/fn_doc_azioni_permesse) — i passaggi manuali che l'utente può fare
> * [script.fn_doc_testata_in_stato](/dbzero/script/funzioni/fn_doc_testata_in_stato) — la testata nello stato, dal lock di testata
> * [script.fn_doc_riga_modificabile](/dbzero/script/funzioni/fn_doc_riga_modificabile) — fornitura e indirizzi nello stato, dal lock dei satelliti
> * [vendite.fn_offerta_documenti_vivi](/dbzero/vendite/funzioni/fn_offerta_documenti_vivi) — il contratto o l'ordine vivo nato dall'offerta
> * [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — il guard dei passaggi di stato, che solleva con gli stessi motivi
> * [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — il verbo «Genera contratto»
> * [vendite.fn_genera_ordine_da_offerta](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta) — il verbo «Genera ordine»
> * [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — il verbo «Crea revisione»
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — come il contratto e l'ordine dichiarano di nascere dall'offerta

---

### 🎯 Scopo Principale

Le capability di un'offerta commerciale, in un unico oggetto: le azioni disponibili nello stato di
oggi, con il motivo di quelle spente, che cosa si può ancora modificare, se si può generare un
contratto o un ordine, la modalità del PDF e la nota di stato. Il dettaglio dell'offerta la
trasporta così com'è, e l'interfaccia non ricalcola nessuna regola di stato. Un'offerta che non
esiste dà un risultato vuoto, che il backend traduce in «non trovata».

---

### ⭐ Pulsanti e database non possono dissentire

Ogni motivo che spegne un'azione viene dallo **stesso** building block con cui il guard o il verbo
rifiuterebbero l'operazione: la funzione non scrive regole proprie, le chiede. Un'azione spenta
porta l'elenco dei motivi, e il primo è quello che si mostra.

* **Verso l'emissione**: il listino che si congelerebbe (`script.fn_check_listino_congelabile`), i
  prezzi non autorizzati (`script.fn_check_prezzi_autorizzati`), gli indirizzi che non sono del
  cliente (`script.fn_check_indirizzi_documento_cliente`) e, per ultime, le righe che la regola
  intera non ammette (`script.fn_check_righe_documento`, solo dallo stato iniziale).
* **Verso l'accettazione**: i prezzi non autorizzati.
* **Verso l'annullo**: un contratto o un ordine vivo nato dall'offerta
  (`script.fn_check_offerta_annullabile`).
* **«Crea revisione»**: proposta sull'offerta emessa, spenta se c'è un prezzo in attesa
  (`script.fn_check_prezzi_in_attesa`, la stessa con cui il verbo rifiuta).

Quali stati sono la bozza, l'emissione, l'accettazione e l'annullo lo dice il vocabolario degli stati
(le colonne `iniziale`, `emissione`, `accettazione`, `is_abortito`), non il codice dello stato.

---

### Le azioni, stato per stato

I passaggi manuali vengono dalla matrice, filtrati da `script.fn_doc_azioni_permesse`: matrice viva,
passaggio manuale, permesso dell'utente. Un passaggio che chiede un'azione di processo **sparisce**
per chi non ce l'ha; un passaggio che lo stato non consente resta **spento col motivo**. Le tre
azioni applicative (`crea_revisione`, `push_contratto`, `genera_ordine`) non cambiano stato, e non
hanno uno stato di destinazione.

| Stato | Azioni |
| --- | --- |
| `BOZZA` | `emetti`, `annulla` |
| `EMESSA` | `accetta`, `rifiuta`, `crea_revisione` |
| `ACCETTATA`, senza contratto né ordine vivi | `annulla`, `push_contratto`, `genera_ordine` |
| `ACCETTATA`, con un contratto o un ordine vivo | `annulla`, spenta: l'offerta vive nel documento generato |
| `RIFIUTATA`, `ANNULLATA`, `SUPERATA` | nessuna |

Il rientro automatico da `SUPERATA` a `EMESSA`, quando una revisione si annulla, non è un'azione
manuale e non compare.

---

### ⛔ Contratto e ordine: uno solo, e solo i vivi

Un'offerta accettata genera **un** documento: o il contratto o l'ordine. Le due azioni hanno quindi
la stessa abilitazione (offerta accettata, nessun contratto e nessun ordine **vivi** nati da lei), e
generato uno dei due spariscono entrambe.

* «Nato dall'offerta» è la provenienza del contratto o dell'ordine: tipo `OFFERTA_COMMERCIALE` e la
  chiave dell'offerta. La legge `vendite.fn_offerta_documenti_vivi`, la stessa sede che leggono i
  due verbi. Un documento annullato conserva la provenienza ma non consuma l'offerta.
* Con l'offerta trasformabile le due azioni sono **proposte**, e si spengono col motivo se una riga
  non può andare nel documento da generare: per il contratto le righe dell'offerta
  (`script.fn_check_righe_documento`), per l'ordine le righe espanse giudicate da ordine
  (`script.fn_check_righe_offerta_in_ordine`).
* Con l'azione non proposta, il motivo segue l'ordine «prima il proprio documento»: per il contratto
  `OFFERTA_CONTRATTO_GIA_GENERATO`, poi `OFFERTA_ORDINE_GIA_GENERATO`; per l'ordine l'inverso; in
  ogni altro stato `OFFERTA_NON_ACCETTATA`. Le chiavi di traduzione stanno sotto `vendite.offerte.`.

⚠️ La capability calcola solo che cosa proporre. La regola vera sta nei verbi, che rifiutano un
secondo contratto o un ordine accanto al contratto (e viceversa) leggendo gli stessi documenti
vivi, e negli indici unici che ammettono al più un contratto vivo e un ordine vivo per offerta.

---

### Che cosa si modifica nello stato

* **La testata**: le colonne non modificabili sono quelle «sempre» (i campi di sistema e quelli che
  scrivono i passaggi di stato: codice, uid, numero e padre della revisione, stato, date di
  emissione, accettazione, rifiuto e annullo), seguite da quelle che il lock di testata blocca nello
  stato, lette con `script.fn_doc_testata_in_stato`. La testata è modificabile se nello stato almeno
  una colonna si cambia: fuori bozza restano aperte, per esempio, le note di un documento vivo e la
  motivazione del rifiuto.
* **Fornitura e indirizzi**: dal lock montato sui satelliti, con `script.fn_doc_riga_modificabile`.
* **Le eccezioni di prezzo**: solo nello stato iniziale (la bozza), letto dal vocabolario.

---

### Il PDF e la nota di stato

La modalità del PDF e la possibilità di allegare vengono dal vocabolario degli stati. La nota di
stato è la frase che spiega lo stato in cui si trova il documento: viene dal dato dello stato, e
c'è **sempre** quando lo stato la dichiara, anche accanto a un'azione ancora accesa. Il campo è
sempre presente, col valore vuoto quando non si applica: va guardato il valore, non la presenza.

### Lo stato corrente: `stato_codice` e `stato_terminale`

`stato_codice` è il codice interno dello stato corrente. `stato_terminale` è la colonna `terminale`
del vocabolario per quello stato: vero quando il documento non ha più passaggi a mano in uscita.
Chi mostra l'offerta (il banner del drawer, per esempio) legge questo campo invece di tenere un
suo elenco degli stati terminali.

---

### Test

* `db/pgtap/script/test-fn-available-actions-offerta-v1.sql` — le azioni per stato, l'esclusività
  fra contratto e ordine coi suoi motivi, le modifiche nello stato, l'indice unico dell'ordine nato
  dall'offerta, l'emissione col listino in vigore, gli spazi delle chiavi di traduzione.
* `db/pgtap/script/test-fn-check-prezzi-autorizzati-v1.sql` — i motivi dei prezzi non autorizzati.
* `db/pgtap/vendite/test-offerta-guard-dal-vocabolario-v1.sql` — `stato_terminale`, e «in bozza»
  dallo stato iniziale: spostata la marca in transazione, `can_edit_eccezioni` la segue.
* `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql` — un documento annullato non consuma
  l'offerta.

---

### Note di migrazione

* 2026-06-08 — contratto e ordine diventano mutuamente esclusivi (`brief-db-univocita-offerta-ordine`).
* 2026-09-24 — le azioni di stato passano all'elenco dei motivi, con i prezzi non autorizzati
  (`brief-db-preventivi-congelamento-pricing`).
* 2026-10-10 — le colonne non modificabili non sono più scritte nella funzione: si leggono dal lock
  di testata (`brief-db-testata-dopo-emissione`).
* 2026-10-11 — contano i soli documenti vivi (`brief-db-annullo-documento-con-legami`).
* 2026-10-21 — righe ammesse, «Genera» proposte con il motivo, annullo dell'accettata
  (`brief-db-offerta-emissione-ed-erogazione`).
* 2026-11-07 — l'ordine nato dall'offerta si riconosce dalla provenienza del modello
  (`sorgente_tipo_id` con la chiave del documento); le colonne `documento_origine_*` dell'ordine e il
  loro indice unico sono ritirati (`brief-db-sorgente-documento-e-riga`).
* 2026-11-13 — «in bozza» dallo stato iniziale del vocabolario, non dal codice; nasce
  `stato_terminale` (`brief-db-stati-documento-dal-vocabolario`, giro 2).

---

{% include-markdown "signature-core.md" %}
