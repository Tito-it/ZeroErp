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

(rev 2026-08-17 — agganciata alla partita di merce; rev 2026-07-26 etichetta reso-aware;
rev 2026-07-18 forma cambiata)

> ⭐ **Dal 2026-08-17 la coda si aggancia alla PARTITA DI MERCE**
> ([vw_partite_merce](vw_partite_merce.md)) invece che alla riga d'ordine.
> Cambia una cosa sola, ed è il motivo di tutto il cantiere:
> `resi_righe.ordine_riga_id` è **facoltativo**, `ddt_riga_id` è
> **obbligatorio**. Agganciarsi al primo significava che un reso su merce senza
> ordine — una riga aggiunta a mano, un documento di trasporto senza ordine
> dietro — **usciva dal conto senza dare errore**: registrato, e mai
> accreditato.
>
> ⚠️ **Ne discende che `ordine_riga_id` può ora essere vuoto** in questa coda,
> ed è proprio la merce che prima non compariva. Resta esposto per risalire
> all'ordine quando c'è, ma **non è più la chiave**.
>
> ⚠️ **E l'accredito si distribuisce per spedizione**, non per riga d'ordine: un
> reso appartiene alla spedizione da cui la merce è tornata. Su una riga
> d'ordine evasa da più documenti di trasporto le due letture danno numeri
> diversi — e la seconda è quella giusta, perché un reso su merce **non
> fatturata** di una spedizione non deve diluire l'accredito dovuto su
> un'altra.

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

**Il tipo di reso è solo un'etichetta** — e dal 2026-07-26 non basta il tipo:

| `etichetta` | Quando | Natura |
|---|---|---|
| `DOVUTA` | reso *a credito* (la merce non torna più) **oppure** reso per ri-consegna la cui copertura residua è **esaurita** | obbligo — è arretrato |
| `FACOLTATIVA` | reso *per ri-consegna* con copertura residua **ancora > 0**: la merce può ancora tornare fuori | opzione dell'operatore |

#### Perché il tipo non basta più (rev 2026-07-26)

`riapre_residuo = true` significava «la merce tornerà al cliente, quindi l'accredito è una
scelta». Vero **finché la ri-consegna è possibile**. Ma se la quota è stata dichiarata
**definitiva** ([`resi_righe_rinunce`](/dbzero/vendite/tabelle/resi_righe_rinunce)) la merce
non torna, e l'accredito non è più una scelta. La condizione diventa:

```text
riapre_residuo AND fn_resi_riga_residuo_riconsegna(riga) > 0  ->  FACOLTATIVA
altrimenti                                                    ->  DOVUTA
```

È l'ultimo pezzo che rende **visibile** la chiusura: chi lavora la coda «dovute» prima non
vedeva mai quelle righe.

⚠️ **L'IMPORTO NON CAMBIA.** `accredito_dovuto` viene dal contatore
([`vw_contatore_merce`](/dbzero/vendite/views/vw_contatore_merce)), che le rinunce **non
toccano** per scelta di progetto. Una rinuncia cambia l'etichetta, non il numero: se dopo
una chiusura l'importo cambiasse — o la riga uscisse dalla coda — sarebbe il sintomo che la
sottrazione delle rinunce è finita nella vista sbagliata.

Il caso «tutto ri-consegnato» non serve gestirlo qui: quelle righe **escono da sole** dalla
coda (il fulfillment rialza `evaso`, `differenza` torna a 0).

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
