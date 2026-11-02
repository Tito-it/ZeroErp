<div style="text-align: center; margin-bottom: 2rem;">
  <img src="/assets/images/zeroerp-logo.png" alt="Zero ERP" width="250">
</div>

# Zero ERP

> **Ultimo aggiornamento**: 2 novembre 2026

Benvenuto nella documentazione di **Zero ERP** — un ERP open-source (AGPL v3, con doppia licenza commerciale) per
aziende italiane, costruito **DB-first**: le regole di dominio vivono nel
database, Django orchestra ed espone le API, il frontend presenta e basta.

Questa non è una documentazione di riferimento e nient'altro: è il posto dove le
**decisioni sono scritte con il loro perché**. Molte pagine dicono anche cosa
*non* fare, e perché quella strada è già stata provata.

---

## Da dove iniziare

Dipende da cosa sei venuto a fare:

- **Voglio capire cos'è e perché esiste** → [Cos'è Zero ERP](./introduzione.md) ·
  [Perché Zero ERP](./perche-zeroerp.md) ·
  [Manifesto dello sviluppo concentrico](./sviluppo-concentrico.md)
- **Voglio installarlo e farlo girare** → [Prerequisiti e installazione](./installazione.md) ·
  [Liquibase: setup e workflow](./liquibase-setup-workflow.md)
- **Voglio capire come funziona un'area** (fatturazione, pratiche, listini…) →
  le [Guide](#guide-come-funziona-larea-e-perche)
- **Devo metterci le mani** → [Linee guida API](./dev/api.md) ·
  [Ricette: dove intervenire](./dev/ricette-dove-intervenire.md) ·
  [Trappole: cosa non fare](./dev/trappole.md)
- **Voglio sapere a che punto è il progetto** →
  [Mappa Concentrica](./mappa-concentrica.md): stato per anello, roadmap e
  lezioni metodologiche

---

## Cosa trovi qui

### Visione e filosofia

- **Sviluppo concentrico**: il metodo con cui il progetto cresce — un nucleo
  stabile e anelli successivi, mai dipendenze all'indietro
- **Vocabolario**: le parole del progetto, definite una volta sola
- **Mappa Concentrica**: dove siamo adesso, cosa è aperto, e le lezioni pagate
  sul campo (compresi gli errori di ordine di costruzione)

### Architettura e database

- **Architettura applicativa**: i tre strati e cosa decide ciascuno
- **Linee guida SQL e trigger**: convenzioni di naming, guard, funzioni, atomicità
- **Liquibase**: come si scrive e applica una migrazione, e cosa non si tocca mai
- **PostgreSQL**: estensioni in uso, parametri personalizzati (GUC), pgAgent,
  dblink, pgcrypto, aggiornamento di versione

### DB Zero — la struttura viva del database

Una scheda **auto-generata** per ogni tabella, vista e funzione, schema per
schema (anagrafiche, catalogo, vendite, acquisti, magazzino, pagamenti,
contabilità, pratiche, documenti, config, ui, storico, script, dbops…).

- ⛔ Le schede auto-generate **non si modificano a mano**: si rigenerano
- ✅ Accanto a ognuna c'è una sezione **manuale** con la semantica: a cosa serve
  quell'oggetto, quali regole lo governano, cosa **non** è
- ⭐ È **la fonte** per capire o modificare un oggetto esistente — non gli YAML di
  migrazione, che sono quasi sempre superati da revisioni successive

### Backend (Django)

Il contratto di ogni endpoint, area per area: scopo, input, output, regole,
dipendenze DB. Struttura standard, così due manuali si confrontano a colpo
d'occhio.

### Guide — come funziona l'area, e perché

Il livello concettuale, diviso in due:

- **Come funziona ZeroErp** — il percorso del lavoro reale:
  - *anagrafiche*: soggetti e ruoli, generazione di un cliente, indirizzi,
    contatti, conti bancari, istanze utility
  - *ciclo attivo*: listini, preventivi, offerte commerciali, contratti,
    ordini, DDT, fatturazione, cruscotti, commesse
  - *incassi*: modello contabile dei pagamenti
  - *trasversali*: pratiche e loro configurazione, documenti e stampe, mail,
    liste configurabili, risorse umane e accessi, integrazione AI
- **Approfondimenti tecnici** — i meccanismi sotto:
  - permessi e autorizzazioni, multi-face auth, contratto GUC
  - audit e tracciabilità, storicizzazione, transaction id
  - automazioni DB, parametri, code di lavoro, job pgAgent
  - sorgente polimorfa, `obsoleto_dal`, presidi e registri del debito
  - messaggi di errore e di audit, tracciamento di processi e job

### Per chi sviluppa

- **Linee guida API**: grammatica degli URL, envelope, errori, atomicità,
  paginazione e ricerca
- **Cataloghi dei building block** (backend e frontend): l'inventario di ciò che
  esiste già. Si guardano **prima** di scrivere qualcosa di nuovo — è la prima
  difesa contro le duplicazioni
- **Standard frontend**: componenti, composable, CSS, i18n, pattern operativi
- **Ricette** (dove intervenire) e **trappole** (cosa non fare)
- **Playbook operativi**: backend, VM di sviluppo, provisioning dei ruoli DB,
  checklist post-upgrade
- **Come si scrive un test pgTAP** — e perché un test che passa non basta

### Tutorial e strumenti

- Framework di automazione DB, spiegato costruendone uno
- Generatore della documentazione di database

---

## Convenzioni che vale la pena conoscere subito

- **DB-first**: se una regola può stare nel database, ci sta. Non si duplica in
  Python e tanto meno nel frontend
- **Una decisione, un documento**: i cantieri hanno un *brief* che registra cosa
  è stato deciso **e cosa lo ribalterebbe**
- **La documentazione riflette la realtà, non le intenzioni**: se una voce non si
  può verificare contro il codice, non è stato — è memoria

---

[README del progetto](./readme.md) · [Licenza AGPL v3](./LICENSE-AGPL3.md) ·
[Versioni supportate](./versioni-supportate.md)
