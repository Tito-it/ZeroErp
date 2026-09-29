## 📘 Documentazione Concettuale – Tabella `magazzino.magazzini`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — di chi è il magazzino
> • [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — dove sta
> • [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — le posizioni al suo interno
>
Approfondimento funzioni:
> • [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) — la risalita che tutto il dominio usa
> • [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7, §4.10) · analisi carico e scarico (§7-sexies, M-6)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Anagrafica dei magazzini e depositi.** Un magazzino è un *luogo*, non un soggetto: il suo
indirizzo è legato ad `anagrafiche.indirizzi_dettaglio` e non passa da un ruolo anagrafico —
è la differenza rispetto a clienti, fornitori e vettori. ⚠️ `indirizzo_dettaglio_id` è
obbligatorio: serve un indirizzo prima del magazzino.

Il codice viene normalizzato da `trgfn_magazzini_normalize` (maiuscolo, senza spazi ai
bordi): `mag1`, `MAG1 ` e ` Mag1` sono lo stesso codice.

---

### L'ancora del perimetro: `emittente_fiscale_id`

Dal 15-09 ogni magazzino dice **di chi è**: `emittente_fiscale_id` è obbligatorio (con il
default dalla sessione, vedi sotto), con la FK verso `anagrafiche.emittenti_fiscali`. È l'**ancora** da cui discende il
perimetro di tutto il dominio — movimenti, attese, valore, inventari, rettifiche,
trasferimenti, ubicazioni e le loro note leggono l'emittente dal magazzino
(`fn_scope_ef_whitelist_via_magazzino`). Un magazzino senza emittente non appartiene a
nessuno e nessuno lo vedrebbe.

Un operatore vede e scrive i magazzini del **proprio emittente** (policy
`rls_magazzini_ef_whitelist`); chi scrive deve avere l'emittente che dichiara nel proprio
perimetro (`trgfn_guard_emittente_scope`, la difesa in profondità). Il meccanismo è quello
comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

✅ **Il default dell'emittente** (chiuso il 2026-09-15, decisione di Tid): se chi crea il
magazzino non indica l'emittente, lo mette il trigger `trg_magazzini_a10_default_emittente_ins`
— il building block unico [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) in modo
`SOLLEVA` — con l'emittente di lavoro di chi scrive (attivo di sessione, o assegnato). Un
super admin in modalità «tutti gli emittenti» deve dichiararlo, o legge
`E_EMITTENTE_NON_RISOLTO` invece di un errore di vincolo. Il default scatta **prima** del
guard di scope (ordine alfabetico dei `BEFORE ROW`): riempie, poi lo scope giudica. Fino a
quel giorno questa riga era un «punto aperto»: dal pannello generico un magazzino senza
emittente moriva con `23502`. Brief: `brief-db-emittente-di-default-un-bb-solo`.

---

### Le regole che il magazzino porta con sé

* nessuna operazione di magazzino attraversa due emittenti: un trasferimento fra un
  magazzino di A e uno di B è rifiutato (`trgfn_trasferimenti_guard_stesso_emittente`);
* un magazzino con movimenti, attese, inventari, rettifiche o ubicazioni non si spegne
  (guard generati dal framework delle automazioni);
* è storicizzato e la sua storia porta il perimetro dell'emittente (mappa
  `dbops.storico_scope_policy`, modo `EF`).

### Le ubicazioni le decide il magazzino (dal 18-09, Lotto 2)

`usa_ubicazioni` (default `false`): con `true` **ogni** movimento — e ogni riga di inventario o
rettifica — nomina un'ubicazione del magazzino, attiva; con `false` non può nominarne una. Lo
stesso stampo di `requires_lotto`/`requires_serial` sull'articolo: o sempre o mai. Esiste perché
un conteggio per ubicazione, su merce a registro senza posizione, avrebbe **raddoppiato** la
giacenza. Si decide alla nascita e si cambia solo a registro vuoto
([trgfn_magazzini_guard_usa_ubicazioni](/dbzero/magazzino/funzioni/trgfn_magazzini_guard_usa_ubicazioni)):
con merce dentro, un magazzino nuovo e un trasferimento. Un'area di ricezione, in un magazzino a
ubicazioni, **è** un'ubicazione.

Il magazzino è anche l'**ancora del perimetro** del ledger: il guard di scope su `movimenti`,
`movimenti_attesi` e `valore_giacenza` risale da `magazzino_id` all'emittente (modo `magazzino` di
[fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id)).

`magazzino.trasferimenti` è il trasferimento **interno** (stesso magazzino fra ubicazioni, o
magazzini dello stesso emittente, senza trasporto); quello con trasporto è il DDT `TRASFERIMENTO`
(decisione del 17-09, D-L2-g).

### Il magazzino predefinito (dal 28-09, Lotto 3)

`predefinito` segna **il** magazzino di un'azienda da cui parte la merce quando non si dice
altro: al massimo **uno per emittente** (indice unico `uq_mag_magazzini_predefinito_emittente`).
Lo legge la bolla: una bolla nata senza magazzino prende il predefinito della sua azienda
([trgfn_ddt_default_magazzino](/dbzero/vendite/funzioni/trgfn_ddt_default_magazzino)), e in
bozza lo si cambia. Nessun predefinito: la bolla resta senza, e se sposta merce il magazzino
lo chiede l'emissione.

⚠️ Il **reso** non usa il predefinito: la merce resa rientra, di norma, nel magazzino da cui
era partita la bolla d'origine (Lotto 3-bis,
[trgfn_resi_default_magazzino](/dbzero/vendite/funzioni/trgfn_resi_default_magazzino)).

### Un documento nomina solo magazzini della sua azienda

Bolla e reso possono indicare soltanto magazzini del **proprio emittente**. La regola sta in un
punto solo, [script.fn_magazzino_dell_emittente](/dbzero/script/funzioni/fn_magazzino_dell_emittente),
che legge il magazzino con i permessi di chi scrive: un magazzino di un'altra azienda risponde
come uno che non esiste, così il rifiuto non rivela niente fuori dal perimetro.

---

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
