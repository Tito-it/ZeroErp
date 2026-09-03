## 📘 Documentazione Concettuale – Tabella `vendite.listini`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • `vendite.listini_associazioni` — **ritirata** (DROP TABLE `20260415-05`)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
> • [config.listini_tipologie](/dbzero/config/manual/listini_tipologie)  
> • [config.listini_tipologie_utilities](/dbzero/config/manual/listini_tipologie_utilities)  
>
**Approfondimento funzioni:**
>
• [trgfn_listini_guard_tipologia_utility](/dbzero/vendite/manual/trgfn_listini_guard_tipologia_utility)  
> • [trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato)  
> • [fn_resolve_prezzo_listino](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)  

### 🎯 Scopo Principale
La tabella `vendite.listini` rappresenta la testata anagrafica dei listini prezzo
del dominio vendite.

Contiene i dati stabili del listino (codice, descrizione, utility, tipologia), mentre
validita` temporale e prezzi sono demandati rispettivamente a `listini_versioni` e
`listini_righe`.

---

### Campi chiave (semantica)

| Colonna | Note |
| --- | --- |
| `codice` | Identificativo univoco del listino (`uq_listini_codice`) |
| `descrizione` | Descrizione leggibile |
| `utility_id` | FK a `config.utilities`. NOT NULL. Ogni listino appartiene a una utility. Listini commerciali generici usano utility "Base" (id=5) |
| `tipologia_id` | FK a `config.listini_tipologie`. NOT NULL. Classifica la natura delle voci (consumo, quota fissa, imposta, onere, prodotto, servizio) |
| `emittente_soggetto_ruolo_id` | FK a `anagrafiche.soggetti_ruoli`. NOT NULL (dal 14-04-2026, pricing v5). Emittente fiscale del listino: un listino vale per un solo emittente. Non e' input del resolver (viene derivato dalla sessione operatore), ma dimensione interna della tupla univoca (utility, tipologia, emittente) |
| `attivo` | Abilita il listino per associazione e risoluzione prezzi |
| `validita` | `daterange` NOT NULL calcolato dal trigger `script.trgfn_set_validita()` da `valido_dal`/`valido_al`. Query: `validita @> data` |

---

### Regole principali

* La coppia `(utility_id, tipologia_id)` deve essere ammessa dalla matrice
  `config.listini_tipologie_utilities` con `attivo = true`. Il trigger guard
  `trgfn_listini_guard_tipologia_utility` lo verifica su INSERT e UPDATE.
* `attivo = true` abilita il listino per associazione e risoluzione prezzi.
* La disattivazione e` bloccata se esistono versioni o associazioni attive
  (trigger `trgfn_prevent_deactivate_if_children`).

---

### Utilizzo previsto

* Contenitore principale per listini multi-utility;
* Classificazione per tipologia (flag semantici booleani sulla tabella tipologia);
* Separazione tra identita` listino e versionamento temporale;
* Base per mapping contesto (`listini_associazioni`) e pricing resolver.

---

### Nota storica

Il campo `dominio VARCHAR` (valori `UTILITY`/`COMMERCIO`) e` stato rimosso il 12 aprile 2026
e sostituito dalla coppia `utility_id` + `tipologia_id` che offre classificazione piu`
granulare e referenze FK anziche` stringhe.

---

{% include-markdown "signature-core.md" %}
