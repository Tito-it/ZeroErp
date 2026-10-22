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

### ⛔ Rev 2026-09-05 — il listino ha un perimetro, e adesso qualcuno lo applica

`emittente_soggetto_ruolo_id` è `NOT NULL` **dal principio**, e fino a questa data non
la usava nessuno: né una policy, né un guard. ⇒ Un operatore di un'azienda vedeva e
scriveva i listini — cioè i **PREZZI** — di tutte le altre.

Adesso la tabella ha entrambe le difese della famiglia dei documenti:

| | |
| --- | --- |
| `rls_listini_ef_whitelist` | la policy **nasconde** ciò che è di altri |
| `trg_listini_a10_guard_emittente_scope_ins_upd` | il guard **rifiuta e spiega** (`E_SCOPE_EMITTENTE`) |

⭐ Servono entrambe: una policy senza guard lascerebbe scoperto il caso in cui la RLS
non morde — una `SECURITY DEFINER` di `titodb` che scriva qui passerebbe senza che
nessuno guardi l'emittente.

⚠️ **E non era solo una falla di lettura.** `chiusura_scadenze_daily` tocca ogni notte
`vendite.listini_versioni`, e sta per girare **un'azienda alla volta**: senza queste
policy avrebbe filtrato i contratti e non i listini, dicendo un'azienda e toccandole
tutte. Per questo il lavoro è arrivato prima di quella migrazione, non dopo.

⛔ **Scrivere un listino e la sua prima versione nella stessa istruzione non funziona
più**: la policy della figlia legge il padre con lo snapshot dell'istruzione. Due
istruzioni separate — vedi
[listini_versioni](/dbzero/vendite/manual/listini_versioni).

---

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
| `validita` | `daterange` NOT NULL, colonna generata da `valido_dal`/`valido_al` (linee-guida-sql §7b). Query: `validita @> data` |

---

### Regole principali

* La coppia `(utility_id, tipologia_id)` deve essere ammessa dalla matrice
  `config.listini_tipologie_utilities` con `attivo = true`. Il trigger guard
  `trgfn_listini_guard_tipologia_utility` lo verifica su INSERT e UPDATE.
* `attivo = true` abilita il listino per associazione e risoluzione prezzi.
* ⭐ **Un listino con storia non si spegne** (rev 2026-10-22): se ha almeno una versione
  ATTIVA o CHIUSA ([vendite.fn_listino_ha_storia](/dbzero/vendite/manual/fn_listino_ha_storia)),
  l'interruttore `attivo` è rifiutato con `E_LISTINO_CON_STORIA_NON_SPEGNIBILE`
  ([vendite.trgfn_listini_guard_spegnimento_storia](/dbzero/vendite/manual/trgfn_listini_guard_spegnimento_storia)).
  Si chiude con la **fine validità** della versione in vigore.
* Un listino **senza storia** si spegne; la catena generica «figli prima, padre poi»
  (`trgfn_prevent_deactivate_if_children`) chiede prima di spegnere le sue bozze.

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
