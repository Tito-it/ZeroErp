# Guida — Le operazioni che non si ripetono

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari**: analisti funzionali, chi assiste gli operatori, sviluppatori database,
> backend e frontend che vogliono il quadro prima del dettaglio
>
> **Vedi anche** — schemi DB:
>
> * [dbops.idempotency_keys](/dbzero/dbops/tabelle/idempotency_keys) — il registro delle key: campi, regole, scadenza
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [dbops.fn_idempotency_prenota](/dbzero/dbops/funzioni/fn_idempotency_prenota) — la prenotazione di una key e la risposta al backend
>
> **Vedi anche** — API e service backend:
>
> * [API — regole comuni](/dev/api) — sezione «Idempotency-Key»: l'header, chi lo pretende, la modalità forte
> * [API endpoint helpers](/backend/core/manual/api_endpoint_helpers) — come il backend prenota, esegue e registra l'esito
>
> **Vedi anche** — guide correlate:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — la scadenza delle key e la pulizia periodica
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — i codici che l'operatore può vedere
> * [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri) — dove sta la soglia di ripresa

---

## Il problema

Alcune operazioni non si devono fare due volte: emettere le fatture di un lotto, numerarle,
registrare una distinta di incasso, registrare un documento di magazzino, cancellare un fondo.
Eppure la stessa richiesta può arrivare due volte al server:

* l'operatore clicca due volte, o riclicca perché la risposta tarda;
* la rete perde la risposta e il browser ripete l'invio;
* l'operatore riprova dopo un errore di rete, senza sapere se la prima volta è andata.

ZeroErp risolve il problema con una **chiave di idempotenza** (Idempotency-Key): un codice unico
che accompagna la richiesta. Se il server riceve due volte la stessa chiave, sa che è la stessa
operazione e non la rifà.

---

## La chiave: una per gesto

La chiave la crea il **frontend**, non l'operatore.

* Su ogni chiamata che scrive il frontend mette una chiave nuova. Basta contro la rete che
  ripete un invio, ma non contro l'operatore che riclicca: per il frontend un secondo clic è una
  chiamata nuova.
* Sui **gesti irreversibili** la chiave appartiene al **gesto**, non alla chiamata. Finché
  l'operatore ripete lo stesso gesto con gli stessi dati, il frontend rimanda la stessa chiave;
  se cambia i dati, è un'operazione diversa e la chiave è nuova. Dopo un successo, o dopo dieci
  minuti, la chiave si rinnova: un reinvio vero arriva a ridosso del primo.

Il **backend** pretende la chiave su ogni POST che scrive, e risponde 400 se manca. Il controllo
completo (riconoscere il secondo invio e non rifarlo) agisce sugli endpoint che lo chiedono,
quando la **modalità forte** è accesa nell'ambiente. Il dettaglio sta in
[API — regole comuni](/dev/api), sezione «Idempotency-Key».

---

## Che cosa risponde il server

Quando arriva una richiesta con la chiave, il backend la **prenota** nel database, prima di fare
qualunque cosa. Il database guarda se la chiave c'è già e risponde con uno di tre esiti:

| Esito | Quando | Che cosa fa il backend | Che cosa vede l'operatore |
| --- | --- | --- | --- |
| **Esegui** | la chiave è nuova, oppure si può riprendere (vedi sotto) | esegue l'operazione | il risultato dell'operazione |
| **Rimanda** | l'operazione con questa chiave è già stata fatta | rimanda la risposta della prima volta, senza rifare niente | lo stesso risultato della prima volta, come un successo normale |
| **In corso** | un'altra richiesta con questa chiave sta ancora lavorando | risponde 409 | «L'operazione è ancora in corso»: attendere qualche secondo e riprovare |

A operazione finita il backend registra l'esito: **fatta**, con la risposta da rimandare, oppure
**fallita**.

```text
primo clic   → prenota: chiave nuova     → Esegui    → operazione → esito «fatta»
secondo clic → prenota: chiave «fatta»   → Rimanda   → stessa risposta, nessuna operazione
clic durante → prenota: chiave «in corso»→ In corso  → 409, l'operatore riprova dopo
```

---

## La chiave è di chi l'ha prenotata

Una chiave vale solo per **lo stesso utente** sulla **stessa richiesta** (metodo e indirizzo
dell'endpoint). Se arriva da un altro utente, o su un'altra richiesta, il database la rifiuta
con un errore 400 (`E_IDEMPOTENCY_KEY_RIUSATA`) invece di rimandare la risposta: quella
risposta è dell'operazione di qualcun altro, e non va mostrata.

Una richiesta senza utente (anonima) conta come un utente a sé: non può usare la chiave di
nessun altro.

---

## Quando una chiave si riprende

Una chiave si **riprende** quando l'esito di prima non basta a dire «è fatta»: allora il
database risponde **Esegui** anche se la chiave esiste già, e l'operazione si rifà.

* **Una chiave fallita si riprende sempre.** L'esito l'ha scritto il backend: si sa che
  l'operazione non è andata, e riprovarla è il comportamento atteso.
* **Una chiave rimasta «in corso» troppo a lungo** si riprende **solo se l'operazione lo
  ammette.**

### Perché una chiave resta «in corso»

Se il server si ferma mentre lavora (un riavvio, un aggiornamento, un processo bloccato e
ucciso), nessuno scrive l'esito: la chiave resta «in corso» per sempre, e ogni reinvio
riceverebbe «L'operazione è ancora in corso».

Il server web ha un tempo massimo per ogni richiesta: oltre quel tempo la interrompe. Una chiave
«in corso» da più della **soglia di ripresa** (oggi 120 secondi, sopra il tempo massimo di una
richiesta) non può appartenere a una richiesta ancora viva: chi lavorava si è fermato.

### Le operazioni in un passo e quelle a passi

Riprendere è sicuro solo se l'operazione interrotta **non ha salvato niente**. Dipende da come
è fatta, e lo dichiara il backend per ogni endpoint:

| Tipo | Com'è fatta | Una chiave «in corso» oltre la soglia |
| --- | --- | --- |
| **In un passo** | l'operazione e il suo esito «fatta» si salvano insieme, tutto o niente, e l'operazione finisce dentro la richiesta | **si riprende**: se l'esito manca, manca anche l'operazione |
| **A passi** | l'operazione salva un passo alla volta (per esempio la fatturazione di un lotto, la numerazione di un lotto, l'invio delle commesse) | **resta «in corso»**: una parte del lavoro può essere già salvata, e riprenderla la rifarebbe |

Per un'operazione a passi la chiave rimasta «in corso» si chiude in due modi: scade, oppure
l'operatore fa un gesto nuovo e il frontend genera una chiave nuova. Lo stato vero del lavoro
lo dicono i registri dell'operazione stessa (lo stato del lotto, dei suoi passi), non la chiave.

⚠️ **La soglia deve restare sopra il tempo massimo di una richiesta.** Se il tempo massimo del
server web viene alzato sopra la soglia, una richiesta ancora viva potrebbe essere ripresa da
un reinvio, e l'operazione girerebbe due volte. Le due impostazioni vanno cambiate insieme: la
soglia sta nei parametri di sistema (`SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`), il tempo massimo
nella configurazione del server web. Il backend lo controlla da sé: all'avvio, e a ogni ricarica della configurazione, rifiuta di partire
se la soglia non supera il tempo massimo di almeno 30 secondi, o se il server web è configurato
in un modo in cui una richiesta non ha un tempo massimo.

---

## Quanto vive una chiave

Una chiave serve solo finché il frontend può rimandare la **stessa** richiesta, cioè per la
durata di un gesto (al massimo dieci minuti). Per questo la sua riga nel registro vive **un
giorno**: la scadenza si scrive quando la chiave nasce, e la pulizia periodica del database
cancella le righe scadute. Il dettaglio sta in [Audit e tracciabilità](/guide/audit-e-tracciabilita),
sezione «7. Manutenzione e retention».

---

## In sintesi

* Una chiave per gesto, creata dal frontend; il backend la pretende su ogni POST che scrive.
* Il database risponde **Esegui**, **Rimanda** o **In corso**; il secondo invio non rifà mai
  un'operazione già fatta.
* Una chiave vale solo per chi l'ha prenotata, sulla stessa richiesta.
* Una chiave fallita si riprende sempre; una «in corso» oltre la soglia solo per le operazioni
  in un passo.
* Una chiave vive un giorno.

---
{% include-markdown "signature-core.md" %}
