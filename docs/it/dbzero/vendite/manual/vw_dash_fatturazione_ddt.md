## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_ddt`

> 👀 **Vedi anche**
>
Aggregata e rami gemelli:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_fatturazione_ordini](vw_dash_fatturazione_ordini.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)
>
Approfondimento tabelle:
>
[vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)
> [config.motivi_fermo](/dbzero/config/tabelle/motivi_fermo)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §4a

---
### 🎯 Scopo Principale
(latest review 2026-07-18)

`vendite.vw_dash_fatturazione_ddt` è il **resolver dell'area DDT**: la sesta area della
Dashboard Fatturazione. Ha la stessa forma dei cinque gemelli (identiche 19 colonne), e da
`vw_dash_fatturazione_documenti` **entrambe le lenti la prendono da sole** — il serbatoio
filtra `fase <> CHIUSO`, il backlog filtra `classe <> FISIOLOGICO`.

Risponde a: *quali bolle di consegna portano valore che deve ancora diventare fattura, e
perché sono ferme?*

---

### ⚠️ La popolazione: solo i DDT che hanno un ruolo di fatturazione

Non tutti i DDT c'entrano con la fatturazione. Entrano solo quelli che fattureranno davvero:

| DDT | Dentro? | Perché |
|---|---|---|
| da ordine con trigger **SPEDITO/CONSEGNATO** | ✅ | è lui il veicolo di fatturazione |
| **standalone** con causale fatturabile | ✅ | fattura in proprio |
| da ordine con trigger **CONFERMATO** | ❌ | ha fatturato l'ordine alla conferma: lui non fatturerà mai |
| con **causale non fatturabile** | ❌ | solo trasporto: la merce viaggia ma non c'è una vendita |

L'esclusione dei DDT a trigger `CONFERMATO` chiude **due difetti in un colpo**, senza
meccanismi dedicati:

1. **il falso positivo**: quel DDT non ha uno stato-trigger con cui confrontarsi
   (`CONFERMATO` è uno stato *ordine*, non esiste fra gli stati DDT) → resterebbe segnalato
   come «push non eseguito» **per sempre**, con un'azione che il sistema stesso rifiuta;
2. **il doppio conteggio**: l'ordine sta già nel serbatoio col suo valore — sommarci il DDT
   significherebbe contare due volte la stessa merce.

Il criterio è **lo stesso discriminatore del lister di push**, letto **per la stessa strada**
(il trigger si risolve via `ordini_righe_fulfillment`): la card mostra la stessa popolazione
che il motore considera sua. Fonte unica anche qui.

---

### Il motivo per cui è fermo — «in viaggio» ≠ «in ritardo»

| Situazione | `motivo_fermo` | Classe |
|---|---|---|
| tutto già fatturato / documento annullato | *(nessuno)* | — |
| DDT in bozza | `DOC_BOZZA` | 🟢 FISIOLOGICO |
| **non ha ancora raggiunto lo stato che fattura** | `IN_TRANSITO` | 🟢 FISIOLOGICO |
| dallo stato-trigger in poi, mai pushato | `PUSH_NON_ESEGUITO` | 🟠 RECUPERABILE |
| idem, pushato solo in parte | `PUSH_PARZIALE` | 🟠 RECUPERABILE |

La soglia è il **rank dello stato-trigger** dell'ordine (`config.stati_doc_ddt.ordine`); per un
DDT standalone, che non ha ordine, la soglia è `SPEDITO` — il primo stato in cui il lister lo
considera. `IN_TRANSITO` è fisiologico apposta: **merce in viaggio non è arretrato**, e per
questo l'area non compare nel backlog finché il DDT non arriva a destinazione.

---

### 📑 Campi chiave esposti

Le **19 colonne del contratto comune** ai resolver: `area` (`'DDT'`), `competenza_mese`,
identificativi del documento, emittente, `valore_totale` / `valore_transitato`,
`unita_totali` / `unita_transitate`, `is_transitato`, `is_abortito`, `motivo_fermo`, stato,
`cliente_display`, `data_riferimento`.

* **Valore**: il DDT non ha importi in testata, quindi si somma per riga con
  `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)` — lo stesso prezzo che
  userà il push. ⚠️ `vw_ddt_righe_iva_base` **non è riusabile** qui: filtra
  `prezzo_unitario IS NOT NULL` e perderebbe proprio le righe da evasione, che il prezzo lo
  ereditano.
* **`data_riferimento` = `ddt.data`**: non esiste una data di spedizione reale
  (`data_ora_consegna_prev` è *prevista*).
* **`fase` e `is_abortito` dal catalogo** (`config.stati_doc_ddt`), come tutti i gemelli.

---

### Esempio d'uso

```sql
-- I DDT consegnati che devono ancora andare in fatturazione.
SELECT codice, cliente_display, valore_totale, motivo_fermo
FROM vendite.vw_dash_fatturazione_ddt
WHERE motivo_fermo = 'PUSH_NON_ESEGUITO'
ORDER BY data_riferimento;
```

---

### Note operative

* **La quantità non è qui**: questa vista misura il *valore fermo* di un documento. Quanti
  pezzi siano davvero da fatturare lo dice la partita di merce
  ([vw_partite_merce](vw_partite_merce.md)), ed è quello che il lister proietta.
* `security_invoker=on` — la famiglia dash è sotto scope emittente. ⚠️ Ri-specificarla a ogni
  `CREATE OR REPLACE`: non è visibile in `pg_get_viewdef` e verrebbe azzerata in silenzio.
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-ddt-v1.sql`.

---

{% include-markdown "signature-core.md" %}
