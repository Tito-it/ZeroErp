## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_righe_dettaglio`
### 🎯 Scopo Principale
(latest review 25-08-2026)

**Le righe di un reso, come le vede il drawer di dettaglio**: anagrafica di riga,
copertura della ri-consegna, quota già accreditata e — dal 2026-08-25 — il
**motivo per cui l'annullo dell'accredito è bloccato**.

```sql
SELECT * FROM vendite.vw_resi_righe_dettaglio
 WHERE reso_id = :reso AND attivo IS TRUE
 ORDER BY riga_nr, id;
```

> 👀 **Vedi anche**
>
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare) — l'altra superficie dell'accredito
> [script.fn_check_accredito_annullabile](/dbzero/script/funzioni/fn_check_accredito_annullabile)
> [vendite.fn_resi_riga_accreditato_partita](/dbzero/vendite/funzioni/fn_resi_riga_accreditato_partita)
> [vendite.fn_resi_riga_residuo_riconsegna](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna)
> [vendite.fn_annulla_accredito_riga_reso](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso)

---

### Perché esiste

Fino al 2026-08-25 le righe del reso erano l'**unico dettaglio documento servito
da SQL scritto in Python** (`resi_repository.py::list_righe`) invece che da una
vista.

Non era una questione di stile. Quando il team BE ha chiesto il motivo di blocco
dell'annullo *«sia sulle righe del reso sia sulla coda accrediti»*, il database
poteva consegnarlo **su una superficie sola** — e proprio non quella giusta:
misurato lo stesso giorno, **le tre righe con un accredito sono tutte uscite
dalla coda al verbo**, quindi il pulsante «Annulla l'accredito» vive **qui**.

⭐ E finché quella query stava in Python, **ogni colonna derivata andava aggiunta
due volte**.

`list_righe` non aveva filtri dinamici: era una `SELECT` piatta con
`WHERE rr.reso_id = %s AND rr.attivo IS TRUE ORDER BY rr.riga_nr, rr.id`. Era
una vista, scritta nel posto sbagliato.

---

### Le colonne, per gruppi

| Gruppo | Colonne |
| --- | --- |
| **Identità** | `id`, `reso_id`, `riga_nr`, `attivo` |
| **Origine** | `ddt_riga_id`, `ordine_riga_id` |
| **Articolo** | `articolo_id`, `articolo_codice`, `articolo_descrizione`, `descrizione` |
| **Quantità** | `quantita`, `qta_operativa`, `factor_to_base`, `uom_operativa_id`, `uom_codice` |
| **Tipo reso** | `tipo_reso_id`, `tipo_reso_codice_interno`, `tipo_reso_descrizione`, `riapre_residuo`, `motivo` |
| **Ri-consegna** | `qta_riconsegnata`, `qta_rinunciata`, `qta_residua`, `stato_riconsegna` |
| **Accredito** | `gia_accreditato`, **`annullo_blocco_codice`** |
| **Audit** | `meta`, `data_insert`, `data_update` |

`stato_riconsegna` è allineato **1:1** a
[`vw_resi_da_riconsegnare`](/dbzero/vendite/views/vw_resi_da_riconsegnare): la
stessa semantica nel drawer e nella coda, `RINUNCIATA` quando la copertura si è
chiusa per rinuncia e non per consegna. È `NULL` sui tipi di reso che non
riaprono il residuo.

---

### ⚠️ La vista proietta, il chiamante filtra

`attivo` è una **colonna**, non un filtro incorporato. Anche l'ordinamento resta
al chiamante.

È una scelta: una vista chiamata «dettaglio» che nascondesse righe di nascosto
darebbe un conteggio diverso da quello della tabella **senza che niente lo
dica** — il genere di sorpresa che si scopre contando male mesi dopo. Il filtro
resta dov'era, cioè esplicito in chi interroga.

Presidiato dal **test 5**, che confronta il numero di righe della vista con
quello della tabella a perimetro pari.

---

### ⛔ Il perimetro: la vista passa da `vendite.resi`

Misurato: `vendite.resi` ha `relrowsecurity = t`
(`rls_resi_ef_whitelist`), `vendite.resi_righe` **no**.

Una vista costruita sulle sole righe sarebbe leggibile per **qualunque
`reso_id`**, anche fuori dal perimetro emittente di chi chiede. Il join alla
testata — una chiave primaria — la riporta dentro il recinto per costruzione.

⚠️ **E non basta che oggi il service autorizzi prima.** Un oggetto di database
dev'essere sicuro da solo, perché **il prossimo consumatore non sa cosa faceva il
primo**.

⚠️ È la **stessa classe di difetto** trovata lo stesso giorno sugli archi
`B`/`E`/`F`/`G` del grafo di genealogia (changeSet `20260825-19`): le tabelle
figlie e le tabelle ponte non danno perimetro, lo danno le **testate**. Quando se
ne trova una, si cercano i gemelli.

Per la stessa ragione la vista è **`security_invoker=on`**: dev'essere la RLS di
*chi chiede* a mordere, non quella del proprietario.

---

### ⭐ `annullo_blocco_codice`, e la sede unica

`NULL` = l'annullo dell'accredito è ammesso. Altrimenti il `reason` del **primo**
motivo restituito da
[`script.fn_check_accredito_annullabile`](/dbzero/script/funzioni/fn_check_accredito_annullabile):

| valore | significa |
| --- | --- |
| `NESSUN_ACCREDITO` | non c'è niente da annullare |
| `FUORI_PERIMETRO` | alcune rettifiche non sono visibili con i permessi di chi guarda |
| `RETTIFICA_EMESSA` | almeno una rettifica è già uscita dalla finestra |

⭐ **È la stessa funzione che
[`fn_annulla_accredito_riga_reso`](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso)
interroga per sollevare.** Lettura e guardia non possono divergere — che era il
punto della richiesta del BE: *«non una seconda scrittura: se le due divergono si
torna al punto di partenza, col pulsante spento su un annullo che sarebbe
passato»*.

⚠️ Lo stesso vale per `gia_accreditato`, che arriva da
`fn_resi_riga_accreditato_partita` e **non** da una somma rifatta qui: sui kit
N righe portano la **stessa** quota padre, e sommarle la moltiplicherebbe.

---

### 🔴 Non è una capability per riga

`linee-guida-sql` §12.4: *«le capability stanno solo sul DETTAGLIO, mai per riga
di lista; le liste fanno il gate sui codici che hanno già in riga»*.

La riga porta il codice; il frontend spegne il pulsante e mostra il motivo con
`labelOrCode`. Le tre chiamate scalari per riga (`residuo`, `accreditato`,
`annullo`) sono in `CROSS JOIN LATERAL`: valutate **una volta** per riga e
riusate: `STABLE` non garantisce il riuso fra occorrenze, e senza il `LATERAL`
`qta_residua` e i tre rami della `CASE` farebbero tre chiamate invece di una.

---

### Note operative

* **Consumatore previsto**: `resi_repository.py::list_righe`, che con questa
  vista smette di contenere SQL.
* ⚠️ **Il pulsante «Annulla l'accredito» vive qui, non nella coda.** Una riga
  esce da `vw_resi_da_accreditare` **al verbo**, quindi un accredito completo la
  fa sparire dalla coda: il reso è l'unica sede da cui si può ancora disfare.
* 🔴 Le tre `reason_key` corrispondenti (`vendite.resi.annullo_blocco.*`) devono
  esistere nei locales: `check_i18n_keys.py` fallisce se ne manca una, e un
  tooltip vuoto è peggio del pulsante acceso.
* Test: `db/pgtap/vendite/test-vw-resi-righe-dettaglio-v1.sql` (`plan(6)`) —
  forma, `security_invoker`, **perimetro**, **nessun filtro nascosto**, e la
  coerenza fra `annullo_blocco_codice` e la sede unica del predicato.
* ⭐ **Prova di equivalenza** all'introduzione: `EXCEPT` nei due versi contro
  l'SQL che sostituisce, su **tutti** i resi — 0 differenze su 17 righe. Una
  vista che rimpiazza una query si verifica così, non leggendola.
* changeSet `20260825-25`. Cantiere: `brief-design-note-credito-resi.md` §45.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

È dichiarata come vista della lista configurabile `vendite.reso_righe` (`vista_sql`, 2026-09-28): il catalogo delle liste ne controlla le colonne al migrate. Nessun cambio al corpo.

---

{% include-markdown "signature-core.md" %}
