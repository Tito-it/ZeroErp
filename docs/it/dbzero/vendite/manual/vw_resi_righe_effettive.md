## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_righe_effettive`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.resi](/dbzero/vendite/tabelle/resi)
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
> [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso)
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso)
>
Consumatori:
>
[vw_contatore_merce](vw_contatore_merce.md)
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §3b

---
### 🎯 Scopo Principale
(latest review 2026-07-18)

`vendite.vw_resi_righe_effettive` risponde a **una domanda sola**: *quale merce è davvero
tornata indietro?*

Serve perché quella domanda, prima, aveva **tre risposte diverse** sparse nel sistema — il
calcolo del residuo d'ordine, il flip di stato del DDT e le code resi filtravano ciascuno a
modo proprio, e le differenze fra quei filtri erano bug con i soldi in mezzo. Questa vista è
la **definizione unica**, e i consumatori la adottano invece di ripetere la catena di join.

**Merce effettivamente tornata = riga di reso CONFERMATA e attiva.**

| Filtro | Perché |
|---|---|
| `stati_doc_reso.codice_interno = 'CONFERMATO'` | ⚠️ **whitelist, mai `<> 'ANNULLATO'`**: il dominio contiene anche `DRAFT`, e una bozza non è merce tornata — è un'intenzione. Contarla significa sottrarre pezzi che il cliente ha ancora in mano |
| `resi_righe.attivo IS TRUE` | una riga disattivata non conta |

**Tutti i tipi di reso, senza distinzione.** Se la merce è tornata è tornata, che debba essere
accreditata o ri-spedita: il tipo dice cosa succederà dopo, non cosa c'è adesso. Chi ha bisogno
della distinzione la applica **sopra** la vista — che infatti espone `riapre_residuo` apposta.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `vendite.resi_righe` | La riga di merce resa (quantità in unità base) |
| `vendite.resi` | Testata: porta lo stato del documento |
| `config.stati_doc_reso` | Filtro `CONFERMATO` per `codice_interno` (mai id letterale) |
| `config.tipi_reso` | Espone `riapre_residuo`, il discriminante che i consumatori usano sopra |

---

### 📑 Campi chiave esposti

* **Chiave**: `resi_riga_id`
* **Legami**: `reso_id`, `ddt_riga_id`, `ordine_riga_id` — le due chiavi con cui i consumatori
  agganciano la merce (per riga DDT o per partita d'ordine)
* **Discriminante**: `tipo_reso_id`, `riapre_residuo`
* **Misura**: `quantita` (unità base)

---

### Esempio d'uso

```sql
-- Merce tornata su una partita, di qualunque tipo (uso del contatore).
SELECT SUM(quantita)
FROM vendite.vw_resi_righe_effettive
WHERE ordine_riga_id = 12345;

-- Solo la merce che dovrà essere ri-spedita (il filtro-tipo sta SOPRA la vista).
SELECT SUM(quantita)
FROM vendite.vw_resi_righe_effettive
WHERE ordine_riga_id = 12345 AND riapre_residuo IS TRUE;
```

---

### Note operative

* **Chi la usa oggi**: `vw_contatore_merce` (addendo dei tenuti, tutti i tipi),
  `fn_ordine_riga_qta_riconsegna` (solo `riapre_residuo`), il flip di stato del DDT in
  `fn_conferma_reso` / `fn_annulla_reso`.
* ⚠️ **Una definizione resta deliberatamente fuori**: il guard anti-over-return
  (`resi_righe`), che deve contare anche le **bozze** — se due bozze insieme superano il
  consegnato va bloccato subito, non alla conferma. È l'unico posto dove «tornata indietro»
  significa un'altra cosa, ed è giusto così.
* `security_invoker=on`: legge `vendite.resi`, che è sotto RLS di scope emittente. ⚠️ Chi la
  modifica con `CREATE OR REPLACE` **deve ri-specificare la reloption** — non è visibile in
  `pg_get_viewdef` e sparirebbe in silenzio.
* Test: `db/pgtap/vendite/test-vw-resi-righe-effettive-v1.sql`.

---

{% include-markdown "signature-core.md" %}
