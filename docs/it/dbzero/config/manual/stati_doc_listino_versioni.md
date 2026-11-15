## 📘 Documentazione Concettuale – Tabella `config.stati_doc_listino_versioni`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — la versione di listino, che porta lo stato (`stato_doc_listino_versione_id`)
> * [config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni) — i passaggi ammessi fra questi stati
>
> Approfondimento funzioni:
>
> * [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) — legge lo stato `iniziale`
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — fa nascere la versione nello stato iniziale
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — dal `codice_interno` all'id dello stato
>
> Guide:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — vocabolario, matrice e nascita

---

### 🎯 Scopo Principale

`config.stati_doc_listino_versioni` è il **vocabolario degli stati di una versione di listino**:
in preparazione, in uso, chiusa. Dice in quale stato una versione nasce e da quale non esce più; i
passaggi stanno nella matrice
[`config.transizioni_stati_listino_versioni`](/dbzero/config/tabelle/transizioni_stati_listino_versioni).

---

### Gli stati

| `codice_interno` | Che cosa vuol dire | Marcato da |
| --- | --- | --- |
| `BOZZA` | in preparazione: righe e date si cambiano, la versione si elimina | `iniziale` |
| `ATTIVA` | i prezzi sono in uso; si cambia solo la fine della validità | — |
| `CHIUSA` | la finestra di validità è passata: è la storia dei prezzi di un periodo | `terminale` |

`codice_interno` è la chiave stabile: non si modifica (`E_CODICE_NON_MODIFICABILE`), e lo leggono
[`script.fn_doc_stato_id`](/dbzero/script/funzioni/fn_doc_stato_id) e i lettori che confrontano un
codice. Uno stato già usato da una versione o dalla matrice non si disattiva.

---

### Le colonne che hanno un significato

* **`iniziale`** — lo stato in cui una versione nasce. Al più uno (indice unico parziale), ed è
  attivo (CHECK). Il trigger
  [`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) su
  `vendite.listini_versioni` mette questo stato quando chi crea non ne dice uno, e rifiuta ogni
  altro con `E_DOC_STATO_INIZIALE_NON_VALIDO`. Lo legge anche il controllo dei listini in scadenza
  senza una versione successiva.

  È anche **la bozza**: chi chiede «la versione è in bozza?» legge questa colonna, mai il codice
  `BOZZA`. In bozza la versione si cambia tutta e si elimina
  ([`vendite.trgfn_listini_versioni_guard_per_stato`](/dbzero/vendite/manual/trgfn_listini_versioni_guard_per_stato),
  [`script.fn_check_versione_listino_eliminabile`](/dbzero/script/manual/fn_check_versione_listino_eliminabile)),
  le sue righe, i componenti e i kit si scrivono liberamente
  ([`vendite.trgfn_listini_righe_guard_stato`](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato),
  [`vendite.trgfn_listini_righe_comp_guard_immutabilita_v5`](/dbzero/vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5),
  `vendite.trgfn_listini_kit_guard`, con la regola in `script.fn_check_listino_riga_scrivibile`),
  e un prezzo non ne proviene: non è in vigore
  ([`vendite.fn_listino_versione_in_vigore`](/dbzero/vendite/manual/fn_listino_versione_in_vigore)),
  il resolver non la usa come versione preferita
  ([`vendite.fn_resolve_prezzo_listino_v2_esito`](/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2_esito)),
  una riga di documento non la cita (`vendite.fn_check_listino_provenienza_emittente`), non dà
  storia al listino ([`vendite.fn_listino_ha_storia`](/dbzero/vendite/manual/fn_listino_ha_storia)),
  e un prezzo bundle che comincia oltre la fine del legame vi si cancella
  ([`vendite.fn_prezzi_legame_oltre_la_fine`](/dbzero/vendite/manual/fn_prezzi_legame_oltre_la_fine)).
  Lo presidia `vendite/test-listino-stati-dal-vocabolario-v1`, con la marca spostata su ATTIVA.
* **`terminale`** — nessun passaggio **a mano** esce da questo stato (lo fa rispettare
  [`script.trgfn_doc_terminale_senza_uscita_manuale`](/dbzero/script/manual/fn_doc_terminali_con_uscita_manuale)).
  Non vale il contrario: `ATTIVA` non ha uscite a mano, la chiude il processo, e non è terminale.

`ATTIVA` e `CHIUSA` non hanno una colonna, e i lettori li nominano col codice: sono le
**destinazioni** dei due processi della versione, l'attivazione
(`vendite.fn_attiva_versione_listino`) e la chiusura (`vendite.fn_chiudi_versioni_listino_scadute`),
e chi li confronta vuole proprio quello stato, come la riga della matrice lo nomina.

Rispetto ai vocabolari dei documenti di vendita, questo è ridotto: non ha `emissione` (una versione
si **attiva**, col suo passaggio `BOZZA → ATTIVA`), non ha un annullo (`is_abortito`) e non ha la
proiezione per il motore pratiche (`fase`, `esito`). Nemmeno `codice`: basta `codice_interno`.

---

### ⚠️ Gli id del seed stanno anche in due vincoli

Gli id 1 (`BOZZA`), 2 (`ATTIVA`) e 3 (`CHIUSA`) sono scritti anche nel predicato di
`ex_listini_versioni_no_overlap` e in `chk_listini_versioni_chiusa_con_fine`, su
`vendite.listini_versioni`, perché un vincolo non legge un'altra tabella. Non si rinumerano; se si
cambiano, si cambiano insieme ai vincoli. Il pgTAP
`vendite/test-listino-versione-al-modello-v1` li confronta coi codici.

Il contenuto della tabella sta nel CSV `80_data/sql/config/stati_doc_listino_versioni.csv`.

---

### Codici errore

* `E_DOC_STATO_INIZIALE_NON_VALIDO` — una versione nuova chiesta in uno stato diverso dall'iniziale.
* `E_CODICE_NON_MODIFICABILE` — una modifica di `codice_interno`.

---

### Test

* `db/pgtap/vendite/test-listino-versione-al-modello-v1.sql` — la versione di listino sul modello del documento, e gli id dei vincoli confrontati coi codici.
* `db/pgtap/vendite/test-listino-stati-dal-vocabolario-v1.sql` — la bozza dalla colonna `iniziale`, nei lettori di significato, con la marca spostata.
* `db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql` — uno stato iniziale per vocabolario, attivo, e la nascita della versione.

---

### Note di migrazione

* 2026-10-28 — nasce il vocabolario (brief `brief-modello-documento-vendita` §16, L-1): prima lo
  stato della versione di listino non aveva una tabella sua.

---

{% include-markdown "signature-core.md" %}
