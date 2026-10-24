## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_annullabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
>
Approfondimento funzioni:
> • [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile)
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-08-15)

Elenca i motivi che impediscono di **annullare** un ordine: merce già uscita con un DDT figlio
vivo (MOTIVO 1), oppure **righe di commessa già `EMESSA`** (MOTIVO 2).

> ⛔ **rev 26-08-2026 — il MOTIVO 2 è cambiato, e non di poco.**
> Fino a quella data bastava che l'ordine **avesse spinto** in commessa perché
> l'annullamento fosse rifiutato (`E_ORD_ANNULLA_IN_COMMESSA`). Quel divieto è
> stato **ritirato**: il motivo per cui esisteva era che **non c'era modo di
> disfare il push**, e adesso c'è — alla chiusura il documento **ritira da sé**
> le righe che nessuno ha ancora emesso
> (rev 2026-10-11: non più in silenzio — le righe `NON_EMESSA` sono legami, l'annullo chiede
> conferma e le ritira il verbo di annullo, BB
> [`vendite.fn_documento_ritira_legami`](/dbzero/vendite/funzioni/fn_documento_ritira_legami);
> brief-db-annullo-documento-con-legami, D-5).
>
> ⭐ Resta un freno solo, e su una condizione **vera**: le righe già `EMESSA`
> sono in volo verso una fattura. E ha una via d'uscita che il messaggio nomina —
> [«Riporta da emettere»](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere)
> le riporta a `NON_EMESSA`, e da lì il ritiro le prende.
>
> ⭐ Il conteggio **non si scrive più qui**: si delega a
> [`script.fn_check_sorgente_chiudibile`](/dbzero/script/funzioni/fn_check_sorgente_chiudibile),
> la stessa che il guard generico usa. *Una implementazione, due superfici* —
> questa accende il pulsante, quella ferma la scrittura.
>
> ⚠️ **E la chiave è cambiata insieme al criterio.** Il vecchio conteggio leggeva
> `vendite.commesse_sorgenti` con `id::text`; la primitiva legge
> `vendite.commesse_attivita` con `uid::text`. Sono chiavi polimorfe **diverse e
> deliberate**: passare quella vecchia non darebbe un errore, darebbe **zero
> motivi**.
>
> ⚠️ `E_ORD_ANNULLA_IN_COMMESSA` **non è stato cancellato**: resta a catalogo con
> `obsoleto_dal = 2026-08-26` e smette di essere sollevato.
> Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, Q-9.

---

### ⚠️ Qui `sorgente_uid` **è** il legame — al contrario del gemello

Il DDT si aggancia al padre con `ddt.sorgente_uid` (uuid, punta all'`uid` dell'ordine) più
`sorgente_tipo_id`. È la catena diretta, e la colonna è popolata.

⛔ **Non trasportare questa forma sul preventivo**: là la colonna omonima è l'origine *import*
e non il legame al padre. È la stessa parola per due cose diverse, ed è precisamente ciò che
ha tenuto spento per tre changeSet il MOTIVO 1 del gemello.

⛔ **rev 26-08-2026** — il MOTIVO 2 usava la chiave **`id::text`** su
`vendite.commesse_sorgenti`, perché per `ORDINE_VENDITA` il `key_selector` della
sorgente polimorfa dice `id` e non `uid`. Adesso legge
`vendite.commesse_attivita`, dove `sorgente_uid` porta **`uid::text` per tutte le
sorgenti** — verificato sul corpo delle cinque `fn_list_*_da_pushare`.

⚠️ **Le due tabelle usano chiavi polimorfe diverse per la stessa sorgente**, e
non è disordine: `commesse_sorgenti` registra *chi* ha spinto (con la chiave
dichiarata dal catalogo), `commesse_attivita` porta *cosa* è stato spinto (con
l'`uid` che il push scrive). Confonderle non produce un errore: produce **zero
motivi**, cioè un freno che lascia passare tutto.

⭐ Tre legami nella stessa funzione, tre chiavi diverse: è il modello polimorfo,
e va letto ogni volta invece che dedotto per simmetria.

---

### 🔴 «Asimmetria latente, oggi non morde» — su dati di test

Fino al 2026-08-15 il MOTIVO 1 contava **anche i DDT annullati**, mentre il gemello sul
preventivo li escludeva già dal 10 agosto.

La lacuna era stata classificata *«asimmetria latente, oggi non morde»* perché **nessun DDT
bloccante risultava annullato** — ⚠️ **ma era una conta su dati di TEST**.

In esercizio annullare un DDT è ordinario: destinatario sbagliato, merce sbagliata, duplicato.
L'ordine il cui unico figlio fosse stato annullato sarebbe rimasto bloccato **per sempre**.

⭐ È il caso da tenere a mente ogni volta che una misura sul database di sviluppo dice «non
succede»: la domanda giusta è *«può succedere?»*, non *«è successo?»*.

---

### ⚠️ Esclude solo l'annullato, non il reso

Il predicato è `is_abortito IS NOT TRUE`. Un DDT in stato **RESO** ha `is_abortito = false` e
**continua a bloccare** — ed è giusto: la merce è tornata, ma il documento è vissuto.

---

### Codici errore

| Codice | Motivo |
|--------|--------|
| `E_ORD_ANNULLA_CON_DDT` | Esiste un DDT figlio vivo |
| `E_SORGENTE_CON_RIGHE_EMESSE` | Ci sono righe di commessa già `EMESSA` (delegato a `fn_check_sorgente_chiudibile`) |
| ~~`E_ORD_ANNULLA_IN_COMMESSA`~~ | ⛔ **ritirato il 26-08-2026**: resta a catalogo, non viene più sollevato |
| `E_PARAMETRO_INVALIDO` | `ordine_id` nullo o non positivo |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}` — l'ordine è quello di gravità, chi solleva prende
il **primo**.

⭐ **Sorgente unica** per il guard di transizione (che solleva) e per
`fn_available_actions_*` (che espone `disabled` + `reasons`): il bottone della UI e il rifiuto
del database non possono divergere, perché leggono lo stesso verdetto.

⚠️ Unica eccezione alla purezza: `id` nullo o `<= 0` solleva `E_PARAMETRO_INVALIDO` — errore
di programmazione, non condizione di dominio.

⚠️ **Documento inesistente ⇒ `[]`, cioè «nessun ostacolo».** La funzione non distingue
«annullabile» da «non esiste»: la decisione è lasciata al chiamante. Nel percorso reale il
guard gira su un `UPDATE` di una riga che esiste per definizione, quindi il caso non si
presenta — ma chi la chiamasse da fuori quel percorso deve saperlo.

---

{% include-markdown "signature-core.md" %}
