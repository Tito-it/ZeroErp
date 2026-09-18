## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.trasferimenti_righe](/dbzero/magazzino/tabelle/trasferimenti_righe) — il dettaglio
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — origine e destinazione
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — le due righe OUT/IN
>
Approfondimento funzioni:
> • [magazzino.trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7) · analisi carico e scarico (§7-sexies)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il documento di trasferimento fra due magazzini**: da dove parte la merce
(`magazzino_id_from`), dove arriva (`magazzino_id_to`), quando, in che stato. Il dettaglio
per articolo sta nelle righe.

Un trasferimento genera **due movimenti** per riga — `TRASF_OUT` dall'origine, `TRASF_IN`
nella destinazione — con la stessa sorgente (`TRASFERIMENTO_RIGA`) e causali diverse: è così
che le due righe non collidono nell'identità del registro. Il costo della riga IN è ereditato
da quella OUT: spostare merce non cambia il suo valore, lo sposta. Uno spostamento **dentro**
lo stesso magazzino non è un trasferimento: è una coppia di movimenti fra due ubicazioni.

### Due magazzini, un emittente solo

Origine e destinazione devono appartenere allo **stesso emittente**: fra due emittenti
sarebbe una cessione con un documento, non uno spostamento. Lo fa rispettare il guard
[trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente)
(`E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`, con il campo della destinazione acceso nel form). E
un trasferimento da un magazzino a **se stesso** è rifiutato dal CHECK — che fino al 14-09
era scritto in modo da non rifiutare nulla.

### La sorgente, come sul registro

`sorgente_tipo_id` (una riga di [config.sorgenti](/dbzero/config/tabelle/sorgenti)) più
**esattamente una** chiave fra `sorgente_riga` e `sorgente_uid`, secondo quanto il catalogo
dichiara per quel tipo; senza tipo, nessuna chiave. Il guard tipizzato
(`script.trgfn_guard_sorgente_polimorfa_tipizzata`) verifica che il record esista. Qui la
sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è uno.

Fino al 14-09 la tabella portava **due** coppie di colonne sorgente (`sorgenti_*` e
`sorgente_*`) che dicevano la stessa cosa: il doppione è uscito.

### Chi può vedere e scrivere

Il perimetro poggia sul magazzino di **origine** (`rls_trasferimenti_ef_whitelist`, via
`magazzino_id_from`); la destinazione la copre il guard. Righe e note risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

### Che cos'è, dal 17-09 (decisione di Tid, D-L2-g)

Il trasferimento **interno**: dentro lo stesso magazzino fra ubicazioni, o fra magazzini diversi
dello stesso emittente, **senza documento di trasporto**. Il trasferimento con trasporto fra due
depositi è il DDT con causale `TRASFERIMENTO` (`config.causali_trasporto`), che oggi non sa da quale
magazzino parte né dove arriva. Ne discende, per il lotto che ne scriverà il posting (non il Lotto
2): `ubicazione_id_da`/`_a` sulle righe, il CHECK «magazzini diversi **oppure** ubicazioni
diverse», un guard sullo stesso emittente, la coppia `TRASF_OUT`/`TRASF_IN` con lo stesso
`transfer_uid` e l'entrata al costo dell'uscita (il ramo gemella della primitiva esiste ed è provato).

---

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
