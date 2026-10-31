## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_contratti`

> **Ultimo aggiornamento**: 31 ottobre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.motivi_fermo](/dbzero/config/tabelle/motivi_fermo)
> [vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) — da dove viene il giudizio
>
Union e stock:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)
>
Per chi non sviluppa: [Cruscotti fatturazione §4.2](/guide/cruscotti-fatturazione#42-contratti-i-due-motivi).

---
### 🎯 Scopo Principale

Resolver dell'area **CONTRATTO** per la famiglia dash fatturazione / Situazione aperta: **una riga
per contratto vivo**, **de-esplosa** (DL-12, dal 2026-07-07: niente asse mese). Area **a
conteggi** (D-3).

Dal 2026-10-31 (`20261031-04`) il **giudizio di transito è riacceso**. Era sospeso dal
`20260707-03` «finché non esiste il push ricorrente»: senza push ogni contratto sarebbe stato fermo
per sempre. Il push dei canoni c'è, e il giudizio viene **dalla stessa regola del push**,
[`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati),
al giro di oggi.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Grana | 1 riga per contratto con `esito IS DISTINCT FROM 'NEGATIVO'` (D-6 alla fonte) |
| Chi si giudica | i contratti **ATTIVO** e **CESSATO** (quelli che il push legge: gli stati di emissione e di cessazione, dalle colonne `emissione` e `cessazione` del vocabolario). La **bozza** resta sospesa: `is_transitato`, `unita_transitate`, `motivo_fermo` NULL |
| `motivo_fermo` | `CANONE_NON_GENERABILE` se la funzione dà uno scartato (fonte senza periodicità, durata senza calendario, prezzo che manca alla data); altrimenti `CANONE_NON_GENERATO` se dà un addebito da mandare (canone, una tantum, storno); altrimenti NULL. Il primo vince: il push da solo non lo chiude |
| `is_transitato` | `true` se non c'è niente né da mandare né di scartato; `false` se c'è un motivo |
| `unita_transitate` | 1 se transitato, 0 se fermo (`unita_totali = 1`) |
| `competenza_mese` | `NULL` (senza asse mese non ha significato) |
| `data_riferimento` | `valido_dal` («in essere da»); se il contratto è fermo, l'addebito più vecchio che aspetta (lo scartato senza pezzo: `valido_dal`), **mai dopo oggi**: uno storno di una cessazione programmata ha la competenza nel futuro. L'anzianità del Backlog è `oggi − data_riferimento` |
| Valori | `NULL` (area a conteggi, D-3) |
| `cliente_display` | Ragione sociale intestatario BA (`billing_account → soggetto_ruolo → soggetti`), nullable |

I due motivi in `config.motivi_fermo`: `CANONE_NON_GENERATO` è RECUPERABILE, «Esegui il push dei
canoni»; `CANONE_NON_GENERABILE` è ANOMALIA, «Rivedi il contratto» (le righe sono chiuse fuori dalla
bozza: il rimedio è fuori dalla riga).

---

### Effetti a valle

* **Situazione aperta** (`vw_dash_aperto_documenti`, `is_transitato IS DISTINCT FROM true`): un
  contratto attivo con tutto in commessa **esce**, come un ordine tutto in commessa, e rientra
  quando matura il periodo dopo. Le bozze restano (giudizio NULL). I CESSATO sono fuori per fase
  (`CHIUSO`).
* **Backlog** (`vw_dash_backlog_documenti`): i contratti fermi **entrano**, anche un CESSATO con
  uno storno da mandare.
* **Union** `vw_dash_fatturazione_documenti`: stesse colonne, stessi tipi.

---

### Esempio d'uso

```sql
-- I contratti fermi e perché.
SELECT stato_codice_interno, motivo_fermo, count(*)
FROM vendite.vw_dash_fatturazione_contratti
WHERE is_transitato IS FALSE
GROUP BY 1, 2;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da `vw_dash_fatturazione_documenti` (drill-down) e
  da `vw_dash_aperto_*` / `vw_dash_backlog_*`.
* **Costo**: una chiamata di `fn_contratti_addebiti_maturati` per contratto. Su dbdev, il
  2026-10-31: 339 contratti in 0,16 s, Backlog intero 0,3 s.
* **Scartati perenni**: un CESSATO con una riga scartata resta in ANOMALIA, perché la riga è chiusa
  e il contratto non si riapre. Una quota fissa del listino senza periodicità rende ANOMALIA ogni
  contratto del listino che non la esclude: è un difetto del listino, e la segnalazione è giusta.
* RLS emittente applicata automaticamente (vista invoker su `vendite.contratti`).
* Test: `db/pgtap/vendite/test-vw-dash-contratti-giudizio-v1.sql`,
  `test-vw-dash-fatturazione-v1.sql` (test 12-14), `test-vw-dash-aperto-v1.sql`,
  `test-vw-dash-backlog-v1.sql`.

Brief: `brief-db-contratto-righe-periodiche-in-commessa` §6.13 (decisioni F-12 … F-15).

---

{% include-markdown "signature-core.md" %}
