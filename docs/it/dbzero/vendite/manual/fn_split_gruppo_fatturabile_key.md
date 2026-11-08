## 📘 Documentazione Concettuale – Funzione `vendite.fn_split_gruppo_fatturabile_key`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — **la gemella, da leggere insieme**
> * [vendite.fn_riferimento_gruppo_fatturabile](/dbzero/vendite/funzioni/fn_riferimento_gruppo_fatturabile) — chi la usa per dare un nome alla chiave
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — chi risolve il documento dalla chiave in testo
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — §5, le chiavi in testo

---

### 🎯 Scopo Principale

Il **verso inverso** di `vendite.fn_build_gruppo_fatturabile_key`: da una chiave di gruppo fatturabile torna ciò da cui è stata costruita.

| Chiave | Torna |
| --- | --- |
| `<codice_interno>:<uid>` | il tipo del documento (`sorgente_tipo_id`) e il suo uid **in testo** (`sorgente_uid`) |
| `MAN:<commessa_id>` | la commessa |
| qualsiasi altra cosa | tre `NULL` |

---

### Perché esiste

Chi legge una **segnalazione** ha in mano solo la chiave: `gruppo_key` è tutto ciò che
`vendite.fatturazione_lotti_log` e `vendite.fatturazione_lotti_esiti` contengono. Per mostrare
il **numero** del documento bisogna tornare al documento, e questa funzione è la strada.

---

### ⚠️ L'uid della chiave è testo, ed è sempre l'uid del documento

La chiave di gruppo contiene l'**uid** del documento per ogni tipo, anche per quelli che il
modello della provenienza riconosce per `id`: la chiave non segue `config.sorgenti.key_selector`.
Per questo la funzione restituisce l'uid come **testo**, così come sta nella chiave, e non lo
scrive nelle colonne tipizzate del modello (`sorgente_id` / `sorgente_uid` uuid).

Chi deve arrivare al documento non lo traduce da sé: passa tipo e testo al ponte delle chiavi in
testo, [`script.fn_sorgente_documento_da_chiave`](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave),
che riconosce la forma canonica e risolve come il BB che risolve. È ciò che fa
`vendite.fn_riferimento_gruppo_fatturabile`, attraverso `vendite.fn_get_sorgente_documento_ref`.

---

### ⛔ Le due funzioni sono gemelle e si leggono insieme

Il prefisso `MAN` e la forma della chiave sono decisi **nella funzione che costruisce**. Qui si
**rileggono**.

⚠️ È una duplicazione che nessun occhio può presidiare, quindi non la presidia l'occhio: il
presidio è un pgTAP di **andata e ritorno** — lo split di una chiave costruita restituisce ciò
da cui è stata costruita, su entrambe le forme. Se la forma cambia da una parte e non
dall'altra, quel test diventa rosso.

È lo stesso argomento che la gemella usa per vietare la scorciatoia opposta (ricavare il gruppo
dal `segment_key` spezzandolo sui prefissi, una convenzione di leggibilità che nessuno si è
impegnato a mantenere). Per questo lo split è una funzione **dichiarata** invece che una riga
sparsa.

---

### Regole

* ⛔ **Non solleva mai.** La chiama una lista: una chiave storta deve produrre un ripiego, non una
  lista rotta. Torna **sempre una riga**, con tre `NULL` quando non riconosce la forma;
* ⚠️ il resto della chiave dopo il primo `:` si prende per intero: una chiave malformata con un
  secondo `:` non viene **troncata in silenzio**, perché un troncamento silenzioso è peggio di un
  ripiego dichiarato;
* l'aggancio del tipo è su **`codice_interno`** (immutabile), mai su `codice`: al primo rename
  fatto dall'utente la risoluzione smetterebbe **senza dire niente**;
* nessun filtro su `attivo`: un documento nato da un tipo poi disattivato resta quel documento, e
  la segnalazione che lo nomina va letta comunque;
* `STABLE`, `SECURITY INVOKER`.

---

### ⚠️ Non risale a `commesse_attivita`, ed è una scelta

Sembra la via ovvia: cercare la riga di commessa la cui chiave combacia. Ma la `gruppo_key`
scritta su una segnalazione è un **fatto storico**, e quel lavoro può essere già fatturato,
annullato o uscito dal giro: la risoluzione si svuoterebbe **proprio dopo** — e una segnalazione
si legge dopo.

⭐ Spacchettare la chiave dipende solo dal **documento**, che resta.

---

### Note di migrazione

* 2026-09-08 — nasce insieme alla lettura delle segnalazioni per gruppo: prima chi aveva in mano
  solo la chiave non poteva tornare al documento (brief-db-uscita-documento-dal-giro §6.2).
* 2026-11-07 — la gemella dichiara che l'uid della chiave è testo e vale per ogni tipo; la
  risoluzione del documento passa al ponte delle chiavi in testo del modello della provenienza
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
