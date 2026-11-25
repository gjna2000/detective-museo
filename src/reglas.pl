% 1-3 Escena y acceso
estuvo_en_escena(P) :- hora_robo(H), objeto_robado(_, S), estuvo_en(P, S, H).
tenia_llave(P) :- objeto_robado(_, S), tiene_llave(P, S).
tenia_acceso(P) :- tenia_llave(P).
tenia_acceso(P) :- tiene_llave(P, S), conectada(S, Sala), objeto_robado(_, Sala).

% 4-5 Coartadas
sin_coartada(P) :- persona(P), \+ coartada(P, _).
coartada_falsa(P) :-
    coartada(P, T), hora_robo(H), estuvo_en(P, S, H),
    \+ estuvo_en(T, S, H).

% 6-8 Motivos
tenia_motivo(P) :- motivo(P, _).
deuda_economica(P) :- motivo(P, deuda).
rencor_con_museo(P) :- motivo(P, rencor).

% 9-11 Conocimiento
conocia_el_valor(P) :- conoce_valor(P).
experto_en_seguridad(P) :- experto_seguridad(P).
conocia_horario_guardia(P) :- sabe_horario_guardia(P).

% 12-15 Pruebas y conducta
huella_en_vitrina(P) :- huella(P, vitrina).
testigo_lo_vio(P) :- testigo_vio(_, P, S, H), hora_robo(H), objeto_robado(_, S).
mintio(P) :- declaro_estar(P, S, H), \+ estuvo_en(P, S, H).
comportamiento_sospechoso(P) :- mintio(P) ; coartada_falsa(P).

% 16-17 Oportunidad y medios
tenia_oportunidad(P) :- estuvo_en_escena(P), ( sin_coartada(P) ; coartada_falsa(P) ).
tenia_medios(P) :- tenia_acceso(P), conocia_el_valor(P).

% 18-19 Cómplices y descartados
complice(P1, P2) :-
    ( relacion(P1, P2, _) ; relacion(P2, P1, _) ),
    estuvo_en_escena(P1), tenia_motivo(P2), \+ estuvo_en_escena(P2).
descartado(P) :- persona(P), \+ tenia_motivo(P), \+ comportamiento_sospechoso(P).

% 20-21 Puntaje y sospechoso principal
indicio(P, 2) :- tenia_motivo(P).
indicio(P, 2) :- tenia_medios(P).
indicio(P, 2) :- tenia_oportunidad(P).
indicio(P, 1) :- huella_en_vitrina(P).
indicio(P, 1) :- testigo_lo_vio(P).
indicio(P, 1) :- mintio(P).
indicio(P, 1) :- coartada_falsa(P).
indicio(P, 1) :- conocia_horario_guardia(P).

puntaje_sospecha(P, Total) :-
    persona(P),
    findall(Pts, indicio(P, Pts), L),
    sum_list(L, Total).

sospechoso_principal(P) :-
    puntaje_sospecha(P, Max),
    \+ ( puntaje_sospecha(_, Otro), Otro > Max ).

% 22 Culpable
culpable(P) :- tenia_motivo(P), tenia_medios(P), tenia_oportunidad(P).