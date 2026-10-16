## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_listino_provenienza`

> 👀 **Vedi anche**
>
> • [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga) — il guard che la legge e solleva
>
> • [vendite.listini_righe](/dbzero/vendite/manual/listini_righe) — la riga di listino, e perché non cambia identità
>
> • [vendite.fn_resolve_prezzo_listino_v2_esito](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito) — il risolutore che sceglie versione e riga di listino

### 🎯 Scopo Principale

(rev 2026-10-16, brief `brief-db-coerenza-listino-della-riga-di-commessa`, decisioni di Tid)

Dice se la **provenienza del prezzo** di una riga di commessa (o della sua attività
fatturabile) è ammessa. La provenienza è la **versione** del listino sotto cui la riga è
registrata e la **riga di listino** che ha dato il prezzo. Restituisce il codice del **primo
motivo** per cui non lo è, oppure `NULL` se va bene.

| # | Codice | La regola |
| --- | --- | --- |
| 1 | `E_ATTIVITA_LISTINO_RIGA_INCOERENTE` | la riga di listino è dello stesso articolo e della stessa unità di misura della riga e, se la versione è data, di quella versione |
| 2 | `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO` | il listino è dell'azienda che emette la commessa |
| 3 | `E_ATTIVITA_LISTINO_VERSIONE_BOZZA` | la versione non è in bozza: mai un prezzo da una bozza |

Le regole 2 e 3 guardano la versione data o, se manca, quella della riga di listino: valgono
anche per la riga con la sola versione (il push la scrive così) e per l'attività fatturabile,
che la versione non la porta.

Una riga di listino è *il prezzo di un articolo, in un'unità di misura, dentro una versione*.
Chi la cita non può contraddirla (regola 1). Non può citare il listino di un'altra azienda
(regola 2): oltre a essere sbagliato, renderebbe cieco il controllo «riga di listino
propagata», che legge le commesse con i permessi di chi modifica il listino. E non può
prendere il prezzo da una bozza (regola 3), che si modifica ancora: il prezzo non sarebbe
riproducibile.

---

### Quando non c'è niente da giudicare

Né riga di listino né versione: `NULL`. È il prezzo scritto a mano, gli oneri, le rettifiche
e il prezzo dal **kit**, che non cita una riga di listino.

---

### Perché SECURITY DEFINER

Listini e commesse hanno la sicurezza per riga (RLS) **per azienda emittente**. Letto con i
permessi di chi scrive, il listino di un'altra azienda tornerebbe a vuoto, e la regola 2
giudicherebbe un'assenza invece di un valore. La funzione restituisce solo un codice: non
rivela niente del listino. `search_path` bloccato, nomi qualificati.

È una *check* e non un *guard* (linee-guida-sql §5): non solleva. Solleva il guard che la
legge.

---

### Storia

Il 2026-10-15 la regola 1 stava in un predicato booleano, `vendite.fn_listino_riga_coerente`.
Con le regole 2 e 3 un booleano non avrebbe più detto quale regola era violata: il
2026-10-16 è stato sostituito da questa check e ritirato (`20261016-02`, `20261016-03`).

---
{% include-markdown "signature-core.md" %}
