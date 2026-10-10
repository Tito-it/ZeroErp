# Brief DB — Gli indirizzi del documento seguono il cliente

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10. **A chi:** team DB; poi BE/FE (§6).
> **Origine:** §12.3 di [brief-db-esecutivi-ba-coppia](../work-done/brief-db-esecutivi-ba-coppia.md).
> Dal giro di quel brief il cliente di un DDT si sceglie, si cambia e si toglie **in bozza**. Gli
> indirizzi del documento gia' scritti non lo seguono.
> **Stato:** 📝 **aperto, decisioni di Tid chiuse il 2026-10-10 (§4), nessun codice.**
> **Nel registro dei difetti DB:** voce **D27** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La regola

Un indirizzo del documento preso dall'anagrafica e' **del cliente del documento**. Se il cliente
cambia, quell'indirizzo non e' piu' valido. Restano validi solo gli indirizzi **una-tantum**, scritti
a mano: per D-4 del brief d'origine, la consegna a terzi passa da li'.

Oggi la regola la tiene solo il backend, e solo quando l'indirizzo viene scritto. Dopo non la
ricontrolla nessuno.

## 2. Che cosa c'e' oggi

**Gli snapshot.** Ci sono sei tabelle: `vendite.{ddt,ordini,preventivi,offerte_commerciali,contratti,fatture}_indirizzi`,
con uno slot per tipo (`uq_*_uno_per_tipo`). Ogni riga dice da dove viene:

| `origine_indirizzo_id` | `origine_soggetto_ruolo_id` | Che cos'e' |
| --- | --- | --- |
| valorizzato | valorizzato | layer RUOLO: una riga di `anagrafiche.indirizzi` (eventualmente di un'istanza) |
| NULL | valorizzato | layer SOGGETTO: dall'anagrafica del soggetto |
| NULL | NULL | una-tantum, scritto a mano |

**L'auto-assegnazione alla creazione la fa solo il backend.**
`auto_assegna_indirizzo_default` (`backend/apps/vendite/services/_indirizzi_documento_helpers.py`)
sceglie lo slot di default: CON, se manca FATT, se manca il primo tipo ammesso. Poi risolve
l'indirizzo con `script.fn_resolve_indirizzo_documento(ruolo, istanza, tipo)`, prima RUOLO e poi
SOGGETTO, con l'istanza che ha la precedenza. E' best-effort: se fallisce scrive un warning e il
documento nasce senza indirizzo. Se lo slot e' gia' pieno, per esempio per la cascata dal documento
sorgente (`fn_genera_ddt_da_ordine` sez. 4-bis, `fn_genera_ddt_riconsegna`), non lo tocca. La
chiamano DDT, ordine, preventivo, offerta e contratto.

**Il controllo che l'indirizzo sia del cliente lo fa solo il backend, e solo in scrittura**
(`upsert_indirizzo_documento`, stesso file): `origine_soggetto_ruolo_id` deve essere il ruolo del
documento. Lato DB su `*_indirizzi` c'e' soltanto la whitelist dei tipi
(`vendite.trgfn_tipi_indirizzi_only_allowed`).

**Il gate d'emissione guarda solo che l'indirizzo ci sia.** `script.fn_check_ddt_emittibile`
(punto 4) confronta i tipi presenti con quelli obbligatori (`script.fn_indirizzi_obbligatori_mancanti`).
Non controlla l'origine.

## 3. Perche' e' un difetto, sul modello

* **Il DDT si emette con la Consegna del cliente di prima.** Si crea la bozza col cliente A e lo
  slot CON viene preso dal ruolo di A. Poi il cliente diventa B, e la bolla si emette, si stampa e si
  consegna all'indirizzo di A. Lo stesso vale per una bolla senza cliente di cui cambia il
  destinatario.
* **Preventivo e offerta hanno lo stesso buco.** Il cliente, cioe' la coppia BA/istanza, si cambia
  in bozza: `preventivi_service.aggiorna_preventivo` e `offerte_service.aggiorna_offerta`. Nessuno dei
  due tocca gli indirizzi. Sul preventivo cambia anche l'**istanza** dello stesso cliente: un
  indirizzo di un'istanza (layer RUOLO con `anagrafiche.indirizzi.istanza_utility_id` valorizzato)
  resta attaccato a una fornitura che il documento non ha piu'.
* **L'ordine no**: BA e ruolo sono bloccati sempre (`E_ORD_CLIENTE_IMMUTABILE`).
* **La regola sta in un posto che non vede tutto.** Chi scrive senza passare dal service salta il
  controllo, e l'emissione non lo recupera.

⚠️ Nessuna di queste ragioni dipende da quante righe ci sono oggi in quello stato.

## 4. Decisioni di Tid (2026-10-10)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | La regola «un indirizzo d'anagrafica e' del cliente del documento» vale su tutti i documenti in cui il cliente si cambia in bozza? | ✅ **Si'**: DDT (BA o destinatario), preventivo, offerta. Gli una-tantum restano |
| **D-2** | Lo slot di default dopo un cambio di cliente lo riempie il backend o il DB? | ✅ **Il DB.** Ne segue che l'auto-assegnazione passa intera nel DB, anche alla creazione: due sedi per la stessa regola sono la copia che la regola del 2 vieta |
| **D-3** | L'emissione controlla l'origine? | ✅ **Si'**: e' un motivo del gate d'emissione, cosi' vale anche per chi scrive saltando il backend |

## 5. Forma proposta (la sceglie il team DB)

1. **Un BB di risoluzione dello slot di default.** Prende documento e cliente (ruolo, istanza) e
   scrive lo slot se e' vuoto, con `script.fn_resolve_indirizzo_documento`. ⚠️ La priorita' fra i tipi
   (CON → FATT → primo ammesso) oggi e' scritta in Python come «regola di UX». Nel DB diventa regola
   di dominio: va dichiarata in `config.tipi_indirizzi_allowed` (per esempio un ordine di default per
   ambito), non cablata per codice.
2. **Alla creazione**, il BB lo chiamano i verbi e/o i trigger. ⚠️ La cascata dal documento sorgente
   deve restare prioritaria: oggi il backend arriva **dopo** il verbo e trova lo slot gia' pieno.
   Bisogna scegliere il «quando» (trigger AFTER INSERT sulla testata, o chiamata esplicita dai verbi
   dopo la cascata) in modo da non scrivere uno slot che la cascata scriverebbe subito dopo.
3. **Al cambio di cliente in bozza** (un `UPDATE` che cambia `billing_account_id`/`istanza_utility_id`
   sul preventivo e sull'offerta, `billing_account_id` o `destinatario_soggetto_ruolo_id` sul DDT):
   * si tolgono le righe d'anagrafica non piu' valide per il cliente nuovo, cioe' con
     `origine_soggetto_ruolo_id` diverso dal ruolo nuovo, oppure del layer RUOLO legate a un'istanza
     diversa da quella nuova. Gli una-tantum restano;
   * si richiama il BB del punto 1 sullo slot di default rimasto vuoto.
4. **Il guard sulla scrittura di `*_indirizzi`**, che sostituisce quello Python: una riga d'anagrafica
   deve avere il ruolo del documento, e se viene da un'istanza, l'istanza del documento. Un
   documento senza ruolo risolvibile lascia passare, come oggi. Un BB parametrico per le sei
   tabelle, come la whitelist dei tipi.
5. **Il motivo d'emissione nuovo**, sul DDT in `script.fn_check_ddt_emittibile` (sede unica di guard
   e capability). Sui gate d'emissione di preventivo e offerta si fa lo stesso censimento.
6. **Codici**: uno per «indirizzo non del cliente del documento» (guard di scrittura e motivo
   d'emissione), registrato con policy e frase di ripiego. Il campo e' `tipo_indirizzo_id` o lo slot.

### 5.1 Da censire nel giro

* Contratto e fattura: il loro cliente si cambia in bozza **a DB**? Lato BE il BA del contratto e'
  vietato in update (`contratti_service._FORBIDDEN_TESTATA_UPDATE`). Se il DB non lo blocca, la regola
  del §5.3 li riguarda anche loro.
* Il reso non ha `*_indirizzi`: la riconsegna li eredita per cascata (`fn_genera_ddt_riconsegna`). Va
  confermato che non serve altro.
* I verbi con cascata degli indirizzi (`fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`, push
  preventivo → ordine, offerta → contratto): con il punto 2 non devono trovarsi uno slot gia' scritto
  dal default.
* La testata del pgTAP `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` (riga 7) punta ancora a
  `work-in-progress/brief-db-esecutivi-ba-coppia.md`. Il brief e' in `work-done/` dal 2026-10-10.

### 5.2 pgTAP (fixture fabbricati)

* DDT in bozza col cliente A e la CON di A; il cliente diventa B: la CON di A non c'e' piu', c'e'
  quella di B (se B ne ha una); un una-tantum resta.
* Preventivo: stesso cliente, istanza cambiata, con un indirizzo legato all'istanza vecchia.
* Scrittura diretta su `ddt_indirizzi` di un indirizzo d'un altro ruolo: rifiutata col codice.
* Emissione di una bolla con una riga d'anagrafica d'un altro ruolo (scritta prima del guard, o a
  guard spento): motivo nuovo.
* Creazione da ordine: lo slot lo scrive la cascata, non il default.

## 6. Ricaduta BE/FE (dopo la consegna DB)

* Ritirare `auto_assegna_indirizzo_default` e `auto_assegna_indirizzo_default_contratto` con i loro
  chiamanti (DDT, ordine, preventivo, offerta, contratto), e il guard d'origine di
  `upsert_indirizzo_documento`: decide il DB, il BE mappa il codice.
* Codice nuovo: policy rigenerata e frase di ripiego. Reason nuova per l'azione «Emetti» del DDT
  nei locales.
* FE: dopo il salvataggio del cliente in bozza il pannello indirizzi si ricarica, perche' il DB
  potrebbe averlo cambiato.
