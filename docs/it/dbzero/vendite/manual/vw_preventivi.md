## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi`

> 👀 **Vedi anche**
>
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [vendite.vw_preventivi_list](/dbzero/vendite/views/vw_preventivi_list)
> [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo)

---

### 🎯 Scopo Principale

(rev 15-05-2026)

`vendite.vw_preventivi` e' il **wrapper standard di `vendite.preventivi`** da usare
lato BE per ogni query che necessita di sapere se una revisione e' la corrente per
il proprio numero. Espone tutti i campi della tabella piu' la colonna derivata `is_attiva`.

---

### Colonna `is_attiva`

```sql
NOT EXISTS (
    SELECT 1
      FROM vendite.preventivi p2
      JOIN config.stati_doc_preventivi s2 ON s2.id = p2.stato_doc_preventivo_id
     WHERE p2.numero = p.numero
       AND p2.rev    > p.rev
       AND s2.is_abortito IS FALSE
) AS is_attiva
```

**Semantica**: `TRUE` se non esiste una revisione con `rev` maggiore e stato non-abortito
per lo stesso `numero`. Equivale a "questa e' la revisione viva piu' recente del numero".

**Proprieta' matematica**: per costruzione e' impossibile che due revisioni dello stesso
numero abbiano entrambe `is_attiva = TRUE` contemporaneamente. Se rev B > rev A con
`is_abortito = FALSE`, allora rev A ha `is_attiva = FALSE` per definizione.

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

| Caso d'uso | Vista consigliata |
| --- | --- |
| Detail preventivo (tutti i campi + is_attiva) | `vw_preventivi` |
| Lista preventivi con join cliente/stato/utility | `vw_preventivi_list` |
| INSERT / UPDATE | `vendite.preventivi` direttamente (le viste non sono aggiornabili) |
| Query interne DB senza is_attiva | `vendite.preventivi` direttamente |

---

### Performance

Il `NOT EXISTS` usa l'indice `uq_preventivi_numero_rev` su `(numero, rev)`: cerca
per `numero = ?` e `rev > ?`, operazione O(log N) sul numero di revisioni per numero.
In pratica ogni numero ha poche revisioni — costo trascurabile.

---

{% include-markdown "signature-core.md" %}
