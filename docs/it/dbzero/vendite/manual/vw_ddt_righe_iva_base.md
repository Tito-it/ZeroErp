## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_righe_iva_base`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
Approfondimento viste:
> • [vendite.vw_ddt_riepilogo_iva_dettaglio](/dbzero/vendite/views/vw_ddt_riepilogo_iva_dettaglio)
>
Approfondimento funzioni:
> • [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Strato di base** del calcolo IVA sui DDT di vendita: una riga per riga di DDT, con
l'aliquota già risolta e i tre imponibili calcolati **a piena precisione**, senza
arrotondamenti.

Non è una vista di presentazione. Esiste perché il riepilogo IVA
(`vw_ddt_riepilogo_iva_dettaglio`) possa sommare valori non arrotondati e arrotondare **una
volta sola**, alla fine. Arrotondare per riga e poi sommare darebbe un totale diverso, e su un
documento fiscale la differenza è un errore.

Il suffisso `_full` sulle colonne segnala esattamente questo: `imponibile_lordo_full`,
`sconto_riga_full`, `imponibile_riga_full` sono valori **non arrotondati**, da non mostrare
mai così come sono.

---

### L'aliquota dipende dall'emittente, non solo dall'IVA

```sql
config.fn_get_aliquota_iva(r.iva_id, s.stato_id)
```

L'aliquota effettiva si risolve incrociando il codice IVA con lo **stato del soggetto
emittente**, ricavato risalendo `ddt → emittenti_fiscali → soggetti_ruoli → soggetti`. Lo
stesso codice IVA può quindi valere aliquote diverse a seconda di chi emette.

⚠️ Quella catena è fatta di **`LEFT JOIN`**: se l'emittente non è valorizzato o non risolve,
`stato_emittente_id` resta `NULL` e l'aliquota viene calcolata con uno stato nullo. La riga
**non sparisce** — arriva con `aliquota_effettiva` eventualmente nulla, e a valle il riepilogo
la tratta come zero (`COALESCE(..., 0)`).

⭐ È il punto in cui un DDT con emittente incompleto produce **imposta zero invece di un
errore**. Vale la pena saperlo prima di fidarsi di un riepilogo che torna a zero.

---

### ⚠️ Il `WHERE` esclude tre categorie di righe, e una non è ovvia

```sql
WHERE r.attivo IS TRUE
  AND r.quantita > 0
  AND r.prezzo_unitario IS NOT NULL
```

Le prime due condizioni sono attese. La terza no, ed è quella che conta:

**le righe DDT senza prezzo non entrano nel riepilogo IVA.** `ddt_righe.prezzo_unitario` è
nullable, e il database ammette da sempre la riga senza prezzo — `fn_genera_ddt_riconsegna`
ne crea. Quelle righe compaiono sul documento ma **non contribuiscono a nessun imponibile**,
in silenzio: non c'è errore, non c'è warning, semplicemente il riepilogo non le conta.

È il comportamento voluto — un imponibile non si inventa — ma va tenuto presente ogni volta
che il totale di un DDT non torna con l'elenco delle sue righe. La prima domanda è: *quante
righe hanno `prezzo_unitario` nullo?*

---

### Scope

`WITH (security_invoker = on)`: eredita la RLS di chi interroga. `vendite.ddt` ha la RLS
attiva ed è agganciato con **`JOIN` interno**, quindi le righe di un DDT fuori perimetro non
compaiono affatto.

---

{% include-markdown "signature-core.md" %}
