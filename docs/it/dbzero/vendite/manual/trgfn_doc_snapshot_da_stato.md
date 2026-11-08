## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_doc_snapshot_da_stato()`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — gli snapshot di abortito e bozza
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — lo snapshot di abortito
> * [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) — il vocabolario degli stati del contratto
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — il vocabolario degli stati dell'ordine

---

### 🎯 Scopo Principale

Copia sulla riga di un documento **le bandiere booleane del suo stato**
(`is_abortito`, `is_bozza`…), perché indici e colonne generate non possono
leggere un'altra tabella.

| Tabella | Snapshot | Dal vocabolario | A che cosa serve |
| --- | --- | --- | --- |
| `vendite.contratti` | `is_abortito_snapshot`, `is_draft_snapshot` | `config.stati_doc_contratti.is_abortito`, `is_bozza` | la colonna `GENERATED` `partecipa_overlap_snapshot` (anti-sovrapposizione) e `uq_contratti_sorgente_offerta` |
| `vendite.ordini` | `is_abortito_snapshot` | `config.stati_doc_ordini.is_abortito` | `uq_ordini_v_sorgente_offerta` |

⭐ È un building block per la **regola del 2**: la prima copia era
`trgfn_contratti_sync_is_abortito_snapshot` (contratto); la seconda serviva
all'ordine, per l'indice «un'offerta genera al più un ordine **vivo**». Alla
seconda si è estratto, e la copia del contratto si è ritirata.

Sui due documenti lo snapshot di abortito regge la stessa regola: gli indici unici
sulla provenienza da un'offerta (`uq_contratti_sorgente_offerta`,
`uq_ordini_v_sorgente_offerta`) valgono sui soli documenti **vivi**, così un documento
annullato conserva la provenienza senza consumare l'offerta.

---

### Il contratto: perché quelle colonne contano

Da `is_abortito_snapshot` e `is_draft_snapshot` PostgreSQL calcola la colonna
**`GENERATED`** `partecipa_overlap_snapshot` (`NOT abortito AND NOT draft`), e su
quella poggia l'indice di esclusione `ex_contratti_no_overlap`, che impedisce due
contratti sovrapposti sulla stessa combinazione di billing account, istanza utility,
utility e ambito, per i soli contratti che partecipano.

Un contratto abortito o ancora in bozza **non deve** occupare il perimetro: se lo
facesse, nessuno potrebbe più stipularne uno valido sullo stesso billing account.

---

### ⚠️ `z90` ma `BEFORE`: la fase è la parte che conta

* deve essere **`BEFORE`**, perché una colonna `GENERATED` (e un indice) si
  calcola sul `NEW` finale, dopo tutti i `BEFORE`. Un `AFTER` arriverebbe a
  calcolo fatto;
* deve essere **`z90`**, l'ultimo dei `BEFORE`, perché un trigger che cambiasse
  lo stato dopo di lui lascerebbe gli snapshot disallineati.

⚠️ Chi rinomina questi trigger, o ne aggiunge uno alfabeticamente successivo che
tocca lo stato, rompe anti-sovrapposizione e unicità **senza nessun errore**.

---

### Senza `OF`: lo snapshot non si falsifica

Montato `BEFORE INSERT OR UPDATE`, **senza** `UPDATE OF stato`: ricalcola gli
snapshot a ogni scrittura. Un `UPDATE` che scrive `is_abortito_snapshot` a mano
viene riportato al valore dello stato. La copia del contratto era `UPDATE OF
stato_doc_contratto_id` e lasciava quella porta aperta.

---

### Montaggio

| Argomento | Cosa |
| --- | --- |
| `TG_ARGV[0]` | colonna di stato della riga |
| `TG_ARGV[1]` | vocabolario degli stati (`schema.tabella`) |
| poi, a coppie | colonna snapshot, colonna booleana del vocabolario |

Sul contratto, per esempio, la colonna di stato è `stato_doc_contratto_id`, il
vocabolario `config.stati_doc_contratti`, e le coppie sono `is_abortito_snapshot` con
`is_abortito` e `is_draft_snapshot` con `is_bozza`.

---

### ⚠️ Stato `NULL` o assente: `false`

Ogni bandiera cade a `false` se lo stato non c'è: «né abortito né bozza». Sul
contratto significa `partecipa_overlap_snapshot = true`, il caso più
restrittivo, non il silenzio. Nella pratica la FK verso il vocabolario non
ammette uno stato inesistente.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_VENDITE_CHIAMATA_NON_VALIDA` | montaggio sbagliato (coppia spaiata, colonna che la riga non ha) |

---

### Note di migrazione

* 2026-10-11 — estratto come building block dalla copia del contratto
  (`trgfn_contratti_sync_is_abortito_snapshot`) quando serviva anche all'ordine
  (brief-db-annullo-documento-con-legami, D-6).
* 2026-11-06 — gli indici che lo snapshot serve diventano `uq_contratti_sorgente_offerta` e
  `uq_ordini_v_sorgente_offerta`, sulla provenienza `sorgente_*`, al posto di
  `uq_contratti_offerta_id` e `uq_ordini_v_documento_origine_offerta`
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
