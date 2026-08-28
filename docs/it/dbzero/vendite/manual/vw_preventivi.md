## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi`

> 👀 **Vedi anche**
>
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [vendite.vw_preventivi_lista](/dbzero/vendite/views/vw_preventivi_lista)
> [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo)

---

### 🎯 Scopo Principale

(rev 15-05-2026 · aggiornata 2026-08-28)

`vendite.vw_preventivi` e' il **wrapper standard di `vendite.preventivi`** da usare
lato BE per ogni query che necessita di sapere se una revisione e' la corrente per
il proprio numero. Espone tutti i campi della tabella piu' **quattro** colonne
derivate: `is_attiva`, `is_superata`, `is_abortito`, `has_next_revisione`.

⚠️ Il nome `is_attiva` risponde alla domanda composta («e' l'ultima **e** non e'
annullata»). Se la domanda che si sta facendo e' una sola delle due, la colonna da
usare e' un'altra — sezione seguente.

---

### Le tre colonne derivate — e le DUE domande che rispondono

(rev 2026-08-28 — changeSet `20260828-08`, brief `brief-db-revisione-attiva-due-domande`)

Una revisione puo' non essere «quella buona» per **due ragioni diverse**, che non
hanno niente a che vedere l'una con l'altra:

| Colonna | Domanda | Espressione |
| --- | --- | --- |
| `is_superata` | «qualcuno l'ha **rimpiazzata**?» | esiste una rev con `rev` maggiore e stato **non** abortito, per lo stesso `numero` |
| `is_abortito` | «e' stata **annullata**?» | lo stato proprio ha `stati_doc_preventivi.is_abortito = TRUE` |
| `has_next_revisione` | «qualcuno ha **provato** a revisionarla?» | esiste una rev con `rev` maggiore, di **qualunque** stato |

E `is_attiva` e' la composizione delle prime due:

```sql
is_attiva = NOT is_abortito AND NOT is_superata
```

⭐ **«E' l'ultima revisione?» si chiede a `is_superata IS FALSE`**, e da sola. E' il
motivo per cui le colonne esistono: fino al 2026-08-28 c'era **solo** `is_attiva`,
che rispondeva alle due domande insieme e in AND — quindi a valle non erano piu'
separabili. Chi voleva «solo l'ultima revisione» si portava dietro «e non
annullato», e non poteva farne a meno.

⚠️ **Le conseguenze erano due, entrambe visibili in interfaccia**:

* la lista preventivi filtra `is_attiva IS TRUE` di default, percio' il filtro di
  stato «Annullato» non poteva restituire **niente** — mai, per costruzione. Un
  documento annullato spariva del tutto e riappariva solo col toggle «Mostra
  storico revisioni», che pero' promette un'altra cosa: *un annullato non e' una
  revisione storica*;
* `PreventiviDrawer.vue` leggeva `!is_attiva` come «revisione superata» e forzava
  il readonly. Su un annullato che e' l'**ultima** revisione del numero, quel
  banner e' una frase falsa: nessuno l'ha superato.

⚠️ **`is_superata` e `has_next_revisione` non sono la stessa cosa**, ed e' la
distinzione che regge il flusso «ho sbagliato a revisionare, annullo e torno a
operare sul predecessore»:

| Caso | `has_next_revisione` | `is_superata` | `is_attiva` |
| --- | --- | --- | --- |
| rev 0 EMESSO, rev 1 DRAFT | `TRUE` | `TRUE` | `FALSE` |
| rev 0 EMESSO, rev 1 ANNULLATO | `TRUE` | **`FALSE`** | `TRUE` |

Una revisione abortita **non rimpiazza nessuno**: il predecessore torna a essere
la revisione viva del numero.

⛔ `has_next_revisione` era gia' calcolata a mano dal backend
(`preventivi_repository.get_preventivo`, come `has_next_revision`): stessa logica
in due posti, e uno dei due fuori dal database. Ora la sede e' una sola.

---

### Perche' `is_attiva` e' *derivata* dalle due componenti

Nella vista `is_attiva` non e' riscritta a parte: e' calcolata da `is_abortito` e
`is_superata` (un `CROSS JOIN LATERAL` le produce una volta sola). Cosi' **non
puo' driftare** da loro. Riscriverla in parallelo avrebbe ricreato, dentro la
stessa vista, esattamente il difetto che questo cantiere sta togliendo: due sedi
per lo stesso fatto.

**Proprieta' matematica (invariata)**: e' impossibile che due revisioni dello
stesso numero abbiano entrambe `is_attiva = TRUE`. Il termine sullo stato proprio
— aggiunto dal changeSet `20260708-07` — e' cio' che la garantisce anche quando
l'abortita e' in cima alla catena, e **resta**. Il difetto corretto nel 2026-08-28
non e' che `is_attiva` sbagliasse: e' che non c'era nessun'altra colonna a cui
chiedere una sola delle due domande.

---

### Perche' una vista e non un flag persistito

Il precedente flag `is_revision_attiva` (colonna booleana su `vendite.preventivi`) era
soggetto a drift: quando una revisione veniva annullata, il predecessore restava con
`is_revision_attiva = FALSE` anche se era diventato la rev viva del numero. Questo causava:

* Lista BE con filtro `is_revision_attiva = TRUE` nascondeva la rev N dopo annullamento di rev N+1
* L'utente vedeva solo la rev annullata, senza possibilita' di agire

Con la derivazione, l'annullamento di rev N+1 fa automaticamente tornare rev N come
`is_attiva = TRUE` — nessun codice aggiuntivo, nessun drift possibile.

---

### Stato `is_abortito` su `config.stati_doc_preventivi`

La derivazione si basa su `stati_doc_preventivi.is_abortito`:

| Stato | `is_abortito` |
| --- | --- |
| DRAFT | FALSE |
| EMESSO | FALSE |
| ACCETTATO | FALSE |
| RIFIUTATO | FALSE |
| SCADUTO | FALSE |
| EVASO | FALSE |
| ANNULLATO | **TRUE** |

Solo ANNULLATO e' abortito: indica che l'operatore ha rinunciato a quella specifica
istanza di revisione. Gli altri stati terminali (RIFIUTATO, SCADUTO) chiudono
l'intera negoziazione del numero — non solo la revisione — e non sono abortiti.

---

### Quando usarla

| Caso d'uso | Vista / colonna |
| --- | --- |
| Detail preventivo (tutti i campi + i flag di revisione) | `vw_preventivi` |
| Lista preventivi con join cliente/stato/utility | `vw_preventivi_lista` (la `vw_preventivi_list` e' stata rimossa dal `20260603-09`) |
| «Mostra **solo l'ultima revisione**» | `is_superata IS FALSE` — **non** `is_attiva` |
| «Il documento e' vivo e corrente» (cruscotti, resolver) | `is_attiva IS TRUE` |
| «Qualcuno ha provato a revisionarla» (diagnostica) | `has_next_revisione` |
| INSERT / UPDATE | `vendite.preventivi` direttamente (le viste non sono aggiornabili) |
| Query interne DB senza flag di revisione | `vendite.preventivi` direttamente |

---

### Performance

I tre `EXISTS` usano l'indice `uq_preventivi_numero_rev` su `(numero, rev)`: cercano
per `numero = ?` e `rev > ?`, operazione O(log N) sul numero di revisioni per numero.
In pratica ogni numero ha poche revisioni — costo trascurabile. Il `LATERAL` li
valuta **una volta per riga**, non una volta per colonna esposta.

---

{% include-markdown "signature-core.md" %}
