## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_doc_snapshot_da_stato()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)

---

### 🎯 Scopo Principale
(2026-10-11, brief-db-annullo-documento-con-legami, D-6)

Copia sulla riga di un documento **le bandiere booleane del suo stato**
(`is_abortito`, `is_bozza`…), perché indici e colonne generate non possono
leggere un'altra tabella.

| Tabella | Snapshot | Dal vocabolario | A che cosa serve |
| --- | --- | --- | --- |
| `vendite.contratti` | `is_abortito_snapshot`, `is_draft_snapshot` | `config.stati_doc_contratti.is_abortito`, `is_bozza` | la colonna `GENERATED` `partecipa_overlap_snapshot` (anti-sovrapposizione) e `uq_contratti_offerta_id` |
| `vendite.ordini` | `is_abortito_snapshot` | `config.stati_doc_ordini.is_abortito` | `uq_ordini_v_documento_origine_offerta` |

⭐ È un building block per la **regola del 2**: la prima copia era
`trgfn_contratti_sync_is_abortito_snapshot` (contratto); la seconda serviva
all'ordine, per l'indice «un'offerta genera al più un ordine **vivo**». Alla
seconda si è estratto, e la copia del contratto si è ritirata.

---

### Il contratto: perché quelle colonne contano

Da `is_abortito_snapshot` e `is_draft_snapshot` PostgreSQL calcola la colonna
**`GENERATED`** `partecipa_overlap_snapshot` (`NOT abortito AND NOT draft`), e su
quella poggia l'indice di esclusione che impedisce due contratti sovrapposti:

```sql
ex_contratti_no_overlap
  USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, validita)
  WHERE partecipa_overlap_snapshot
```

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

Esempio, contratto:
`('stato_doc_contratto_id', 'config.stati_doc_contratti', 'is_abortito_snapshot', 'is_abortito', 'is_draft_snapshot', 'is_bozza')`.

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

{% include-markdown "signature-core.md" %}
