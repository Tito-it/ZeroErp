## 📘 Documentazione Concettuale – Funzione `script.fn_get_permessi_riepilogo_aree()`

> 👀 **Vedi anche**
>
> **Cosa legge:** [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) · [script.vw_override_operatore_area](/dbzero/script/views/vw_override_operatore_area) · [script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni) · [script.fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti)
>
> **Chi la legge:** il riepilogo permessi del backend (la lista operatori con i permessi aperti)

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

Per un gruppo di operatori — di solito quelli di una pagina della lista — dice,
**area per area**:

| Colonna | Cosa dice |
| --- | --- |
| `livello` | il livello effettivo dell'operatore sull'area (Bloccato, Lettura, Tutto) |
| `override_count` | quante eccezioni ha scritto l'operatore in quell'area |
| `voci_limitate` | quante sue azioni e quanti suoi oggetti l'area sta bloccando: l'eccezione dice sì, l'area dice no |

È la riga di chip sotto ogni operatore: `Anagrafiche · Tutto · 3 ⚠`.

---

### Come risponde

* Una riga per ogni operatore chiesto e ogni area attiva, **anche senza
  eccezioni** (in quel caso `override_count` vale 0).
* Non fa calcoli suoi: legge le stesse funzioni che decidono i permessi. Per
  questo dice sempre la stessa cosa del pannello dei permessi.
* Un **super admin** risulta Tutto ovunque e non ha mai voci limitate.
* Un operatore con la **veste spenta** risulta Bloccato ovunque e non ha voci
  limitate; le sue eccezioni scritte si contano lo stesso.
* Gli operatori si passano come elenco di id. Un id ripetuto vale una volta;
  un elenco vuoto non restituisce niente.

Presidio: `db/pgtap/script/test-permessi-riepilogo-aree-v1.sql` (test 9-16).

{% include-markdown "signature-core.md" %}
