## 📘 Documentazione Concettuale – Tabella `config.tipi_utenze`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> • [config.utilities](/dbzero/config/tabelle/utilities)
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
>
Approfondimento funzioni:
> • [vendite.trgfn_contratti_utilities_guard_tipo_classe](/dbzero/vendite/funzioni/trgfn_contratti_utilities_guard_tipo_classe)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Tipo di **uso** dell'utenza — domestico, altri usi, condominio, pubblico. Insieme a
`config.classi_utenze` forma la coppia **tipo/classe** che qualifica un'utenza nel contratto.

---

### ⭐ Questa tabella decide un **regime**, non solo un valore

È il punto meno ovvio, e non si vede guardando le colonne.
`vendite.trgfn_contratti_utilities_guard_tipo_classe` deduce se una utility «ha la dimensione
tipo/classe» **dall'esistenza di almeno una riga qui** per quella utility:

* **utility con almeno un tipo** → sul contratto tipo **e** classe sono obbligatori e devono
  essere coerenti;
* **utility senza nessun tipo** → tipo e classe devono essere **entrambi nulli**, e
  valorizzarli è un errore.

⚠️ **Svuotare i tipi di una utility ne cambia quindi il regime**, e da quel momento i contratti
esistenti con tipo/classe valorizzati non sono più aggiornabili — anche se erano corretti
quando sono stati scritti. Va considerato prima di ripulire questa tabella.

---

### ⚠️ Oggi contiene **una** riga

Misurato il 2026-08-21: una sola riga su tutte le utilities. Il regime «con dimensione» è
quindi attivo per una utility soltanto, e tutti gli altri contratti ricadono nel ramo
«tipo e classe devono essere nulli».

---

### Le colonne

`codice`, `descrizione`, `descrizione_breve` (tutte `NOT NULL`), più i collegamenti:
`utility_id` — a quale utility appartiene il tipo — e `iva_id`, che consente di legare un
regime IVA al tipo d'uso.

> ⭐ **Dal 2026-08-29 `iva_id` viene letto davvero.** È il secondo gradino dello
> stadio A del risolutore IVA (`vendite.fn_resolve_iva_riga`), raggiunto da
> `vendite.fn_get_tipo_utenza_fornitura`. ⚠️ Ma **solo dove l'articolo tace**:
> l'articolo può dichiarare di non avere un'opinione sull'IVA, questa tabella no —
> applicata per prima si prenderebbe anche cauzioni, spese e servizi.

`tipo_pdr_std` (`char(1)`, default `'0'`) è il tipo standard di punto di riconsegna: un
codice di dominio gas, che qui compare come default tecnico.

---

{% include-markdown "signature-core.md" %}
