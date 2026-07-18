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
(latest review 2026-07-18)

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

**La partita di merce è la RIGA D'ORDINE** (`ordine_riga_id`), non il documento: la merce
viaggia su più DDT, torna indietro con i resi, riparte con le ri-consegne — ma resta la stessa
partita, e il conto si tiene lì.

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

* **Chiave**: `ordine_riga_id` (la partita)
* **Contesto**: `ordine_id`, `articolo_id`
* **Il conto**: `tenuti`, `fatturati`, `differenza`

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

* **Perimetro: solo merce nata da un ordine e non composita.** Restano fuori:
  * i **DDT standalone** (senza ordine dietro): non hanno una partita su cui appoggiarsi;
  * gli **articoli compositi** (`is_composito`): le loro attività sono in unità-componente
    mentre fulfillment e resi sono in unità-padre — sommarli darebbe un numero senza senso.

  Sono follow-up dichiarati, non dimenticanze: i consumatori li trattano col comportamento
  precedente.
* **L'universo sono le partite con movimento merce**: una riga d'ordine mai evasa e mai resa
  non compare (non c'è nulla da contare).
* `security_invoker=on`: la vista è letta con i permessi di chi interroga, quindi la RLS di
  scope emittente resta attiva. ⚠️ Chi la modifica con `CREATE OR REPLACE` **deve
  ri-specificare la reloption**: non è visibile in `pg_get_viewdef` e verrebbe azzerata in
  silenzio, aprendo un bypass.
* Test: `db/pgtap/vendite/test-vw-contatore-merce-v1.sql`.

---

{% include-markdown "signature-core.md" %}
