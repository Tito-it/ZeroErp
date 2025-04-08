Zero ERP - Open Source ERP Framework
Licenza: GPL v3

✅ Cos'è Zero ERP
Zero ERP è un sistema gestionale ERP open-source, flessibile e modulare, pensato per:
    • Utility (Gas, Energia, Acqua)
    • Multi-servizi
    • Fatturazione e Gestione Commerciale
    • Piccole, Medie e Grandi aziende
Obiettivi
    • Creare una base ERP scalabile e configurabile
    • Fornire un framework moderno per progetti verticali
    • Supportare esigenze standard e di settore

✅ Tecnologie utilizzate
    • Python (Django)
    • PostgreSQL (JSONB, GIS ready)
    • Vue.js (Frontend)
    • Docker + CI/CD
    • Autenticazione JWT, crittografia avanzata

✅ Funzionalità previste
    • Anagrafiche Generali
    • Gestione multi-indirizzo avanzata
    • Gestione multi-servizio
    • Moduli: Fatturazione, Contratti, Forniture, POD/PDR, Cabine REMI
    • Sistema Permessi e Menu dinamico avanzato
    • Multi-livello di configurazione (Globale, Cliente, Utente)

✅ Come contribuire
Requisiti
    • Conoscenza di Python e Django
    • Familiarità con Database Relazionali (PostgreSQL preferibile)
    • Esperienza base con Vue.js (o volontà di imparare)
Modalità
    1. Fork del repository
    2. Creazione branch personale
    3. Creazione di Pull Request
    4. Revisione da parte del team di sviluppo
Per suggerimenti o problemi, aprire una Issue.

✅ Community e Supporto
    • Documentazione su GitBook
    • Roadmap pubblica
    • Issue Tracker GitHub aperto
Per proposte e collaborazioni:
    • Referente: [inserire nome]
    • Email: [inserire email]

✅ Codice di Condotta
Tutti i partecipanti sono tenuti a rispettare le regole di collaborazione, educazione e condivisione open-source.






---
description: Documentazione Zero solution
---





# Zero

## 📘 Documentazione Ufficiale Progetto Zero ERP (in definizione)

### Introduzione

Il progetto **Zero** è un ERP multiservizi ideato per rappresentare un punto di ripartenza personale e professionale, caratterizzato da modularità, flessibilità, precisione operativa e chiarezza nella gestione dei dati aziendali.

### 📖 Documentazione Descrittiva

#### Obiettivi del Progetto

* Fornire una piattaforma ERP robusta, modulare e flessibile.
* Centralizzare e storicizzare informazioni critiche.
* Consentire la gestione di molteplici servizi (gas, energia, acqua, telefonia, standard).
* Garantire massima efficienza operativa e precisione gestionale.
* Facilitare l'integrazione con sistemi esterni, enti regolatori e normative (es. ARERA).
* Favorire semplicità d'uso, rapidità di consultazione e ricerca dei dati.

#### Concetti Fondamentali

* **Anagrafica Generale:** centralizzazione obbligatoria di tutti i soggetti (persone fisiche e giuridiche), ciascuno con almeno un ruolo specificato (cliente, fornitore, distributore, gestore software unico obbligatorio).
* **Ruoli Specifici:** creazione di tabelle dedicate con dati specifici per ciascun ruolo (es. distributore, società, contatti aziendali).
* **Forniture:** ogni servizio, inclusi quelli standard, è obbligatoriamente associato a una fornitura, luogo fisico indipendente, censito con indirizzo specifico.
* **Servizi:** gestione multisettoriale unificata, con servizi di default e storicizzazione completa.
* **Contratti:** definizione chiara e storicizzazione di contratti e offerte commerciali.
* **Centralizzazione Indirizzi:** gestione centralizzata e obbligatoria di tutti gli indirizzi, classificati per tipo (residenza, fornitura, domicilio fiscale, spedizione).

#### Benefici Concreti

* Centralizzazione e chiarezza gestionale.
* Facile reperimento delle informazioni.
* Conformità normativa facilitata.
* Alta flessibilità e modularità.

### ⚙️ Documentazione Tecnica Completa

#### Struttura Database Completa

**Anagrafica Generale**

\| id\_anagrafica | ragione\_sociale | tipo\_soggetto | nome | cognome | codice\_fiscale | partita\_iva | data\_nascita | id\_comune\_nascita | genere | codice\_fiscale\_forzato | note\_cf |

**Anagrafica Società Storico**

\| id | id\_anagrafica | forma\_giuridica | capitale\_sociale | REA | PEC | codice\_SDI | data\_costituzione | data\_inizio\_validita | data\_fine\_validita | note |

**Tabelle Ruoli Specifici**

* Clienti
* Fornitori
* Agenti
* Distributori (codice distributore, nr pronto intervento)
* Gestore Software (unico obbligatorio)
* Contatti aziendali (nome, cognome, titolo, ruolo aziendale, telefono, email)

**Contatti Anagrafica**

\| id\_contatto | id\_anagrafica | tipo\_contatto | valore\_contatto | note |

**Indirizzi**

\| id\_indirizzo | tipo\_indirizzo | toponomastica | nome\_via | numero\_civico | piano | interno | id\_comune | id\_provincia | id\_stato | zip\_code | indirizzo\_completo\_libero | indirizzo\_libero | note |

**Comuni e Province**

* Comuni: nome, cap, codice\_istat, codice\_catastale
* Province: nome, sigla, regione

**Stati**

\| id\_stato | nome\_stato | codice\_iso2 | codice\_iso3 |

**Forniture**

\| id\_fornitura | codice\_fornitura | id\_indirizzo | tipo\_fornitura | id\_pod\_pdr | data\_attivazione | data\_cessazione | note |

**Servizi**

\| id\_servizio | codice | descrizione | default\_servizio | note |

**Clienti (Servizi-Clienti-Forniture)**

\| id\_cliente | id\_anagrafica | id\_fornitura | id\_servizio | codice\_cliente | data\_inizio\_servizio | data\_fine\_servizio | stato | note |

**Contratti**

\| id\_contratto | id\_cliente | codice\_contratto | tipologia\_contratto | id\_offerta | id\_listino | data\_inizio\_contratto | data\_fine\_contratto | condizioni\_particolari | note |

**Cabine REMI**

\| id\_cabina | id\_distributore | codice | descrizione | indirizzo | data\_attivazione | data\_disattivazione | note |

**POD/PDR**

\| id\_pod\_pdr | id\_distributore | codice\_pod\_pdr | tipo | id\_indirizzo | stato | data\_attivazione | data\_cessazione | note |

**Distributori**

\| id\_distributore | id\_anagrafica | codice\_distributore | nr\_pronto\_intervento | note |

#### Tabelle di Collegamento

* Anagrafica indirizzi (storico indirizzi soggetti)
* Cabine REMI - Comuni/Vie

#### Popolamento Tabelle (Esempi)

* Anagrafica: Rossi Mario (fisico), Energia S.p.A. (giuridico)
* Forniture: FORN001, indirizzo specifico
* Servizi: DEFAULT, GAS
* Clienti e Contratti: esempi concreti con codice contratto
* Cabine REMI, POD/PDR: esempi censiti

### 📚 Appendice

* Glossario termini ERP e Utility
* Riferimenti normativi (es. ARERA)

***

### Conclusioni importanti

Questo documento rappresenta la sintesi completa di tutte le considerazioni e scelte fatte per il progetto Zero ERP. Esso costituisce il riferimento ufficiale per sviluppatori, collaboratori e partner di progetto, garantendo coerenza operativa e tecnica durante tutta la vita del progetto.
