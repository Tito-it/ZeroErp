## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_set_categoria_cliente_snapshot()`

> **Ultimo aggiornamento**: 14 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>
Approfondimento funzioni:
> • [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza) — il lock che congela la categoria fuori bozza

---
### 🎯 Scopo Principale

Alla **nascita** del contratto riempie `categoria_cliente_id_snapshot`, copiandola dal billing
account, se chi crea non l'ha passata. Un valore passato esplicitamente non viene toccato.

È lo schema classico dello snapshot: il valore si prende dall'anagrafica una volta sola, poi
diventa un fatto del contratto. Se il cliente viene riclassificato l'anno dopo, il contratto
già attivo continua a valere sulle condizioni con cui è stato firmato.

---

### Aggancio

Trigger `trg_contratti_a10_set_categoria_cliente_snapshot_ins` — fase `_a10_`, `BEFORE INSERT` su
`vendite.contratti`.

---

### Chi congela la categoria

Non questa funzione. In bozza la categoria si cambia: la riclassificazione del billing account
mentre il contratto si prepara è legittima. Fuori bozza (`ATTIVO`, `CESSATO`, `ANNULLATO`) la
blocca il **lock della testata** (`trg_contratti_a05_lock_fuori_bozza_upd`), che la elenca fra le
colonne delle condizioni, senza eccezioni di stato: il rifiuto è `E_DOC_CONDIZIONI_FUORI_BOZZA`.
La bozza è lo stato iniziale del vocabolario.

Fino al 14 novembre 2026 lo diceva anche un ramo `UPDATE` di questa funzione, con
`E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE`: una seconda copia della regola, che non parlava mai
perché il lock arriva prima (`a05` prima di `a10`). È stato ritirato, e il codice resta a catalogo
con `obsoleto_dal`.

⚠️ Il lock guarda la colonna del **contratto**, non quella del billing account: dopo una
riclassificazione BA e contratto dicono cose diverse, ed è voluto. Per il contratto vale la sua.

---

### ⚠️ Se il billing account non ha categoria, lo snapshot nasce vuoto

Il valore viene copiato così com'è: se il BA ha `categoria_cliente_id` nulla, lo snapshot resta
`NULL`, senza errori. Fuori bozza il lock impedisce di correggerlo, perché anche passare da `NULL` a
un valore è un cambio: la finestra per rimediare è la bozza.

---

### Test

* `db/pgtap/vendite/test-contratto-stati-dal-vocabolario-v1.sql` — la categoria si cambia in bozza e
  non fuori (parla il lock), anche con la marca `iniziale` spostata; il trigger è solo
  `BEFORE INSERT`; alla nascita la categoria viene dal billing account.

---

{% include-markdown "signature-core.md" %}
