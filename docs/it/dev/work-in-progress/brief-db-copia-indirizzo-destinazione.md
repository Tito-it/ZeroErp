# Brief DB — La copia di un indirizzo va dove lavora l'operatore

## ⏭️ Chi riparte — aggiornato al 2026-11-19

**Riparte: il team DB col giro 1 (§4).** D-1 … D-3 decise da Tid il 2026-11-19, come proposte (§5). Il FE di oggi
dice già, nella dialog, da dove e verso dove va la copia (§2): quando il DB accetta la destinazione, cambia solo la
riga «Verso».

| # | Chi | Che cosa | Dove | Dopo |
| --- | --- | --- | --- | --- |
| 1 | Tid | D-1 … D-3 ✅ 2026-11-19 | §5 | — |
| 2 | team DB | giro 1: i due verbi con la destinazione (dal ruolo, dal soggetto), le check, il picker sulla destinazione, ritiro della firma vecchia, pgTAP e doc | §4 | 1 |
| 3 | Tid | applicazione su dbdev, pgTAP verdi, doc auto-generata, commit | — | 2 |
| 4 | BE/FE | R-1 … R-3 | §6 | 3 |
| 5 | chi chiude | archiviazione in `work-done/` | — | tutti |

## 1. Il caso (prova a video di Tid, 2026-11-18)

Il cliente ha un servizio (un'istanza utility). L'operatore apre gli indirizzi **del servizio**, sceglie la
Spedizione **del ruolo** e la copia come Fatturazione: vuole la fatturazione **del servizio** su cui sta lavorando.

Il verbo invece la scrive sul **ruolo**: `anagrafiche.fn_copia_indirizzo_ruolo(ruolo, indirizzo, tipi[])` copia
«nello stesso ruolo e nella stessa istanza della sorgente» (COMMENT del verbo). È la regola decisa in
[brief-db-copia-indirizzo-soggetto](../work-done/brief-db-copia-indirizzo-soggetto.md) (§4.6 punto 3, D-1): la copia
resta nel layer e nell'istanza della sorgente, e la copia **fra layer** è un gesto diverso, lasciato fuori.

Il caso di Tid è un gesto con una **destinazione** diversa dalla sorgente, e il modello di oggi non sa dirlo: copiando
dal servizio una riga del ruolo, la copia non arriva dove l'operatore la cerca, e nessun errore lo segnala.

## 2. Che cosa c'è già (FE, 2026-11-18, non committato)

`CopiaIndirizzoDialog` mostra due righe: **Da** (tipo, indirizzo, titolare della sorgente: il soggetto, il ruolo,
il servizio) e **Verso** (oggi «il ruolo, dove sta l'indirizzo di partenza», cioè ciò che il verbo fa). È una
descrizione di ciò che succede: non cambia dove va la copia.

## 3. Che cosa si chiede

La copia scrive sulla **chiave di destinazione** che il chiamante indica: il ruolo (istanza `NULL`) o una sua
istanza. La sorgente può stare in un'altra chiave dello stesso ruolo, e nel layer del soggetto (D-2).

## 4. La proposta per il giro 1 (team DB)

1. **Il verbo con la destinazione.** `fn_copia_indirizzo_ruolo(p_soggetto_ruolo_id, p_indirizzo_id, p_tipi[],
   p_istanza_utility_id_destinazione)`, dove la destinazione è il ruolo stesso (istanza `NULL`) o una sua istanza.
   Il parametro è **obbligatorio** e la firma di oggi a tre argomenti **si ritira** (D-3): niente `DEFAULT NULL`,
   che accanto alla firma vecchia darebbe due overload ambigui su tre argomenti. Per dire «il ruolo» si passa
   `NULL` esplicito.
2. **L'istanza di destinazione dev'essere del ruolo**: altrimenti un codice `NON_TROVATO` (proposta
   `E_INDIRIZZO_COPIA_DESTINAZIONE_NON_TROVATA`). La sorgente resta «del ruolo» (`E_INDIRIZZO_RUOLO_NON_TROVATO`),
   in qualunque sua chiave.
3. **La check e il picker giudicano la destinazione**, non la sorgente: «tipo già presente» si guarda sulla chiave
   di destinazione. Il picker c'è già (`fn_tipi_indirizzo_proponibili_ruolo(ruolo, istanza)`), con l'istanza di
   destinazione. La check di riga (`fn_check_copia_indirizzo_ruolo`, «Copia come…» spento col motivo) va rivista:
   oggi dice se la copia è possibile sulla chiave della sorgente.
4. **La scrittura resta della singolare** `fn_crea_indirizzo_ruolo`, con l'istanza di destinazione: tutti i guard
   della tabella valgono, tutto o niente come oggi.
5. **Il gemello dal soggetto al ruolo** (D-2): la sorgente è una riga di `indirizzi_soggetti` del soggetto del
   ruolo, la destinazione una chiave del ruolo (il ruolo o una sua istanza). Stessa regola dei punti 2-4: la
   sorgente dev'essere del soggetto del ruolo, la check e il picker giudicano la destinazione, la scrittura è
   `fn_crea_indirizzo_ruolo`. Il nome lo sceglie il team DB, nella famiglia dei verbi di copia.

pgTAP: la copia da una riga del ruolo verso una sua istanza; da un'istanza al ruolo; verso un'istanza di un altro
ruolo, rifiutata; «tipo già presente» sulla destinazione, non sulla sorgente; il tipo assente sulla sorgente e
presente sulla destinazione, e il contrario. Per il gemello: dal soggetto al ruolo e a una sua istanza; una riga
di un altro soggetto, rifiutata. La firma vecchia a tre argomenti non esiste più.

## 5. Decisioni di Tid — ✅ decise il 2026-11-19, come proposte

* **D-1 — La destinazione è la chiave del drawer.** ✅ Sì. Il FE manda sempre la chiave su cui l'operatore
  lavora (il ruolo o il servizio aperto). Una copia sulla chiave della sorgente resta possibile aprendo quella chiave.
* **D-2 — Anche dal soggetto al ruolo.** Nella cascata, in contesto ruolo, la lista mostra anche gli indirizzi del
  soggetto, e oggi la loro copia resta sul soggetto. ✅ Sì, nello stesso giro, perché è lo stesso gesto (la
  destinazione è la chiave del drawer) e un'asimmetria si chiude subito.
* **D-3 — La firma.** ✅ La firma vecchia si ritira e la destinazione diventa obbligatoria. Il progetto non è
  in produzione e il chiamante è uno solo, il BE.

## 6. Richieste a BE/FE (dopo il giro 1)

* **R-1 (BE)**: `POST /ruoli/{id}/indirizzi/{id}/copia/` prende `istanza_utility_id` di destinazione (assente =
  il ruolo), e lo passa al verbo; il gemello per la sorgente del soggetto (D-2), con la stessa destinazione.
* **R-2 (FE)**: `IndirizziSoggettoDrawer` manda la chiave del drawer (`istanzaUtilityId`), legge il picker sulla
  destinazione, e la riga «Verso» della dialog dice la chiave del drawer (`copiaDestinazione`, oggi «come la
  sorgente»).
* **R-3 (BE)**: policy e ripiego del codice nuovo (`error_policies_generated.py`, `error_messages_fallback.py`).
