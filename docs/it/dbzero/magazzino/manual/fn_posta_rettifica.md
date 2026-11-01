## 📘 Documentazione Concettuale – Funzione `magazzino.fn_posta_rettifica`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — la testata che porta a `POSTED`
> * [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — le righe con il delta da postare
>
> Approfondimento viste:
>
> * [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — dove si vede una promessa non più mantenibile
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — la gemella, con un passo in più (il piano)
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva che chiama per riga
> * [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile) — le condizioni per registrare
>
> Guide:
>
> * [Linee guida SQL](/linee-guida-sql) — §12.5.2 la madre chiama la check

---

### 🎯 Scopo Principale

**Registra una rettifica confermata**: la *correzione a mano* che il modello promette («la
correzione a mano È una rettifica»). Per ogni riga posta con la primitiva il delta **dato**
(`qta_delta`, con segno) con `RETT_POS` o `RETT_NEG` secondo il segno, sorgente
`RETTIFICA_RIGA`, il costo della riga solo su un'entrata; poi porta la testata a `POSTED`. Una
transazione sola; ritorna i movimenti scritti.

Ha la stessa forma dell'inventario con un passo in meno: il delta non si calcola, è scritto
sulla riga. Sono gli stessi anche il permesso in testa, la porta
(`zeroerp.magazzino_posting_rettifica`), i rifiuti sulla testata (non trovata, non `CONFIRM`,
senza righe) e il «tutto o niente».

---

### È un verbo: il permesso viene per primo

La prima cosa che fa è chiedere il permesso `registra_magazzino`, lo stesso che il backend
chiede all'endpoint (`E_PERMESSO_NEGATO`, anche senza un utente in sessione). Gira con i
permessi del **proprietario** delle tabelle: è la sola strada verso la primitiva.

Poiché gira da proprietario, la sicurezza di riga qui non vale: il perimetro dell'operatore lo
rimette lo stesso predicato della policy, applicato alla lettura della testata. Fuori perimetro
la rettifica **non c'è** (`E_MAG_DOCUMENTO_NON_TROVATO`), e non si prende nessun lock.

---

### Le condizioni per registrare non sono scritte qui

Le dice [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile)
— stato `CONFIRM`, almeno una riga, nessuna riga che la primitiva rifiuterebbe — e questa
funzione ne solleva il **primo motivo**. È la stessa funzione da cui la capability del drawer
accende o spegne il pulsante «Registra»: il rifiuto e il suggerimento sul pulsante vengono
dalla stessa sede.

Il blocco in scrittura della testata resta **primo**: è il lock che serializza due
registrazioni dello stesso documento, e la check, che si limita a leggere, non può prenderlo.

⚠️ Per la rettifica questo vuol dire che una riga non postabile (articolo non gestito,
ubicazione mancante dove il magazzino le usa) viene rifiutata **prima** di toccare il registro,
con lo stesso codice e la stessa frase che darebbe la primitiva. È la simmetria con
l'inventario, non una regola nuova.

---

### ⭐ I blocchi no, il fisico sì

Una rettifica negativa **ignora i blocchi** (una promessa) ma **non il fisico**: registra un
fatto sulla merce, e un magazzino che non può registrare ciò che vede mente. Se dopo la
rettifica una promessa non è più mantenibile, lo dice
[vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) (disponibile negativo), non un
rifiuto del conteggio.

---

### Codici errore

* `E_PERMESSO_NEGATO` — manca il permesso `registra_magazzino`, o manca l'utente in sessione.
* `E_MAG_CHIAMATA_NON_VALIDA` — la rettifica manca o non è un identificativo valido.
* `E_MAG_DOCUMENTO_NON_TROVATO` — rettifica inesistente o fuori perimetro.
* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA` — la rettifica non è in `CONFIRM`.
* `E_MAG_DOCUMENTO_SENZA_RIGHE` — la rettifica non ha righe.
* il primo motivo di una riga non postabile, con il codice della check.
* `E_CONFIG_MANCANTE` — la sorgente `RETTIFICA_RIGA` non è a catalogo o non è attiva.
* i codici della primitiva, se una riga viene rifiutata alla scrittura.

---

### Test

`db/pgtap/magazzino/test-fn-posta-rettifica-v1.sql`.

---

### Note di migrazione

* 2026-09-18 — nasce con `brief-db-magazzino-lotto-2-motore` (§4.5, D-L2-g).
* 2026-09-22 — `brief-db-magazzino-lotto-2-bis-be-fe` (R-1): le condizioni per registrare
  passano alla check condivisa con la capability. Prima una riga non postabile la fermava la
  primitiva a metà ciclo, con lo stesso codice; la transazione annullava comunque tutto.
* 2026-09-24 — `brief-db-magazzino-verbi-con-permesso` (D-4): diventa un verbo, con il
  permesso in testa e i privilegi del proprietario.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
