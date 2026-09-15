## 📘 Documentazione Concettuale – Tabella `magazzino.assets`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il modello (`requires_serial`)
> • [config.assets_ownership](/dbzero/config/tabelle/assets_ownership) — di chi è la proprietà
> • [config.stati_assets](/dbzero/config/tabelle/stati_assets) — lo stato nel ciclo di vita
> • [magazzino.eventi_assets](/dbzero/magazzino/tabelle/eventi_assets) — che cosa gli è successo
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — `asset_id`: dove è passato
>
Approfondimento funzioni:
> • [script.fn_scope_ef_whitelist_via_asset](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_asset)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7) · analisi carico e scarico (§7-quater, §7-sexies)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il pezzo serializzato**: l'istanza fisica di un bene con matricola — un contatore,
un'apparecchiatura, una stampante — che il magazzino sposta **uno alla volta**
(`movimenti.asset_id`, con quantità 1). Un asset è un bene che esce dal magazzino ma non
smette di essere nostro: installato presso un cliente, in comodato, in riparazione.

Ogni asset dice: che cosa è (`articolo_id`), la sua **matricola** (`seriale`, unica), di chi
è la **proprietà** (`ownership_id`: nostro, in conto deposito, del cliente — è la dimensione
per la merce di terzi), in che **stato** è (`stato_id`), e — facoltativi — presso quale
billing account e sotto quale contratto si trova.

---

### L'asset non è il suo GPS

Fino al 14-09 la tabella portava `magazzino_id`, `ubicazione_id` e un testo `ubicazione`:
tre colonne per dire *dove è adesso*, da tenere allineate a mano. Sono uscite. **Dove si
trova** lo dice il registro: l'ultimo movimento che nomina l'asset. Ciò che un asset porta in
proprio è invece **di chi è** — `emittente_fiscale_id`, obbligatorio — perché un asset
installato presso un cliente non è in nessun magazzino, ma è sempre di un emittente. È la
seconda ancora del perimetro (la prima è il magazzino).

---

### Chi può vedere e scrivere

Un operatore vede e scrive gli asset del **proprio emittente** (policy
`rls_assets_ef_whitelist`, diretta); chi scrive deve avere quell'emittente nel perimetro
(`trgfn_guard_emittente_scope`). Gli eventi dell'asset e le sue note risalgono a lui
(`fn_scope_ef_whitelist_via_asset`). Meccanismo comune:
[Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

Fino al 14-09 la tabella era nel registro del debito RLS («quale delle due chiavi nullable,
billing account o contratto, porta il perimetro?»): la risposta è stata la terza chiave, e
la riga di debito è uscita.

---

### Le reti

* `uq_mag_assets_seriale` — la matricola è unica;
* un asset con eventi o note non si spegne, e non si assegna a un articolo, uno stato o una
  proprietà spenti (guard generati dal framework);
* `tx_id`, audit e storicizzazione, con il perimetro dell'emittente congelato nella storia.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
