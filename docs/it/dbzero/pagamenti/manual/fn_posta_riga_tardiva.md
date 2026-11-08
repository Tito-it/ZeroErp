## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_posta_riga_tardiva`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la riga sospesa che registra
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — dove nasce il movimento
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta già registrata, che resta com'è
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — la gemella, che registra una distinta intera
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — la quarta mossa, e la sua porta
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — coerenza e capienza della rata, col doppio tempo
> * [pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) — i dati che l'abbinamento pretende
> * [pagamenti.trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione) — la matrice degli stati della riga
> * [pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga) — il mirror che deriva i riferimenti del movimento dalla riga

---

### 🎯 Scopo Principale

Registra in ritardo una riga contabile rimasta `SOSPESA` sotto una distinta già
registrata: la abbina — fattura, cliente, rata facoltativa, forzatura a due tempi — e la
registra nello stesso gesto. Movimento scritto, riga a `POSTATA`, distinta che **resta
`CHIUSA`** senza toccare la sua conferma.

È la strada del «resto» (*«registra il pronto, lascia lì il resto»*). Senza di lei il resto
non ne avrebbe: sotto una `CHIUSA` la quarta mossa rifiuta a qualunque riga di diventare
pronta, la correzione salta le righe non registrate, nessun verbo la sposta altrove, e una
sospesa potrebbe solo restare, o oscillare con `SCARTATA`. *Il buco è la somma di tre
decisioni giuste prese in momenti diversi.*

---

### ⛔ È una decisione di una persona, mai un job

La chiama solo il verbo del backend che registra una riga — dalla coda «Sospese» quando la
distinta è registrata («Abbina e registra») e dal drawer di una distinta chiusa — con
lo **stesso permesso della registrazione** (`registra_distinta`): muove denaro. La tardiva è
una **decisione** di chi ha identificato quel denaro, e nessun processo automatico la prende al
suo posto.

---

### ⭐ Passa da `ABBINATA`, e alla quarta mossa si presenta

La funzione non porta la riga da `SOSPESA` a `POSTATA` in un colpo. La porta prima
ad **`ABBINATA`** con la destinazione, così girano **tutti** i guard dell'abbinamento normale:
la transizione (`SOSPESA → ABBINATA` è in matrice), i dati (fattura e cliente), la **rata** —
coerenza, e capienza col doppio tempo: il primo tentativo senza forzatura riceve
`E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con la richiesta di conferma, il secondo passa con la
forzatura — e lo scope.

Alla **quarta mossa** del guard sulla distinta finale, che rifiuterebbe l'ingresso in uno
stato pronto sotto una `CHIUSA`, si **presenta** con un'impostazione valida per la sola
transazione, `app.registrazione_tardiva_riga_id`, che porta l'id della riga: il guard
apre **solo** per quella riga, **solo** in quella transazione, **solo** nel ramo del cambio di
stato. Il precedente in casa è `app.cessazione_automatica`. ⚠️ La porta si **richiude in coda
alla funzione**, non al commit: dopo il ritorno nessun'altra scrittura la trova aperta.

Poi il **movimento**, poi **`POSTATA`**: istruzioni separate sulla stessa riga, perché con la
RLS attiva padre e figlio nella stessa istantanea non si vedono — la stessa ragione delle due
istruzioni della registrazione della distinta.

---

### Perché così e non altrimenti

| Alternativa | Perché no |
| --- | --- |
| ricreare la riga in una distinta «di recupero» | raddoppia l'euro: una scartata il giorno 1, una nuova il giorno 30, più un legame per non contarla due volte |
| allentare la quarta mossa (`ABBINATA` ammessa sotto `CHIUSA`, poi «Registra riga») | riapre esattamente il caso che la mossa chiude: una riga «in lavorazione» nei saldi che aspetta qualcuno |
| `SOSPESA → POSTATA` diretta in matrice | salta il guard della capienza, che gira solo entrando in uno stato pronto |

---

### Il movimento è di oggi, la distinta resta quella di ieri

La data effettiva del movimento è la data di pagamento della riga, o, se manca, la data
contabile della distinta; la data contabile è quella della distinta; **data di registrazione
e data di contabilizzazione sono il giorno operativo**: la distinta porta la data della
*prima* registrazione, il movimento la sua. Il `meta` porta l'origine `POSTING_TARDIVO`, che
nel giornale lo distingue dal `POSTING` della distinta. Fattura, cliente, distinta e rata non
si scrivono sul movimento: li deriva dalla riga il mirror, che a quel punto li ha.

La distinta **non cambia**: stato, `data_conferma` e `user_conferma` restano quelli della
prima registrazione. La **quadratura del giorno regge**: la riga era già contata, perché la
quadratura conta tutte le righe attive, sospese comprese. Chi ha registrato tardi sta
sull'audit del movimento.

---

### ⛔ Nessun «niente da registrare»

A differenza della registrazione della distinta, una tardiva su una riga che non si può
registrare è un **rifiuto**, non un esito: chi preme ha identificato quel denaro, e *«non ho
fatto niente»* detto con una risposta positiva sarebbe una bugia.

La forzatura senza motivo è **ammessa**, come sull'abbinamento normale.

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` — riga o fattura nulle o non positive, cliente o rata non
  positivi: un chiamante rotto, perché il backend valida il form prima (tecnico). Il cliente
  mancante **non** è un rifiuto di qui: risponde il guard sui dati entrando in `ABBINATA`,
  col campo da accendere.
* `E_RIGA_CONTABILE_NON_TROVATA` — la riga non si legge: inesistente o di un altro, senza
  dire quale dei due.
* `E_RIGA_CONTABILE_TARDIVA_STATO` — la riga non è attiva o non è `SOSPESA`: da `SCARTATA`
  si passa prima da «Riprendi»; da `POSTATA` il movimento c'è già.
* `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` — la distinta non è registrata (finale
  **e** con la conferma scritta): annullata, chiusa senza registrazione, o ancora aperta. Per
  quella c'è il giro normale.
* `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`, `E_RIGA_CONTABILE_RATA_INCOERENTE`,
  `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` — dai guard dell'abbinamento, come sul giro
  normale.
* `E_CONTABILE_STATO_NON_CONFIGURATO` — manca a catalogo `ABBINATA` o `POSTATA` (tecnico).

---

### Test

`db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — il caso buono con i suoi invarianti
(movimento, riga, distinta invariata, somma invariata, saldo della rata), il doppio tempo
della capienza, i rifiuti, e la **porta**: un aggiornamento a mano resta rifiutato,
l'impostazione con un altro id non apre, dopo la funzione è vuota.

---

### Note di migrazione

* 2026-09-18 — nasce, insieme alla porta della quarta mossa.

---

{% include-markdown "signature-core.md" %}
