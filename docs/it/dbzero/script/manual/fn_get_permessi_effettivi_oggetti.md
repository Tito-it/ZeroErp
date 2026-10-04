## 📘 Documentazione Concettuale – Funzione `script.fn_get_permessi_effettivi_oggetti()`

> 👀 **Vedi anche**
>
> **La regola del tetto:** [script.fn_livello_con_tetto_area](/dbzero/script/funzioni/fn_livello_con_tetto_area) · **l'area di un oggetto:** [script.fn_area_di_oggetto](/dbzero/script/funzioni/fn_area_di_oggetto) · **il catalogo:** [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)
>
> **Chi la legge:** [script.fn_resolve_livello_oggetto](/dbzero/script/funzioni/fn_resolve_livello_oggetto) · [script.fn_get_user_object_permissions_map](/dbzero/script/funzioni/fn_get_user_object_permissions_map) · il pannello permessi del backend
>
> **La gemella sulle azioni:** [script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni)

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

Risponde, per un operatore e per ogni oggetto (una tabella, un modello), a:
**che livello ha davvero su questo oggetto?** E dice anche se un override
sull'oggetto **è stato fermato dall'area**.

È l'unico posto in cui la catena degli oggetti è scritta: il controllo puntuale
(backend e verbi di scrittura), la mappa di `/me/` e il pannello la leggono da
qui.

---

### La regola: l'area è un tetto

Un override su un oggetto **può solo restringere** il livello della sua area,
mai allargarlo. Il livello effettivo è il più restrittivo fra i due:

| Area | Override sull'oggetto | Effettivo | Limitato dall'area |
| --- | --- | --- | --- |
| BLOCCATO | TUTTO | BLOCCATO | sì |
| LETTURA | TUTTO | LETTURA | sì |
| TUTTO | BLOCCATO | BLOCCATO | no |
| TUTTO | (nessuno) | TUTTO | no |

L'area è quella **dell'oggetto** (`fn_area_di_oggetto`), non quella che dice il
chiamante. Contesto non OPERATORE e identità assente danno BLOCCATO; il super
admin ha TUTTO, prima del tetto.

Un override limitato resta scritto e **dormiente**: se l'area si riapre, torna a
valere.

---

### Due modi di chiamarla

| Chiamata | Cosa restituisce |
| --- | --- |
| `(utente)` | una riga per ogni oggetto del catalogo `area_model_overrides` (un override esiste solo per un oggetto a catalogo) |
| `(utente, app_label, model_name)` | una riga sola, per quell'oggetto, a catalogo o no |

Presidio: `db/pgtap/script/test-permessi-tetto-area-v1.sql` (casi d-g e test 16-17).

{% include-markdown "signature-core.md" %}
