## 📘 Documentazione Concettuale – Vista `vendite.vw_contatore_merce`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
Viste collegate:
>
[vw_resi_righe_effettive](vw_resi_righe_effettive.md)
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §3a

---
### 🎯 Scopo Principale
(latest review 2026-08-17)

> ⭐ **Dal 2026-08-17 questa vista non calcola più: legge.** È diventata la lettura **per riga
> d'ordine** delle partite di merce ([vw_partite_merce](vw_partite_merce.md)), più il fatturato
> nato sull'ordine. I sei numeri storici sono rimasti **gli stessi** — la parità è stata
> verificata riga per riga — ma la nozione sotto è cambiata: **la partita non è più la riga
> d'ordine, è la riga di merce**, e la riga d'ordine è una delle sue possibili origini.
>
> **Se stai cercando il conto della merce per lavorarci, leggi
> [vw_partite_merce](vw_partite_merce.md), non questa.** Lì trovi anche la merce che un ordine
> non ce l'ha, il saldo tradotto in italiano (`stato`) e la distinzione fra «il conto torna» e
> «il conto non si sa fare». Questa vista resta il **contatore grezzo** che alimenta le
> macchine, e resta com'è per non cambiare di un pezzo le quantità che finiscono in fattura.

`vendite.vw_contatore_merce` è **il contatore**: per ogni **partita di merce** dice quanti
pezzi il cliente **ha in mano** e quanti gli sono **già stati fatturati**. La differenza fra i
due numeri è l'unica cosa che serve sapere per decidere cosa fare:

```text
differenza = tenuti − fatturati
   > 0  →  c'è merce da fatturare
   = 0  →  non c'è niente da fare
   < 0  →  è stato fatturato più di quanto il cliente tenga → va accreditato
```

È la **fonte unica** su cui si appoggiano il lister di push DDT, la coda accrediti e i
cruscotti di fatturazione: prima di questa vista ognuno rifaceva il conto a modo suo, ed è da
lì che nascevano le doppie fatturazioni.

**Questa vista aggrega per RIGA D'ORDINE** (`ordine_riga_id`): la merce viaggia su più DDT,
torna indietro con i resi, riparte con le ri-consegne, e qui la si guarda tutta insieme
dall'ordine.

> ⚠️ Fino al 2026-08-17 «aggregare per riga d'ordine» e «la partita **è** la riga d'ordine»
> erano la stessa frase, e da lì veniva il difetto: **ciò che una riga d'ordine non ce l'aveva
> non veniva contato affatto**. Oggi sono due cose distinte — la partita sta in
> [vw_partite_merce](vw_partite_merce.md), questa è una **lettura** — e la merce senza ordine ha
> finalmente un conto.

È **read-time**: nessun contatore materializzato, nessun campo da tenere allineato. I documenti
restano l'unica verità.

---

### Le due misure

| Misura | Come si ottiene |
|---|---|
| `tenuti` | `Σ ordini_righe_fulfillment.qta_evasa` − `Σ vw_resi_righe_effettive.quantita` — cioè quanto è stato consegnato meno quanto è tornato indietro. La ri-consegna alza i tenuti da sé (genera un nuovo fulfillment): **non serve nessuna regola dedicata** |
| `fatturati` | `Σ attivita_fatturabili.quantita` delle righe della partita. ⚠️ **L'esistenza della riga AF *è* la frontiera**: viene creata dall'emissione e non è mai cancellata, quindi non serve interrogare nessuno stato |

**I resi contano tutti**, di qualunque tipo (a credito o per ri-consegna): chi ha reso la merce
non ce l'ha più in mano, e il tipo di reso dice cosa succederà dopo, non cosa c'è adesso. Il
filtro di tipo appartiene ai consumatori, non al contatore.

---

### ⚠️ I due segmenti: si guardano ENTRAMBI

La merce può essere stata fatturata per due strade diverse, a seconda di come è configurato il
cliente:

| Segmento | Quando |
|---|---|
| `ORD:<ordine.uid>:R:<ordine_riga.id>` | fattura l'**ordine** alla conferma (trigger `CONFERMATO`) |
| `DDT:<ddt.uid>:R:<ddt_riga.id>` | fattura il **DDT** (trigger `SPEDITO`/`CONSEGNATO`) — attribuito alla partita via `ordini_righe_fulfillment` |

Ne esiste **al massimo uno per partita** (lo garantisce la cintura XOR del lister), quindi la
vista li somma entrambi senza dover leggere il trigger né replicarne la logica.

> **Perché è importante**: `billing_account.fatturazione_ordini` ha default `CONFERMATO`, cioè
> **sul cliente standard la merce è fatturata sotto `ORD:`**. Cercarla solo sotto `DDT:` la
> dichiarerebbe «mai fatturata» proprio nella configurazione più diffusa.

Il collegamento AF ↔ attività di commessa si fa via **`commessa_attivita_id`** (FK), non
tramite l'hash `md5(segment_key)`. Il numero della riga si estrae dal `segment_key` con
`substring(... ':R:([0-9]+)')`, robusto al suffisso `#CMP` delle distinte base.

Entrano solo le AF con `tipo_movimento = 'NORMALE'`: le righe manuali e gli oneri non sono
merce e non devono spostare il conto.

---

### 📑 Campi chiave esposti

* **Chiave**: `ordine_riga_id` (l'asse di aggregazione)
* **Contesto**: `ordine_id`, `articolo_id`
* **Il conto**: `tenuti`, `fatturati`, `differenza`
* **Il dettaglio, dal 2026-08-17**: `consegnato`, `reso`, `in_riconsegna`,
  `fatturato_su_merce`, `fatturato_su_ordine`, `fatturato_anticipato`, `partite_merce`,
  `misurabile`

⭐ **`fatturato_anticipato` è la colonna che spiega un numero che prima sembrava un guasto.**
Sul cliente standard si fattura **l'ordine alla conferma**, e la spedizione arriva dopo: finché
non arriva, quel fatturato non appartiene a nessuna merce. `differenza` diventa negativa, e un
saldo negativo si legge come «va accreditato» — mentre lì c'è solo merce da spedire. Il numero
di `differenza` non è cambiato (la parità viene prima), ma adesso accanto c'è la colonna che
dice **perché**.

---

### Esempio d'uso

```sql
-- Quanta merce è ancora da fatturare su una riga d'ordine?
SELECT tenuti, fatturati, differenza
FROM vendite.vw_contatore_merce
WHERE ordine_riga_id = 12345;

-- Tutte le partite che hanno bisogno di una nota di credito.
SELECT ordine_riga_id, -differenza AS accredito_dovuto
FROM vendite.vw_contatore_merce
WHERE differenza < 0;
```

---

### Note operative

* **Perimetro: la merce nata da un ordine.** Chi un ordine non ce l'ha — righe di DDT aggiunte
  a mano, documenti di trasporto senza ordine dietro — non compare **qui**, ed è corretto:
  questa vista guarda dall'ordine. Il suo conto c'è, e sta in
  [vw_partite_merce](vw_partite_merce.md).
* ✅ **Gli articoli compositi ora ci sono.** Erano esclusi perché le loro attività sono in
  unità-componente mentre consegnato e reso sono in unità-padre: sommarli dava un numero senza
  senso. Era una **rinuncia dichiarata** («follow-up a sé», changeSet `20260717-11`), e il
  follow-up è stato fatto: [vw_af_merce_per_riga](vw_af_merce_per_riga.md) riporta i componenti
  in unità del padre, e l'esclusione non serve più.
* **L'universo sono le partite con movimento merce**: una riga d'ordine mai evasa e mai resa
  non compare (non c'è nulla da contare). ⚠️ **Ne discende un limite di
  `fatturato_anticipato`**: una riga fatturata sull'ordine e **mai** spedita non è in questa
  vista per niente, quindi il suo anticipo non si vede. La colonna copre la spedizione
  *parziale*, non l'assenza di spedizione — che resta fuori apposta, perché portarla dentro
  significherebbe mostrare saldi negativi su merce che deve solo partire.
* ⚠️ **Le righe di ri-consegna sono escluse dall'aggregato.** I loro pezzi sono già
  nel `consegnato` della partita d'origine: contarli anche qui li conterebbe due
  volte, e non è un caso di scuola — una riga di ri-consegna **ha** una riga
  d'ordine, perché `fn_genera_ddt_riconsegna` le crea un fulfillment. Senza il
  filtro, una riga d'ordine con 9 pezzi in mano al cliente ne dichiarerebbe 17.
* ⚠️ **Qui `differenza` non è mai vuota**, a differenza di
  [vw_partite_merce](vw_partite_merce.md). Non è una svista: `fn_list_ddt_da_pushare` fa
  `COALESCE(differenza, 0)`, e un valore vuoto diventerebbe zero — cioè **una riga che smette di
  essere fatturata senza che nessuno se ne accorga**. Questa vista resta grezza per non
  rischiarlo; chi vuole la semantica parlante legge le partite.
* `security_invoker=on`: la vista è letta con i permessi di chi interroga, quindi la RLS di
  scope emittente resta attiva. ⚠️ Chi la modifica con `CREATE OR REPLACE` **deve
  ri-specificare la reloption**: non è visibile in `pg_get_viewdef` e verrebbe azzerata in
  silenzio, aprendo un bypass.
* Test: `db/pgtap/vendite/test-vw-contatore-merce-v1.sql`.

---

{% include-markdown "signature-core.md" %}
