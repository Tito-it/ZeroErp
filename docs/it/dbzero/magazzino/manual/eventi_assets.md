## 📘 Documentazione Concettuale – Tabella `magazzino.eventi_assets`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — di chi è l'evento
> * [config.tipi_evento_assets](/dbzero/config/tabelle/tipi_evento_assets) — che cosa è successo
> * [config.stati_assets](/dbzero/config/tabelle/stati_assets) — da quale stato a quale
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il movimento gemello
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della sorgente
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello tipo, documento, riga

---

### 🎯 Scopo Principale

**Il ciclo di vita di un asset**: installazione, rientro, sostituzione, manutenzione. Ogni
riga dice che cosa è successo a un asset (`tipo_evento_id`), quando, da quale stato a quale,
ed eventualmente da quale magazzino a quale (se ci sono entrambi, sono diversi).

⭐ L'evento e il movimento sono due cose distinte: l'installazione genera un movimento
(`ASSET_INSTALL`, −1) **e** un evento qui. Il movimento dice che il pezzo è uscito dal
magazzino; l'evento dice che cosa è successo all'asset. L'evento è la **sorgente** del
movimento (tipo `EVENTO_ASSET` in `config.sorgenti`, la chiave dell'evento in `sorgente_id`,
senza riga: l'evento non ne ha): è così che i due lati si legano. Scriverli
insieme, in una transazione sola, è compito dell'operazione che li produce, che ancora non
esiste.

---

### Da quale documento nasce l'evento

Qui la sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è
uno. Quando c'è, `sorgente_tipo_id` è il tipo del documento in
[config.sorgenti](/dbzero/config/tabelle/sorgenti), la sua chiave sta in **una sola** fra
`sorgente_id` e `sorgente_uid` (quella che il catalogo dichiara per quel tipo) e
`sorgente_riga`, se scritta, dice la riga di quel documento; senza tipo, tutte vuote
(`chk_mag_eventi_assets_sorgente_forma`). Il guard unico
[script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) verifica che il
documento esista e sia visibile, e che la riga gli appartenga; basta il documento intero. Un
documento citato qui non si può cancellare finché la citazione resta.

---

### Chi può vedere e scrivere

Un evento appartiene all'emittente del suo **asset** (`rls_eventi_assets_ef_whitelist`, via
asset): un evento può non avere magazzino, l'asset ha sempre un emittente. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Note di migrazione

* 2026-09-15 — `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7): esce il riferimento libero
  `doc_*`, che la tabella portava insieme alla sorgente a catalogo; il CHECK sui magazzini di
  partenza e arrivo, che fino ad allora non rifiutava nulla, comincia a funzionare.
* 2026-11-08 — la sorgente passa al modello comune (`brief-db-sorgente-documento-e-riga`): la
  chiave del documento in `sorgente_id` o `sorgente_uid`, la riga in `sorgente_riga`, il CHECK di
  forma e il guard unico al posto del guard tipizzato; esce l'indice unico sulla sorgente.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
