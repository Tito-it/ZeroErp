// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: setup di Vitest (`setupFiles` in `vite.config.js`). Nell'app le
//        misure «righe per pagina» le carica il guard del router dal DB;
//        un test non ha ne' guard ne' backend, quindi le FABBRICA qui, prima
//        di ogni file.
// ⚠️ Sono dati di prova, non una copia del catalogo: i test dichiarano l'USO
//    (`misuraDefault(USO_MISURA.COMPATTA)`) e non scrivono il numero, quindi
//    restano veri qualunque cosa dica il CSV. Il BB stesso — lettura prima
//    del caricamento, risposta malformata — lo prova `misurePagina.spec.js`
//    su un modulo fresco, senza questo setup.
// ------------------------------------------------------------

import { registraMisurePagina } from './misurePagina'

registraMisurePagina({ misure: [10, 25, 50, 100], default_compatta: 10, default_pagina: 25 })
