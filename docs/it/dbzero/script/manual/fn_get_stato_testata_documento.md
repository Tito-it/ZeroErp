## 📘 Documentazione Concettuale – Funzione `script.fn_get_stato_testata_documento`

> 👀 **Vedi anche**
>
> [vendite.trgfn_dlt_block_ordrig_ddtrig](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig) — il motivo per cui esiste (l'etichetta per i legami a valle)
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il building block delle righe, dal 2026-09-22 il consumatore principale (tre documenti)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — terzo tipo, `CONTRATTO` (rev 2026-09-22)
> [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — il guard gemello, sulla testata
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)

---

### 🎯 Scopo Principale

**Rispondere a una domanda sola: la testata di questo documento esiste ancora, e
in che stato è?**

Serve ai guard di documento — quello di cancellazione delle righe, e dal 22
settembre il building block «le righe si toccano solo in bozza» — che su
quella risposta decidono. Non scrive, non solleva sul caso normale, e legge due
colonne.

```sql
-- il caso normale
SELECT * FROM script.fn_get_stato_testata_documento('DDT', 4711);
--  stato  |     etichetta
-- --------+--------------------
--  DRAFT  | DDT 2026/00123

-- e il caso che conta: nessuna riga, non un NULL
SELECT count(*) FROM script.fn_get_stato_testata_documento('DDT', 999999999);
--  0
```

---

### Il contratto

| Esito | Significato |
| --- | --- |
| **zero righe** | la testata **non esiste** |
| **una riga** | `stato` = il `codice_interno` dello stato · `etichetta` = la frase che l'operatore legge |

⚠️ **L'assenza di riga è un segnale, non un'ambiguità.** Lo stato è `NOT NULL` su
entrambe le testate e la chiave esterna verso `config.stati_doc_*` garantisce la
riga di stato: se la testata c'è, `stato` non è mai vuoto. Il chiamante può
quindi leggere «zero righe» come **«la testata non c'è più»** senza dover
distinguere un `NULL` da un vuoto.

Tipi di documento ammessi: `DDT`, `ORDINE` e — dal 2026-09-22, per le righe di
contratto — `CONTRATTO` (`vendite.contratti` → `config.stati_doc_contratti`,
etichetta «Contratto <numero>»). Qualunque altro valore non è un dato sbagliato,
è un **chiamante rotto**: `E_DOC_TIPO_NON_GESTITO`, classe `TECNICO`.

---

### ⛔ Perché `SECURITY DEFINER`: «non c'è» e «non lo vedo» non devono coincidere

Quando è nata (2026-08-26) le testate avevano la RLS e le righe no: un chiamante
fuori perimetro raggiungeva la **riga** senza vedere la sua **testata**. Dal
22-09 anche le righe hanno le policy (`ddt_righe`, `ordini_righe`,
`contratti_righe`, letto dal catalogo), ma il perno non cambia: un guard di riga
che leggesse la testata sotto policy, in qualunque caso in cui la riga è
raggiungibile e la testata no, tornerebbe zero righe e leggerebbe «la testata
non c'è più» — cioè **lascerebbe passare proprio chi sta fuori perimetro**.

> Un guard che non distingue *«non c'è»* da *«non lo vedo»* non è più severo per
> chi sta fuori: è più permissivo.

⚠️ Il perimetro resta comunque stretto, ed è il motivo per cui la deroga è
accettabile: legge **due colonne** di una testata, non scrive, e non restituisce
niente che chi chiama non possa già dedurre dalla riga che ha in mano.

---

### ⭐ L'etichetta, e perché non è un id

Il secondo valore non è un identificativo tecnico: è la **frase** che finirà nel
messaggio d'errore letto da una persona — `DDT 2026/00123`, oppure `DDT #4711`
quando il documento non ha ancora un numero.

⚠️ E il ripiego sull'id non è un caso di nicchia. `numero` è **nullable** su
entrambe le testate, e un documento in bozza normalmente non ce l'ha: è
esattamente la situazione in cui i guard di cancellazione lavorano. Un'etichetta
che si affidasse al solo numero sarebbe vuota proprio nel caso più frequente.

---

### Note operative

* **`STABLE`**: legge e basta. La chiama un trigger `BEFORE DELETE`, una volta per
  riga cancellata.
* **`search_path` fissato** nella firma e tutti gli oggetti qualificati per
  schema: su una `SECURITY DEFINER` è la differenza fra una lettura e una porta.
* **Un guard sui parametri non serve, e non c'è**: un id nullo o `<= 0` non trova
  e basta — la risposta «zero righe» è già quella corretta. Solleva **solo** sul
  tipo documento non previsto, che è l'unico caso in cui il chiamante ha sbagliato
  a chiamare e non a cercare.

> 📎 changeSet `20260826-20`. Decisione di Tid del 2026-08-26 (la regola «solo
> bozza» scende nel DB); presidio in `db/pgtap/vendite/test-delete-righe-documento-bozza-v1.sql`.
