# The Vocabulary of Concentric Development
# Il Vocabolario dello Sviluppo Concentrico

*An appendix to the Concentric Development Manifesto*
*Appendice al Manifesto dello Sviluppo Concentrico*

---

## The Trunk / Il Tronco

The system as a whole. The complete software seen from above, as a cross-section. When you cut a trunk, you see every ring, every phase of growth, every moment of stress. A well-built system can be read the same way: by examining its layers you understand its history, its structure, and its logic.

Il sistema nel suo insieme. Il software completo visto dall'alto, come una sezione trasversale. Quando tagli un tronco vedi ogni anello, ogni fase di crescita, ogni momento di stress. Un sistema ben costruito si legge allo stesso modo: esaminando i suoi strati ne capisci la storia, la struttura e la logica.

---

## The Heartwood / Il Cuore del Legno

The densest, most load-bearing part of the trunk. The first and most critical design decision in any system. It carries the weight of everything above it and is designed with absolute rigor — not because it is the most visible, but because everything else rests on it. A weakness here propagates outward through every ring.

La parte più densa e portante del tronco. La prima e più critica decisione progettuale in qualsiasi sistema. Porta il peso di tutto ciò che sta sopra ed è progettata con rigore assoluto — non perché sia la più visibile, ma perché tutto il resto vi si appoggia. Una debolezza qui si propaga verso l'esterno attraverso ogni anello.

---

## The Rings / Gli Anelli

The business domains. Each ring is a complete functional area that wraps around the inner ones: master data, invoicing, sales, warehouse, accounting. Every ring has meaning only because the one inside it exists. Every ring inherits the vocabulary of the core. No ring exists in isolation.

I domini di business. Ogni anello è un'area funzionale completa che avvolge quelle interne: anagrafiche, fatturazione, vendite, magazzino, contabilità. Ogni anello ha senso solo perché esiste quello al suo interno. Ogni anello eredita il vocabolario del nucleo. Nessun anello esiste isolato.

---

## The Dark Rings / Gli Anelli Scuri

The rings that have been rewritten, refined, and strengthened. In a real trunk, the darker rings are the ones that suffered the most — compressed by the weight of growth, stressed by the seasons. In concentric development, the dark rings are the parts of the system that were reworked because an outer ring revealed they were not strong enough. They are not scars. They are not mistakes. They are proof of integrity — the craftsman going back to the center to make it better.

Gli anelli che sono stati riscritti, raffinati e rafforzati. In un tronco reale gli anelli più scuri sono quelli che hanno sofferto di più — compressi dal peso della crescita, stressati dalle stagioni. Nello sviluppo concentrico gli anelli scuri sono le parti del sistema che sono state rilavorare perché un anello esterno ha rivelato che non erano abbastanza forti. Non sono cicatrici. Non sono errori. Sono la prova dell'integrità — l'artigiano che torna al centro per renderlo migliore.

---

## The Sap / La Linfa

The invisible cross-cutting infrastructure that nourishes every ring without belonging to any specific one: configuration, cross-cutting functions, permissions, database automation, operational scripts. These are not business domains — they are support services that flow through the entire trunk. The sap does not depend on the rings — the rings depend on the sap. It flows everywhere, serves everyone, and requires no modification when a new ring is added. You do not see it in the cross-section of the trunk, but without it the tree dies.

The rings do not need to be adjacent to share sap: an outer ring can draw directly from an inner one without passing through the rings in between. This is not a violation of the concentric order — it is simply how certain information flows through the trunk.

L'infrastruttura trasversale invisibile che nutre ogni anello senza appartenere a nessuno in particolare: configurazione, funzioni trasversali, permessi, automazione database, script operativi. Non sono domini di business — sono servizi di supporto che scorrono attraverso l'intero tronco. La linfa non dipende dagli anelli — gli anelli dipendono dalla linfa. Scorre ovunque, serve tutti e non richiede modifiche quando si aggiunge un nuovo anello. Non la vedi nella sezione del tronco, ma senza di essa l'albero muore.

Gli anelli non devono essere adiacenti per condividere la linfa: un anello esterno può attingere direttamente da uno interno senza passare per gli anelli intermedi. Non è una violazione dell'ordine concentrico — è semplicemente il modo in cui certe informazioni scorrono attraverso il tronco.

---

## Ring Zero / Anello Zero

The core protocol. Not a module, not a feature — the shared understanding that makes all modules possible. It defines how things are tracked, how errors are handled, how consistency is enforced. In ZeroERP it is the infrastructure that activates automatically for every ring built above it: traceability, transaction correlation, versioning, error handling, DB automation. No domain implements it — every domain inherits it. What matters is that it is the heartbeat that every ring can hear, without ever needing to know it is there.

Il protocollo centrale. Non un modulo, non una funzionalità — la comprensione condivisa che rende possibili tutti i moduli. Definisce come le cose vengono tracciate, come gli errori vengono gestiti, come la coerenza viene imposta. In ZeroERP è l'infrastruttura che si attiva automaticamente per ogni anello costruito sopra di essa: tracciabilità, correlazione transazionale, versionamento, gestione errori, automazione DB. Nessun dominio la implementa — ogni dominio la eredita. Ciò che conta è che sia il battito cardiaco che ogni anello può sentire, senza mai dover sapere che è lì.

---

## The Logbook / Il Giornale di Bordo

The immutable record of everything that happens in the system. Every action, every change, every transition is recorded automatically. The logbook is not an optional feature — it is a consequence of the architecture. In a concentric system, traceability is not added later. It exists from the first ring because the core enforces it.

La registrazione immutabile di tutto ciò che accade nel sistema. Ogni azione, ogni modifica, ogni transizione viene registrata automaticamente. Il giornale di bordo non è una funzionalità opzionale — è una conseguenza dell'architettura. In un sistema concentrico la tracciabilità non si aggiunge dopo. Esiste dal primo anello perché il nucleo la impone.

---

## The Craftsman / L'Artigiano

The mindset required to practice concentric development. Not a factory worker who follows instructions. Not a framework evangelist who repeats patterns. A craftsman who cares whether the joint is tight even if no one will ever see it. Someone who names a variable as carefully as a poet chooses a word. Someone who tests not just for bugs but for harmony. The craftsman builds one thing properly rather than ten things fast. The craftsman's work lasts.

La mentalità necessaria per praticare lo sviluppo concentrico. Non un operaio di fabbrica che segue istruzioni. Non un evangelista di framework che ripete pattern. Un artigiano a cui importa se la giuntura è stretta anche se nessuno la vedrà mai. Qualcuno che nomina una variabile con la stessa cura con cui un poeta sceglie una parola. Qualcuno che non testa solo i bug ma l'armonia. L'artigiano costruisce una cosa fatta bene piuttosto che dieci cose fatte in fretta. Il lavoro dell'artigiano dura.

---

## The Domain / Il Dominio

A complete functional area that speaks the language of the business, not the language of the programmer. A domain is something you can explain to a non-technical user in one sentence: "cases management," "customer records," "invoicing." If you need technical jargon to describe it — "API layer," "data access" — it is not a domain, it is infrastructure. In concentric development, every ring is a domain. The domain test: if the company director would understand the name, it is a domain. Not every schema in the database is a domain — some schemas are infrastructure, some carry the sap. The distinction matters.

Un'area funzionale completa che parla la lingua dell'azienda, non la lingua del programmatore. Un dominio è qualcosa che puoi spiegare a un utente non tecnico in una frase: "la gestione delle pratiche," "i clienti," "la fatturazione." Se ti serve gergo tecnico per descriverlo — "layer API," "accesso dati" — non è un dominio, è infrastruttura. Nello sviluppo concentrico ogni anello è un dominio. Il test del dominio: se il direttore dell'azienda capirebbe il nome, è un dominio. Non tutti gli schema del database sono domini — alcuni sono infrastruttura, altri portano la linfa. La distinzione è importante.

---

## The Bark / La Corteccia

The outermost layer of the system: the interface that the external world sees and touches. Portals, external APIs, mobile apps. The bark protects the trunk, filters what comes in, and presents what goes out. It is the most exposed layer and the most replaceable — you can change the bark without touching the wood. A frontend can be rewritten entirely while the rings remain intact.

Lo strato più esterno del sistema: l'interfaccia che il mondo esterno vede e tocca. Portali, API esterne, app mobile. La corteccia protegge il tronco, filtra ciò che entra e presenta ciò che esce. È lo strato più esposto ed il più sostituibile — puoi cambiare la corteccia senza toccare il legno. Un frontend può essere riscritto interamente mentre gli anelli restano intatti.

---

## Growth, Not Assembly / Crescita, Non Assemblaggio

The fundamental principle. Software is not a machine built from parts on an assembly line. Software is a living system that grows from the inside out. Each new capability emerges from what already exists, drawing strength from it, reinforcing it. You do not bolt on a new module — you grow a new ring. The difference is not poetic. It is structural: assembled parts need connectors, grown rings are already one.

Il principio fondamentale. Il software non è una macchina costruita da pezzi su una catena di montaggio. Il software è un sistema vivente che cresce dall'interno verso l'esterno. Ogni nuova capacità emerge da ciò che già esiste, traendone forza, rafforzandolo. Non si imbullona un nuovo modulo — si cresce un nuovo anello. La differenza non è poetica. È strutturale: i pezzi assemblati hanno bisogno di connettori, gli anelli cresciuti sono già una cosa sola.

---

*This vocabulary is a living document. New terms will emerge as the methodology grows — one ring at a time.*

*Questo vocabolario è un documento vivo. Nuovi termini emergeranno man mano che la metodologia cresce — un anello alla volta.*

---
