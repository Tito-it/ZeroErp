## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_da_accreditare`

> 👀 **Vedi anche**
>
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso) ·
> [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) (gemella)
>
> Fonti del conto:
> [vw_contatore_merce](vw_contatore_merce.md) ·
> [vw_resi_righe_effettive](vw_resi_righe_effettive.md)
>
> Consumatore: [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §3c

---

### 🎯 Scopo Principale

(rev 2026-07-18 — **forma cambiata: rileggere le regole chiave**)

**Coda di lavoro** delle righe reso per cui c'è un **accredito dovuto**: merce che il cliente
ha reso ma che gli **risulta già fatturata**. La generazione della nota di credito arriva con
una slice successiva; qui la coda dice *cosa è successo* («fatturata per 10, tenuta 7»), non
*cosa fare*.

> ⚠️ **Breaking rispetto alla forma precedente (fino al 2026-07-17).** Prima la vista
> chiedeva *«che tipo di reso è?»* ed elencava tutte le righe a credito confermate. Ora chiede
> **«il conto è in rosso?»**: popolazione e quantità vengono dal contatore, e il tipo di reso è
> degradato a semplice **etichetta**. La popolazione cambia in **entrambe le direzioni** — chi
> consuma questa vista deve rileggere le regole qui sotto.

---

### Regole chiave

**Popolazione = il conto, non il tipo.** Entra chi ha `vw_contatore_merce.differenza < 0`,
cioè `fatturati > tenuti`:

```text
accredito_dovuto = fatturati − tenuti      (esposto in colonna)
```

Cosa cambia in concreto:

* **escono** le righe a credito con conto già pareggiato — merce resa che non era mai stata
  fatturata (il push l'aveva già sottratta). Prima restavano in coda per sempre: erano falsi
  positivi eterni;
* **entrano** le righe **per ri-consegna** su merce già fatturata, prima invisibili (il filtro
  `riapre_residuo = false` le tagliava) ma che un accredito lo meritano eccome, finché la merce
  non riesce.

**Grana = riga reso** (invariata). Il conto però vive sulla *partita* (riga d'ordine), quindi
l'accredito della partita si **distribuisce** fra le sue righe reso, oldest-first, cappato alla
quantità della singola riga; chi riceve 0 esce.

**Il tipo di reso è solo un'etichetta**:

| `etichetta` | Quando | Natura |
|---|---|---|
| `DOVUTA` | reso *a credito*: la merce non torna più | obbligo — è arretrato |
| `FACOLTATIVA` | reso *per ri-consegna*: la merce tornerà fuori | opzione dell'operatore |

---

### 📑 Campi chiave esposti

* **Chiave**: `resi_riga_id` (invariata — gli ordinamenti del BE reggono)
* **Il conto (nuovo)**: `accredito_dovuto`, `tenuti`, `fatturati`
* **Etichetta (nuovo)**: `etichetta` (`DOVUTA` | `FACOLTATIVA`)
* **Riferimenti**: reso, DDT/riga DDT d'origine, `ordine_riga_id`, billing account, emittente,
  articolo, quantità resa

⚠️ **`ddt_id` e `ddt_numero` ora possono essere NULL**: la riga si aggancia alla partita via
`ordine_riga_id`, e il join al DDT è diventato facoltativo.

---

### Esempio d'uso

```sql
-- Quanto va accreditato, e perché.
SELECT reso_numero, descrizione, fatturati, tenuti, accredito_dovuto, etichetta
FROM vendite.vw_resi_da_accreditare
ORDER BY data;
```

---

### Note operative

* **Perimetro ereditato dal contatore**: solo merce nata da un ordine e non composita. Le righe
  reso senza `ordine_riga_id` (standalone) non entrano più — è la frontiera di tutta la slice,
  non una scelta di questa vista.
* **Nel backlog ci va solo la `DOVUTA`** (motivo `MERCE_RESA_GIA_FATTURATA`): le facoltative
  sono un'opzione, non arretrato. Oggi quel motivo è `FISIOLOGICO`, quindi in lista non compare
  ancora — si promuove con una cella di seed quando esisterà la NC.
* **`security_invoker=on`** + RLS sulla base; espone `emittente_fiscale_id` per il filtro
  applicativo BE. ⚠️ Ri-specificarla a ogni `CREATE OR REPLACE`.
* Test: `db/pgtap/vendite/test-vw-resi-da-accreditare-contatore-v1.sql`.

---

{% include-markdown "signature-core.md" %}
