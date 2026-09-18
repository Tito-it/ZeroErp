## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe_stati`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
### 🎯 Scopo Principale
(latest review 13-02-2026)  
La tabella **`pagamenti.vendite_contabili_righe_stati`** definisce il lookup
degli stati delle **righe contabili** legate ai movimenti vendite.

---

### Campi chiave (semantica)

* `codice`: codice stato di riga.
* `codice_interno`: codice tecnico applicativo.
* `descrizione`: descrizione funzionale.
* `is_postabile`: indica se lo stato consente contabilizzazione/posting.
* `is_final`: indica stato terminale per la riga.
* `ordine`: sequenza di avanzamento stato.
* `attivo`: stato abilitato/disabilitato.
* `meta`: estensioni configurative.
* audit: `data_insert/user_insert/data_update/user_update`.

---

### Regole principali

* `codice` univoco.
* `is_postabile = true` per gli stati ammessi al passaggio contabile.
* Stati terminali marcati con `is_final = true`.

---

### Esempio d’uso

```sql
SELECT id, codice, codice_interno, is_postabile, is_final
FROM pagamenti.vendite_contabili_righe_stati
WHERE attivo IS TRUE
ORDER BY ordine, id;
```

---

### Le quattro bandiere, e perché sono quattro

| Bandiera | Risponde a |
| --- | --- |
| `is_postabile` | «questa riga è **pronta** da registrare?» |
| `is_final` | «da questo stato si va ancora da qualche parte?» |
| `richiede_abbinamento` *(2026-08-21)* | «questo stato pretende di sapere **a chi** appartiene la riga?» |
| `lavorata` *(2026-09-18, D20-a)* | «qualcuno ha **guardato** questa riga?» — `false` su `IMPORTATA` e `DA_ABBINARE`, `true` sugli altri |

⭐ **`lavorata` è la bandiera della validazione.** `VALIDATA` è «ho finito di
inserire»: entrando in `VALIDATA` una distinta non può avere righe attive in uno
stato non lavorato, perché dopo la registrazione nessuno le guarderebbe più. La
legge [script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile),
chiamata dal guard di validazione ed esposta dal dettaglio. La **sospesa è stata
guardata** — ha un motivo — e con la registrazione tardiva (D20-b) ha un futuro
anche sotto una distinta chiusa. Default `false`: uno stato nuovo non
classificato è fail-closed. ⚠️ Il valore sta nel CSV (mirror `20260821-30`).

⚠️ **La terza non è derivabile dalle prime due**, ed è la ragione per cui esiste:
`ABBINATA` pretende fattura e cliente e **non è finale**, quindi una regola
costruita su `is_final` l'avrebbe mancata del tutto.

⭐ Sta nel catalogo e non dentro il guard che la applica per la stessa ragione per
cui le transizioni stanno in una tabella: una regola in una tabella si legge e si
cambia senza toccare il codice.

⚠️ **La rata resta fuori di proposito**: su `ABBINATA` è facoltativa, perché la
riga del fondo fattura ha fattura sì e rata no — è un saldo per **trasferimento**.
Quando arriverà la colonna della scadenza, questa bandiera **non va toccata**.

### 🔴 Due correzioni del 2026-08-21

* **`SCARTATA` non è più uno stato finale.** Da lì si torna a `SOSPESA` per
  riprendere in mano una riga scartata per errore. Il catalogo la marcava finale
  mentre la matrice ammette il ritorno: *un catalogo che dichiara una cosa mentre
  la matrice ne permette un'altra insegna il falso*;
* **`STORNATA` è ritirata** (`obsoleto_dal`). Non esiste più il gesto che ce la
  portava: lo storno non è un tipo di documento, è una contabile a **importi
  negativi**. ⚠️ Ritirata, **non spenta**: `attivo` resta vero, perché spegnerla
  romperebbe le righe che la referenziassero. Chi costruisce una lista di stati
  filtra `obsoleto_dal`; chi legge uno stato già scritto **non** filtra.

### ⚠️ Gli id di questo catalogo NON sono un contratto

Il CSV di seed **non porta la colonna `id`** e il suo loader usa il `codice` come
chiave. Chi scrive una funzione deve risolvere questi stati **sempre per
`codice_interno`**, mai incidendo un id — a differenza del catalogo gemello della
testata, dove gli id sono espliciti nel CSV e sono un contratto.

---

{% include-markdown "signature-core.md" %}
