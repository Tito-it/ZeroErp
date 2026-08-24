## 📘 Documentazione Concettuale – Tabella `config.classi_utenze`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)
> • [config.categoria_accisa](/dbzero/config/tabelle/categoria_accisa)
> • [config.tipi_tariffe_ee](/dbzero/config/tabelle/tipi_tariffe_ee)
> • [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
>
Approfondimento funzioni:
> • [vendite.trgfn_contratti_utilities_guard_tipo_classe](/dbzero/vendite/funzioni/trgfn_contratti_utilities_guard_tipo_classe)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

La **classe di utenza**: il livello di dettaglio sotto il tipo, e il punto in cui convergono
tutti gli assi tecnico-fiscali di un'utenza elettrica.

Una classe raccoglie in una riga sola: a quale **tipo** appartiene (`tipo_utenza_id`), quale
**accisa** le si applica (`categoria_accisa_id`), quale **tariffa** di mercato elettrico
(`tipi_tariffa_ee_id`), la **potenza contrattuale** ammessa (`pot_contratto_min_ee` /
`max_ee`, entrambe `NOT NULL`) e il `tipo_pod`.

---

### ⚠️ La classe deve appartenere al tipo dichiarato

È la regola che `trgfn_contratti_utilities_guard_tipo_classe` verifica sul contratto:
`classi_utenze.tipo_utenza_id` deve coincidere con il `tipo_utenza_id` scritto sul contratto,
altrimenti `E_CONTRATTO_CLASSE_TIPO_INCOERENTE`.

⚠️ **`tipo_utenza_id` è però `nullable`.** Una classe senza tipo esiste dal punto di vista del
vincolo, ma sul contratto non passerà mai: il confronto `IS DISTINCT FROM` la respinge sempre.
E l'errore che ne esce parla di *incoerenza fra due tipi*, non di *classe senza tipo* — la
causa vera va letta nel `context`, dove `tipo_utenza_id_classe` è `null`.

---

### ⚠️ Oggi contiene **una** riga

Misurato il 2026-08-21. Le due tabelle che referenzia — `categoria_accisa` e
`tipi_tariffe_ee` — sono invece **vuote**, quindi quella riga ha necessariamente entrambi i
riferimenti nulli.

È coerente con lo stato del dominio energia: la struttura è completa, la configurazione no.

---

### La potenza è obbligatoria, gli altri assi no

`pot_contratto_min_ee` e `pot_contratto_max_ee` sono `NOT NULL`; accisa, tariffa e tipo sono
tutti nullable. Il disegno assume quindi che una classe **debba** sempre dichiarare una banda
di potenza, mentre gli altri attributi possono arrivare dopo.

⚠️ Non c'è un CHECK che imponga `min <= max`: una banda invertita è oggi scrivibile.

---

{% include-markdown "signature-core.md" %}
