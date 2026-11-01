## 📘 Documentazione Concettuale – Tabella `magazzino.assets`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il modello (`requires_serial`)
> * [config.assets_ownership](/dbzero/config/tabelle/assets_ownership) — di chi è la proprietà
> * [config.stati_assets](/dbzero/config/tabelle/stati_assets) — lo stato nel ciclo di vita
> * [magazzino.eventi_assets](/dbzero/magazzino/tabelle/eventi_assets) — che cosa gli è successo
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — `asset_id`: dove è passato
>
> Approfondimento viste:
>
> * [dbops.vw_magazzino_dipendenze_inverse](/dbzero/dbops/views/vw_magazzino_dipendenze_inverse) — il registro non nomina i processi che lo usano
>
> Approfondimento funzioni:
>
> * [script.fn_scope_ef_whitelist_via_asset](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_asset) — la risalita di eventi e note all'asset
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — l'emittente di default

---

### 🎯 Scopo Principale

**Il pezzo serializzato**: l'istanza fisica di un bene con matricola — un contatore,
un'apparecchiatura, una stampante — che il magazzino sposta **uno alla volta**
(`movimenti.asset_id`, con quantità 1). Un asset è un bene che esce dal magazzino ma non
smette di essere nostro: installato presso un cliente, in comodato, in riparazione.

Ogni asset dice: che cosa è (`articolo_id`), la sua **matricola** (`seriale`, unica), di chi
è la **proprietà** (`ownership_id`: nostro, in conto deposito, del cliente — è la dimensione
per la merce di terzi), in che **stato** è (`stato_id`), e — facoltativo — presso quale
billing account si trova.

---

### L'asset non sa sotto quale contratto sta

L'asset fa parte del **registro** del magazzino, che è un servizio usato dai processi e non
deve conoscerli ([vista di controllo](/dbzero/dbops/views/vw_magazzino_dipendenze_inverse)):
per questo non porta il contratto sotto cui il bene si trova. Se un contratto dovrà sapere
quali beni ha in carico, il legame nascerà **nel contratto**, e punterà all'asset.

---

### L'asset non è il suo GPS

**Dove si trova** lo dice il registro: l'ultimo movimento che nomina l'asset. L'asset non
porta un magazzino né un'ubicazione da tenere allineati a mano. Ciò che porta in proprio è
invece **di chi è** — `emittente_fiscale_id`, obbligatorio — perché un asset installato
presso un cliente non è in nessun magazzino, ma è sempre di un emittente. È la seconda ancora
del perimetro (la prima è il magazzino).

---

### Chi può vedere e scrivere

Un operatore vede e scrive gli asset del **proprio emittente** (policy
`rls_assets_ef_whitelist`, diretta); chi scrive deve avere quell'emittente nel perimetro
(`trgfn_guard_emittente_scope`). Gli eventi dell'asset e le sue note risalgono a lui
(`fn_scope_ef_whitelist_via_asset`). Meccanismo comune:
[Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

Se chi crea l'asset non indica l'emittente, lo mette `trg_assets_a10_default_emittente_ins`
— il building block [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale)
in modo `SOLLEVA` — con l'emittente di lavoro di chi scrive; chi non ne ha uno (admin globale
in modalità «tutti gli emittenti») lo dichiara, o legge `E_EMITTENTE_NON_RISOLTO`.

---

### Le reti

* `uq_mag_assets_seriale` — la matricola è unica;
* un asset nominato da eventi, note, movimenti, attese, righe di inventario, rettifica o
  trasferimento, o prelievi non si spegne, e non si assegna a un articolo, uno stato, una
  proprietà o un emittente spenti (guard generati dal framework);
* `tx_id`, audit e storicizzazione, con il perimetro dell'emittente congelato nella storia.

---

### Note di migrazione

* 2026-09-15 — `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7; analisi carico e scarico,
  §7-quater, §7-sexies): escono `magazzino_id`, `ubicazione_id` e il testo `ubicazione`, tre
  colonne per dire *dove è adesso* da tenere allineate a mano; entra `emittente_fiscale_id`
  con il suo default. La tabella esce dal registro del debito RLS («quale delle due chiavi
  nullable, billing account o contratto, porta il perimetro?»): la risposta è stata la terza
  chiave.
* 2026-10-01 — esce il collegamento al contratto di vendita sotto cui il bene si trova: non
  lo leggeva e non lo scriveva nessuno.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
