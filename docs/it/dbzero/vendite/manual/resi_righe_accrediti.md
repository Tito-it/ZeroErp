## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe_accrediti`

> 👀 **Vedi anche**
>
Tabelle sorelle:
>
[vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne)
> [vendite.resi_righe_rinunce](/dbzero/vendite/tabelle/resi_righe_rinunce)
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
>
Funzioni e viste:
>
[fn_accredita_riga_reso](fn_accredita_riga_reso.md)
> [trgfn_resi_accrediti_guard](trgfn_resi_accrediti_guard.md)
> [fn_resi_riga_tetti_accredito](fn_resi_riga_tetti_accredito.md)
> [fn_resi_riga_accreditato_partita](fn_resi_riga_accreditato_partita.md)
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)

---

> **Il terzo lato.** Una riga di reso ha tre uscite; due avevano già la loro
> tabella-ponte, questa è la casella che mancava.
>
> ```text
> torna al cliente   →  vendite.resi_righe_riconsegne   (resi_riga_id, ddt_riga_id, qta)
> non torna più      →  vendite.resi_righe_rinunce      (resi_riga_id, qta)
> si accredita       →  vendite.resi_righe_accrediti    ← questa
> ```
>
> Non è un'eccezione al modello: ne completa una simmetria che la doc delle due
> sorelle nominava già. Ed è il motivo per cui la nota di credito non ha avuto
> bisogno di una seconda pipeline.
>
> Piano: [brief-design-note-credito-resi](../../../dev/work-done/brief-design-note-credito-resi.md),
> decisione **D-NC-10**. Introdotta il 2026-08-18 (`20260818-35`, guard `20260818-36`).

---

### 🎯 Scopo

Registrare che **N pezzi** di una riga di reso sono stati **accreditati** al
cliente **contro una precisa riga di fattura**, e quale rettifica di commessa ne
è nata.

Serve tre cose insieme, e nessuna delle tre esisterebbe altrove:

1. **il fatto** — chi, quando, quanto, a fronte di cosa. La rettifica in
   commessa dice *cosa* è stato fatto, non *a fronte di cosa*;
2. **il presidio** contro il doppio accredito;
3. **il numero che la coda espone in riga** (`gia_accreditato`), così il
   frontend disabilita il bottone senza chiamare una capability per riga di
   lista — che il progetto vieta.

---

### Colonne che portano il senso

| Colonna | Cosa dice |
| --- | --- |
| `resi_riga_id` | la riga di reso accreditata |
| `fattura_riga_rettificata_id` | **quale** riga di fattura si accredita. È da qui che il generatore righe copierà prezzo, sconto e IVA — mai da un ricalcolo, mai dal listino |
| `qta` | la quantità nell'unità della **riga di fattura**. Su un componente di kit è `unità padre × coeff_qta` |
| `qta_partita` | la stessa quota in unità di **merce** (unità padre della partita). Coincide con `qta` quando non c'è un kit |
| `gruppo` | l'**unità consumata** a cui la riga appartiene: il segmento della rettifica privato del `#CMP` (es. `DDT:<uid>:R:<id>#RET:1`) |
| `commessa_attivita_id` | la rettifica generata. **NOT NULL**: la riga non nasce mai orfana |

#### ⚠️ Perché servono due misure, e perché serve `gruppo`

La merce si conta in **unità padre**, il documento in **unità di riga di
fattura**. Su un articolo composito le due divergono: tre righe di ponte
valgono **una** unità di merce.

E `qta_partita` va sommata **una volta per gruppo**, non una volta per riga —
due casi tirano in direzioni opposte e coesistono:

```text
kit           →  N righe con la STESSA quota padre   →  sommarle la moltiplica
consumo LIFO  →  N righe con quote padre DIVERSE     →  vanno sommate
```

`gruppo` distingue i due casi. La formula sta in un posto solo:
`vendite.fn_resi_riga_accreditato_partita`.

---

### I due tetti, e chi li tiene

```text
Σ unità di merce per riga di reso      =  accredito dovuto   ← la MADRE
Σ qta per riga di fattura              ≤  qta della riga     ← il GUARD
```

Due misure che parlano lingue diverse e devono concordare: una conta i pezzi
tornati, l'altra i pezzi fatturati. Quando divergono non c'è un numero di cui
fidarsi — c'è un difetto da guardare.

⚠️ **Non hanno lo stesso proprietario, e non è un dettaglio.** Il tetto del
**documento** è esatto riga per riga e sta nel guard
(`trgfn_resi_accrediti_guard`), dove vale anche contro una scrittura diretta.
Quello della **merce** sta in `fn_accredita_riga_reso` ed è un'**uguaglianza**
(D-NC-6: l'accredito è sempre pieno): è l'unica a conoscere l'unità padre e a
sapere quando l'operazione è finita. Un trigger di riga non sa né l'una né
l'altra cosa — e se sommasse le righe di un kit rifiuterebbe il secondo
componente di un accredito perfettamente legittimo.

La `UNIQUE (resi_riga_id, fattura_riga_rettificata_id)` ferma il **doppione
esatto**, cioè il doppio click. L'eccesso lo ferma solo il guard.

---

### Chi la scrive

**Solo `vendite.fn_accredita_riga_reso`.** Non ci sono altri scrittori, e non
devono nascerne: il verbo è una sola unità atomica, e l'ordine delle scritture
(rettifica, poi ponte, poi audit) è ciò che rende impossibile lo stato
intermedio «accredito registrato senza rettifica».

---

### ⭐ Come chiude la finestra dell'idempotenza

Fra il verbo e l'emissione della fattura, la rettifica esiste come attività
**NON_EMESSA**: l'attività fatturabile non c'è ancora, il conto della merce non
è cambiato, e senza questa tabella **la riga sarebbe ancora in coda**. Un
secondo click sarebbe stato perfettamente coerente col conto.

Con l'accredito registrato **al momento del verbo**, e con
`vw_resi_da_accreditare` che sottrae la quota già accreditata, la riga esce
dalla coda subito: l'operatore lo scopre **quando clicca**, non a fine batch su
un documento fiscale.

---

### ⚠️ Trappole di una tabella nuova

* indici FK **decisi nel seed**: una FK scoperta nasce `DA_DECIDERE` in
  `dbops.fk_index_policy`, e l'indice c'è solo se il CSV della politica la decide
  `CON_INDICE` (qui le FK verso la commessa attività e verso la riga di fattura
  rettificata). La FK verso `resi_righe` è `SENZA_INDICE` perché già coperta
  **per prefisso** dalla `UNIQUE`;
* audit, `tx_id` e storico girano solo in contesto `ci_apply`: su un migrate
  manuale li aggancia il job serale del pgagent;
* il guard legge `fatture_righe` **sotto RLS**, e una riga fuori perimetro si
  leggerebbe come «non c'è»: il tetto si legge da
  `vendite.fn_resi_riga_tetti_accredito`, che è `SECURITY DEFINER`.

---

### Query utili

```sql
-- Cosa è stato accreditato di una riga di reso, e contro cosa
SELECT a.qta, a.qta_partita, a.gruppo,
       f.numero AS fattura_rettificata, fr.prezzo_unitario
  FROM vendite.resi_righe_accrediti a
  JOIN vendite.fatture_righe fr ON fr.id = a.fattura_riga_rettificata_id
  JOIN vendite.fatture f        ON f.id  = fr.fattura_id
 WHERE a.resi_riga_id = :resi_riga_id;

-- Le due misure devono concordare: se questa query torna righe, c'è un difetto
SELECT a.fattura_riga_rettificata_id, sum(a.qta) AS accreditato, fr.qta AS fatturato
  FROM vendite.resi_righe_accrediti a
  JOIN vendite.fatture_righe fr ON fr.id = a.fattura_riga_rettificata_id
 GROUP BY a.fattura_riga_rettificata_id, fr.qta
HAVING sum(a.qta) > fr.qta;
```

---

### Importanza nel sistema

È il punto in cui «ho deciso di accreditare questo reso» smette di essere una
constatazione e diventa un fatto registrato, con una data e un autore. Senza,
la coda accrediti resterebbe quello che era prima del 2026-08-18: un elenco di
righe che chiedono qualcosa che nessun verbo sapeva fare.

---

{% include-markdown "signature-core.md" %}
