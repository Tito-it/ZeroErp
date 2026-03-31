# Contesto operativo ZeroERP per l'assistente AI

> Questo file viene iniettato nel system prompt dell'LLM.
> Contiene vocabolario, regole e strutture essenziali del sistema.
> NON contiene dati reali — solo definizioni e regole.

## Vocabolario

- **Pratica**: contenitore tracciabile per qualsiasi processo operativo (onboarding cliente, allaccio, assistenza). Ogni evento significativo genera una pratica.
- **Flusso**: step operativo dentro una pratica, con prerequisiti, esito e scadenza. Puo' essere manuale o gestito da handler automatici.
- **Giornale di bordo**: registro immutabile di tutti gli eventi di una pratica (append-only, mai modificabile).
- **Soggetto**: identita' anagrafica — persona fisica (PF), persona giuridica (PG) o ente (ENTE).
- **Ruolo anagrafico**: funzione di un soggetto nel sistema. Lo stesso soggetto puo' avere piu' ruoli contemporaneamente (cliente, fornitore, risorsa umana).
- **Istanza utility**: rapporto contrattuale tra un soggetto con ruolo e una business area (es. fornitura gas, energia).
- **Emittente fiscale**: entita' giuridica che emette fatture. Ogni operatore e' associato a uno o piu' emittenti.
- **Operatore**: utente del sistema con profilo, reparto e permessi per area funzionale.
- **Commessa**: contenitore di attivita' fatturabili provenienti da fonti diverse, convogliate nella pipeline di fatturazione.

## Stati pratica e transizioni ammesse

| Stato | Significato |
|---|---|
| BOZZA | Pratica in preparazione, non ancora operativa |
| APERTA | Pratica attiva e operativa |
| SOSPESA | Pratica temporaneamente congelata (con tutti i flussi) |
| CHIUSA | Pratica completata |
| ANNULLATA | Pratica annullata |

Transizioni:
- BOZZA → APERTA (attivazione)
- BOZZA → ANNULLATA
- APERTA → SOSPESA (sospensione — congela anche i flussi attivi)
- APERTA → CHIUSA
- APERTA → ANNULLATA
- SOSPESA → APERTA (riattivazione — manuale o automatica via job)

La data di apertura viene impostata automaticamente alla prima transizione BOZZA → APERTA.

## Stati flusso

| Stato | Significato |
|---|---|
| DA_ESEGUIRE | Creato, in attesa di avvio |
| IN_CORSO | In esecuzione |
| COMPLETATO | Terminato con esito (positivo/negativo/parziale/non applicabile) |
| SOSPESO | Congelato (propagato dalla sospensione della pratica) |
| ANNULLATO | Annullato |
| ERRORE | Handler automatico fallito |

Al completamento di un flusso, se esistono regole di generazione automatica, vengono create nuove pratiche cross-dominio.

## Struttura anagrafica

Gerarchia a tre livelli:
1. **Soggetto** — l'identita' (chi e')
2. **Ruolo** — la funzione (cosa fa: cliente, fornitore, risorsa umana)
3. **Istanza utility** — il contratto (per quale servizio/business area)

Un soggetto PG "Acea Energia" puo' essere contemporaneamente cliente (ruolo 1) e fornitore (ruolo 2), con istanze diverse per gas e energia.

## Stati cliente

| Stato | Fatturabile |
|---|---|
| AT (Attivo) | Si |
| PR (Precontrattuale) | Si |
| SF (Sospeso fatturabile) | Si |
| SC (Sospeso non fatturabile) | No |
| CH (Chiuso) | Si |
| CF (Chiuso e fatturato) | No |
| AN (Servizio annullato) | No |

## Stati fornitore

| Stato | Blocca ordini |
|---|---|
| VE (In verifica) | Si |
| AT (Attivo/Qualificato) | No |
| SO (Sospeso) | Si |
| CE (Cessato) | Si |
| BL (Blacklist) | Si |

## Regole operative fondamentali

- **Transizioni a macchina di stati rigida**: ogni cambio stato e' validato da trigger DB. Solo le transizioni esplicitamente configurate sono ammesse.
- **Sospensione con propagazione**: sospendere una pratica congela automaticamente tutti i flussi attivi. I giorni di sospensione sono esclusi dal calcolo tempi netti.
- **Prerequisiti flusso**: un flusso puo' avere prerequisiti (altri flussi che devono essere completati prima). Verificati da guard DB prima dell'inserimento.
- **Disattivazione a cascata**: per disattivare un'entita' padre, i figli devono essere disattivati prima (trigger DB).
- **Codici generati dal sistema**: le pratiche hanno codice formato PRA-YYYY-NNNN, generato automaticamente dal sistema di codici.
- **Emittente obbligatorio**: ogni operazione e' sempre nel contesto di un emittente fiscale. Le query sono filtrate per emittente dell'operatore.
- **Audit automatico**: ogni record ha campi data_insert, user_insert, data_update, user_update — gestiti da trigger, non dal codice applicativo.

## Permessi

Il sistema permessi ha due livelli:
1. **Livello 1 — Area funzionale**: ogni operatore ha un livello di accesso per area (TUTTO, LETTURA, BLOCCATO)
2. **Livello 2 — Azioni processo**: azioni specifiche (es. "sospendi pratica") abilitate/negate per profilo

Se un operatore ha LETTURA su un'area, puo' vedere i dati ma non modificarli. Se BLOCCATO, non vede nulla.

## Convenzioni codice fiscale

Il sistema valida i codici fiscali italiani inclusa l'omocodia (sostituzione cifre con lettere secondo tabella ministeriale). Per le persone giuridiche il CF coincide spesso con la partita IVA.
