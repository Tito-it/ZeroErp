# Brief DB — Gli stati dei documenti: ogni significato dal vocabolario

## ⏭️ Chi riparte — aggiornato al 2026-11-08

**Riparte: Tid**, con la decisione S-1 (che cosa vuol dire `terminale`) e il via al censimento; poi il **team DB**.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ DB | i difetti, trovati riscrivendo le pagine `config/manual/stati_doc_*` (giro DOC.4 di `brief-db-sorgente-documento-e-riga`), verificati sul DB | §2 | — |
| 2 | ✅ Tid | il brief si apre: i difetti degli stati vanno qui, non nel cantiere della provenienza (2026-11-08) | — | — |
| 3 | Tid | **S-1**: il significato di `terminale` | §3 | — |
| 4 | DB | censimento: per ogni difetto i lettori e gli scrittori, la proposta di correzione | §4 | 3 |
| 5 | Tid | via allo sviluppo | — | 4 |
| 6 | DB | sviluppo, prova in transazione, pgTAP | — | 5 |
| 7 | BE/FE | le ricadute che il censimento trova (oggi nessuna nota) | — | 6 |

**Decisioni aperte di Tid:** S-1. **Lavoro da committare:** questo brief.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-08. **A chi:** Tid, poi il team DB.
> **Origine:** il giro DOC.4 di `brief-db-sorgente-documento-e-riga` (§7.3 «Trovato da DOC.4»): riscrivendo le dieci
> pagine dei vocabolari degli stati sono emersi difetti fuori dal tema della provenienza. Tid, 2026-11-08: si apre un
> brief per gli stati.
> **Brief vicini verificati:** `work-done/brief-modello-documento-vendita` (chiuso il 2026-10-31: il significato di uno
> stato lo dice il vocabolario, non un letterale; questo brief ne chiude i residui, non ne revoca niente);
> `analisi-pratiche-valutazione-stato` e `brief-design-proiezione-stato-dominio` (leggono `fase`/`esito`/`terminale` per
> la proiezione nelle pratiche: sono i consumatori di S-1, non lo decidono); `gestione-pratiche-come-procedere` §3 (le
> segnalazioni di `pratiche`, separate per decisione di Tid). Nessun brief aperto sui vocabolari degli stati.
> **Ambito:** i vocabolari `config.stati_doc_*`, le loro matrici, i guard e i verbi che li leggono. ⚠️ Tocca tutti i
> documenti di vendita: è ammesso dal fermo allentato (PROJECT_CONTEXT, «poggia su un pezzo comune già fatto»: il
> vocabolario) e Tid ne ha dato l'ok (2026-11-08).

---

## 1. Il buco in una frase

La guida del modello del documento dice che il significato di uno stato (iniziale, emissione, accettazione, terminale,
annullo) lo dice il vocabolario; in alcuni punti il codice lo dice ancora con un letterale, o il vocabolario dichiara un
significato che la matrice smentisce.

## 2. I difetti (verificati sul DB, 2026-11-08; non provati in transazione)

| # | Difetto | Dove |
| --- | --- | --- |
| ② | Il lotto di fatturazione non nasce dal vocabolario: `vendite.fn_create_fatturazione_lotto` sceglie lo stato col letterale `'DRAFT'`, e `trgfn_doc_stato_iniziale` non è montato su `vendite.fatturazione_lotti` (mentre `fn_riporta_lotto_a_draft` legge già `iniziale`) | `vendite.fatturazione_lotti` |
| ③ | Il guard di transizione dell'offerta confronta i codici (`'BOZZA'`, `'EMESSA'`, `'ACCETTATA'`, `'ANNULLATA'`) nelle condizioni e nelle date del passaggio, invece di `emissione`, `accettazione`, `is_abortito` | `vendite.trgfn_offerte_commerciali_guard_transizione` |
| ④ | `terminale` è dichiarato su stati che hanno passaggi attivi in uscita (automatici): `SUPERATA→EMESSA` (offerte), `EVASO→ACCETTATO` (preventivi), `EVASO→PARZIALMENTE_EVASO` ed `EVASO→CONFERMATO` (ordini). Il COMMENT dice «non evolverà più», e `pratiche.fn_stato_sorgente` lo legge | vocabolari e matrici; S-1 |
| ⑤ | Quattro stati d'ordine attivi che nessun passaggio raggiunge: `ALLOCATO`, `SPEDITO`, `CONSEGNATO`, `FATTURATO` | `config.stati_doc_ordini` |
| ⑥ | Il controllo di `applica_fattura` in `trgfn_fatture_guard_stato` sta nel solo ramo «prima assegnazione» (UPDATE con stato precedente NULL), che non scatta: lo stato è NOT NULL e lo mette il trigger alla nascita | `vendite.fatture` |
| ⑦ | Bolla e reso non dichiarano `esito` e `terminale`: li ricavano `vw_stato_sorgente_ddt` e `vw_stato_sorgente_reso` con una regola scritta nella vista | `config.stati_doc_ddt`, `config.stati_doc_reso` |
| ⑧ | (minore) `config.stati_doc_listino_versioni` non ha `fase` (e quindi il CHECK che lega `terminale` a `fase`), e l'indice di `iniziale` si chiama `ux_…` invece di `uq_…` | `config.stati_doc_listino_versioni` |

**COMMENT stantii** (ognuno è un changeSet): `config.stati_doc_reso` e la sua `meta` (`fase` in `meta.fase`: è una
colonna); `config.stati_doc_offerte_transizioni` («5 transizioni»: sono 7); `config.stati_doc_offerte` (manca
`accettazione`) e le colonne `ordine` (manca 60) e `is_superato` (lo scrive `vendite.fn_offerta_proietta_stato_revisione`);
`codice` di `stati_doc_contratti` (`SOSPESO`, che non c'è), `stati_doc_ddt` e `stati_doc_ordini` (CONFERMATA/ALLOCATA);
`stati_doc_fiscale.fase`; `vendite.contratti.is_abortito_snapshot` (trigger, colonna e vincolo che non ci sono più: oggi
`partecipa_overlap_snapshot`, `ex_contratti_no_overlap`); le colonne di significato degli stati («Emetti» produce numero e
PDF: per offerta, contratto e ordine il numero è assegnato alla nascita).

Le pagine `manual/` descrivono già lo stato di oggi, difetti compresi (DOC.4, 2026-11-08).

## 3. Da decidere (Tid)

* **S-1 — che cosa vuol dire `terminale`.** Due letture, e decidono ④:
  * **A** «nessun passaggio **a mano** in uscita»: gli automatismi (la revisione che riapre, l'evasione che si
    riapre) restano ammessi; si corregge il COMMENT e si dichiara nella matrice quali passaggi sono di sistema
    (`meta.manuale` c'è già). Chi legge `terminale` per dire «finito per sempre» va censito.
  * **B** «nessun passaggio **in assoluto**»: gli stati con uscite perdono `terminale`, e chi oggi lo legge
    (la proiezione nelle pratiche) va rivisto perché un'offerta superata o un ordine evaso non sono più «chiusi».
  * Proposta DB: **A**, perché `meta.manuale` distingue già i passaggi di sistema e la proiezione nelle pratiche vuole
    sapere se l'operatore ha ancora qualcosa da fare. Da confermare col censimento dei lettori.

## 4. Il censimento (dopo S-1)

Per ogni difetto: chi lo scrive, chi lo legge (DB, BE, FE), la correzione, il pgTAP che la presidia costruendo il caso
(non confrontando la popolazione). Per ⑤ la domanda è di modello: stati previsti per un ciclo che verrà, o da ritirare.
