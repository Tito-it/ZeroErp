## 📘 Documentazione Concettuale – Funzione `magazzino.fn_posta_inventario`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — la testata che porta a `POSTED`
> * [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe) — le righe su cui scrive `qta_sistema`
>
> Approfondimento funzioni:
>
> * [magazzino.fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) — da dove legge
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva che chiama per riga
> * [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile) — le condizioni per registrare
> * [script.fn_sorgente_provenienza](/dbzero/script/funzioni/fn_sorgente_provenienza) — la sorgente da scrivere sui movimenti
> * [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — la porta `POSTED`
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §5b la funzione madre, §12.5.2 la madre chiama la check

---

### 🎯 Scopo Principale

**Registra un inventario confermato.** Legge il [piano](/dbzero/magazzino/funzioni/fn_inventario_piano),
scrive su ogni riga la quantità che il registro diceva (`qta_sistema`: la fotografia contro cui
il conteggio è stato posto, e resta), posta con la primitiva ogni riga con differenza, porta la
testata a `POSTED`. Ritorna, riga per riga, il movimento scritto.

È **una transazione sola** per costruzione: se una riga è rifiutata (la merce non c'è,
l'articolo non è gestito), non resta niente e il documento resta `CONFIRM`.

---

### È un verbo: il permesso viene per primo

La prima cosa che fa è chiedere il permesso `registra_magazzino`, lo stesso che il backend
chiede all'endpoint: senza permesso, o senza un utente in sessione, si ferma con
`E_PERMESSO_NEGATO`.

Gira con i permessi del **proprietario** delle tabelle: è la sola strada verso la primitiva,
che l'applicazione non chiama più direttamente.

---

### Le condizioni per registrare non sono scritte qui

Le dice [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile)
— stato `CONFIRM`, almeno una riga, nessuna riga che la primitiva rifiuterebbe — e questa
funzione ne solleva il **primo motivo**. È la stessa funzione da cui la capability del drawer
accende o spegne il pulsante «Registra»: il rifiuto e il suggerimento sul pulsante non possono
divergere, perché vengono dalla stessa sede.

---

### Che cosa posta

* la **differenza** fra quantità contata e quantità a registro, alla grana della riga
  (articolo, ubicazione, lotto, seriale); differenza zero = nessun movimento;
* la **causale** la decide il registro: `INV_INIZIALE` se quell'articolo non ha nessun
  movimento nel magazzino (è il primo carico in assoluto), altrimenti `RETT_POS` / `RETT_NEG`;
* la **sorgente** è l'inventario (tipo `INVENTARIO`) con la riga in `sorgente_riga`, il **costo** è quello della riga solo su
  un'entrata (un'uscita va alla media), la **data** del movimento è l'inizio del giorno
  operativo della data dell'inventario;
* le posizioni `NON_CONTATA` del piano restano com'erano — informazione, non blocco;
* una riga `NON_POSTABILE` fa rifiutare tutto, col primo motivo della stessa check che il piano
  aveva mostrato.

---

### La porta, e il lock sulla testata

Un inventario va a `POSTED` **solo** da qui: la funzione si firma con un'impostazione di
sessione valida per la sola transazione (`zeroerp.magazzino_posting_inventario`, che porta
l'id del documento). Il [guard di famiglia](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)
la pretende per ammettere lo stato, e le righe in `CONFIRM` la accettano per lasciar scrivere
`qta_sistema`. Un aggiornamento diretto a `POSTED` è rifiutato.

La testata si blocca in scrittura **prima** di ogni domanda: è il lock che serializza due
registrazioni dello stesso documento (la check, che si limita a leggere, non può prenderlo).
Il secondo trova `POSTED`.

Poiché la funzione gira da proprietario, la sicurezza di riga qui non vale: il perimetro
dell'operatore lo rimette lo stesso predicato della policy, applicato alla lettura della
testata. Fuori perimetro il documento **non c'è** (`E_MAG_DOCUMENTO_NON_TROVATO`, lo stesso
«non trovato» di un id inesistente), e non si prende nessun lock.

---

### Codici errore

* `E_PERMESSO_NEGATO` — manca il permesso `registra_magazzino`, o manca l'utente in sessione.
* `E_MAG_CHIAMATA_NON_VALIDA` — l'inventario manca o non è un identificativo valido.
* `E_MAG_DOCUMENTO_NON_TROVATO` — inventario inesistente o fuori perimetro.
* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` — l'inventario non è in `CONFIRM`.
* `E_MAG_DOCUMENTO_SENZA_RIGHE` — l'inventario non ha righe.
* il primo motivo di una riga non postabile, con il codice della check.
* `E_SORG_CONF` — il tipo `INVENTARIO` non è a catalogo in `config.sorgenti` o non è attivo (dal BB
  che compone la sorgente).
* i codici della primitiva, se una riga viene rifiutata alla scrittura.

---

### Test

`db/pgtap/magazzino/test-fn-posta-inventario-v1.sql`.

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§4.5, D-L2-f, D-L2-n).
* 2026-09-22 — `brief-db-magazzino-lotto-2-bis-be-fe` (R-1): le condizioni per registrare
  escono dal corpo e passano alla check condivisa con la capability. Codici, valori e frasi
  restano quelli di prima.
* 2026-09-24 — `brief-db-magazzino-verbi-con-permesso` (D-4): diventa un verbo, con il
  permesso in testa e i privilegi del proprietario.
* 2026-11-08 — `brief-db-sorgente-documento-e-riga`: la sorgente dei movimenti diventa il
  documento con la riga (prima il tipo `INVENTARIO_RIGA`, ritirato), composta da
  `script.fn_sorgente_provenienza`; un tipo mancante o spento è `E_SORG_CONF`, non più
  `E_CONFIG_MANCANTE`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
