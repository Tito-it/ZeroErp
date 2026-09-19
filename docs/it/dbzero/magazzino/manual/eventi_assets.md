## 📘 Documentazione Concettuale – Tabella `magazzino.eventi_assets`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.assets](/dbzero/magazzino/tabelle/assets) — di chi è l'evento
> • [config.tipi_evento_assets](/dbzero/config/tabelle/tipi_evento_assets), [config.stati_assets](/dbzero/config/tabelle/stati_assets)
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il movimento gemello
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il ciclo di vita di un asset**: installazione, rientro, sostituzione, manutenzione. Ogni
riga dice che cosa è successo a un asset (`tipo_evento_id`), quando, da quale stato a quale,
ed eventualmente da quale magazzino a quale (se entrambi, sono diversi — un CHECK che fino al
14-09 non rifiutava nulla).

⭐ L'evento e il movimento sono due cose distinte: l'installazione genera un movimento
(`ASSET_INSTALL`, −1) **e** un evento qui. Il movimento dice che il pezzo è uscito dal
magazzino; l'evento dice che cosa è successo all'asset. Con la forma decisa, l'evento è la
**sorgente** del movimento (`EVENTO_ASSET` in `config.sorgenti`): è così che i due lati si
legano, e la scrittura in una transazione sola è compito dell'operazione (lotto successivo).

### La sorgente, come sul registro

`sorgente_tipo_id` (una riga di [config.sorgenti](/dbzero/config/tabelle/sorgenti)) più
**esattamente una** chiave fra `sorgente_riga` e `sorgente_uid`, secondo quanto il catalogo
dichiara per quel tipo; senza tipo, nessuna chiave. Il guard tipizzato
(`script.trgfn_guard_sorgente_polimorfa_tipizzata`) verifica che il record esista. Qui la
sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è uno.

Il riferimento libero `doc_*`, che questa tabella portava insieme alla sorgente a catalogo,
è uscito il 15-09.

### Chi può vedere e scrivere

Un evento appartiene all'emittente del suo **asset** (`rls_eventi_assets_ef_whitelist`, via
asset): un evento può non avere magazzino, l'asset ha sempre un emittente. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
