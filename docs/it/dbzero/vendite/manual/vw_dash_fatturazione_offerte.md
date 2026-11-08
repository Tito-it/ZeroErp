## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_offerte`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — il documento, una riga per offerta
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — il figlio contratto, che dichiara l'offerta come provenienza
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — il figlio ordine, che dichiara l'offerta come provenienza
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) — lo stato e l'esito dell'offerta
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `OFFERTA_COMMERCIALE`
>
> Approfondimento viste:
>
> * [vendite.vw_dash_fatturazione_documenti](/dbzero/vendite/views/vw_dash_fatturazione_documenti) — l'unione delle aree, che consuma questa vista
> * [vendite.vw_dash_aperto_documenti](/dbzero/vendite/views/vw_dash_aperto_documenti) — l'aggregato dell'aperto
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.vw_dash_fatturazione_offerte` è il resolver dell'area `OFFERTA_COMMERCIALE` della dashboard della fatturazione: una riga per offerta, a conteggi.

L'area non ha valore in euro: le righe dell'offerta sono eccezioni al listino e l'offerta non
ha un totale di testata. I valori sono vuoti, `unita_totali` vale 1 e `unita_transitate` 0 o 1.

---

### Il transito si legge dai figli

L'offerta **non ha uno stato dopo il push** (resta accettata): il transito si legge dai suoi
**figli**, cioè dai documenti che la dichiarano come provenienza (tipo `OFFERTA_COMMERCIALE` e
la chiave dell'offerta, nella colonna che il tipo vuole).

| Aspetto | Regola |
| --- | --- |
| Figlio contratto | un contratto che nasce dall'offerta; vivo se non annullato (`is_abortito_snapshot`) |
| Figlio ordine | un ordine che nasce dall'offerta; vivo se l'esito del suo stato non è `NEGATIVO` |
| `is_transitato` | esiste un figlio **vivo** |
| Competenza | il mese della validità, o in mancanza dell'emissione o dell'inserimento (giorno operativo) |
| `is_abortito` | l'esito dello stato dell'offerta è `NEGATIVO` (rifiutata, annullata, superata) |
| `motivo_fermo` | `DOC_BOZZA` · `IN_ATTESA_ACCETTAZIONE` (emessa) · `SENZA_FIGLIO` (accettata, nessun figlio) · `FIGLIO_ABORTITO` (solo figli annullati); vuoto se transitata o abortita |
| `cliente_display` | la ragione sociale dell'intestatario dell'istanza utility, se c'è |

⭐ **Un'offerta ha al più un figlio vivo, ma può averne più annullati.** I figli si riassumono
in una riga per lato (esiste, vivo): l'offerta non si duplica, e un figlio annullato non
nasconde quello vivo.

⚠️ **`FIGLIO_ABORTITO` non è `SENZA_FIGLIO`**: l'offerta ha generato un documento, poi
annullato. Un documento annullato conserva la provenienza ma non consuma l'offerta: l'offerta
si sblocca **generando** un nuovo contratto o ordine.

---

### Chi la usa

* **Non si interroga dal backend**: il backend passa da `vendite.vw_dash_fatturazione_documenti`
  e dalle viste `vw_dash_aperto_*`.
* È `security_invoker = on`: la RLS per emittente di `vendite.offerte_commerciali` si applica
  attraverso la vista.

---

### Test

* `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql` — le aree della dashboard.

---

### Note di migrazione

* 2026-07-03 — la vista è parte della dashboard della fatturazione (brief-design-dashboard-fatturazione §5).
* 2026-11-06 — i figli si leggono dalla provenienza `sorgente_*` (tipo `OFFERTA_COMMERCIALE`),
  non più da `vendite.contratti.offerta_id` né da `vendite.ordini.documento_origine_*`, ritirate
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
