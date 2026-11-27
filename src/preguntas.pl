:- encoding(utf8).
% preguntas.pl - Entiende preguntas en español (DCG) y responde con la base de conocimiento

% ---------- 1. Normalizar el texto ----------
normalizar(Texto, Tokens) :-
    string_lower(Texto, Min),
    string_chars(Min, Cs),
    maplist(plano, Cs, Ps),
    string_chars(Plano, Ps),
    split_string(Plano, " ,.;:¿?¡!", " ", Partes),
    exclude(==(""), Partes, Utiles),
    maplist(atom_string, Tokens, Utiles).

plano(C, P) :- ( acento(C, A) -> P = A ; P = C ).
acento('á', a). acento('é', e). acento('í', i). acento('ó', o).
acento('ú', u). acento('ü', u). acento('ñ', n).

% ---------- 2. Gramática (DCG): qué quiere saber el detective ----------
resto --> [].
resto --> [_], resto.

% una pregunta "contiene" una palabra que empieza con alguna de las raíces
clave(Raices) --> resto, [T], { member(R, Raices), sub_atom(T, 0, _, _, R) }, resto.

pregunta(saludo)    --> clave([hola, buenas, buenos, saludos]).
pregunta(uniforme)  --> clave([uniform, ropa, vestia, vestid]).
pregunta(huella)    --> clave([huella, vitrina, dedo]).
pregunta(llave)     --> clave([llave, acceso, abrir, entrar]).
pregunta(motivo)    --> clave([motivo, deuda, dinero, plata, rencor, odi, ambic, razon]).
pregunta(vio)       --> clave([vio, viste, raro, notaste, observ, escuch, presenci]).
pregunta(coartada)  --> clave([coartada, confirm, respald, acompan, solo, sola, testig]).
pregunta(ubicacion) --> clave([donde, estaba, estabas, estuvo, estuviste, ubic, lugar, sala]).
pregunta(relacion)  --> clave([conoc, amig, relacion, cercan]).
pregunta(sospecha)  --> clave([sospech, culpable, ladron, roba]).
pregunta(robo)      --> clave([robo, copa, trofeo, desaparec]).

% ---------- 3. Respuestas desde la base de conocimiento ----------
respuesta(P, ubicacion, T) :-
    hora_robo(H),
    (   declaro_estar(P, S, H) -> true
    ;   estuvo_en(P, S, H)
    ), !,
    lugar(S, B),
    format(atom(T), 'A las ~w:00 estaba en ~w.', [H, B]).
respuesta(_, ubicacion, 'No recuerdo bien dónde estaba.').

respuesta(P, coartada, T) :-
    coartada(P, Q), !, nombre(Q, N),
    format(atom(T), '~w puede confirmarlo.', [N]).
respuesta(_, coartada, 'No tengo a nadie que pueda confirmarlo.').

respuesta(P, uniforme, 'Sí, hoy llevo el uniforme del museo.') :- uniforme(P), !.
respuesta(_, uniforme, 'No, hoy no llevo uniforme.').

respuesta(P, huella, 'Es posible que mi huella esté ahí; paso seguido por esa sala.') :-
    huella(P, vitrina), !.
respuesta(_, huella, 'Yo nunca he tocado esa vitrina.').

respuesta(P, llave, T) :-
    findall(B, ( tiene_llave(P, S), lugar(S, B) ), L), L \== [], !,
    atomic_list_concat(L, ' y ', Ls),
    format(atom(T), 'Tengo llave de ~w.', [Ls]).
respuesta(_, llave, 'No tengo llaves de esas salas.').

respuesta(P, motivo, 'Debo dinero, no lo niego, pero eso no me convierte en ladrón.') :- motivo(P, deuda), !.
respuesta(P, motivo, 'Tengo diferencias con el museo, sí, pero no robaría nada.')      :- motivo(P, rencor), !.
respuesta(P, motivo, 'Quiero crecer en mi carrera, nada más.')                         :- motivo(P, ambicion), !.
respuesta(_, motivo, 'No tengo ningún motivo para robar esa copa.').

respuesta(P, vio, T) :-
    testigo_vio(P, _, S, H), !, lugar(S, B),
    format(atom(T), 'A las ~w:00 vi a alguien con uniforme del museo en ~w, pero no distinguí quién era.', [H, B]).
respuesta(_, vio, 'No vi nada raro esa noche.').

respuesta(P, relacion, T) :-
    findall(N, ( ( relacion(P, Q, _) ; relacion(Q, P, _) ), nombre(Q, N) ), L), L \== [], !,
    atomic_list_concat(L, ' y ', Ls),
    format(atom(T), 'Tengo amistad con ~w.', [Ls]).
respuesta(_, relacion, 'No tengo relaciones cercanas con los demás.').

respuesta(_, sospecha, 'Yo no fui, detective, y no me gusta acusar a nadie sin pruebas.').
respuesta(_, robo, 'La Copa de Oro desapareció de la sala de trofeos a las 8:00 p. m.').
respuesta(_, saludo, 'Buenas, detective. Pregunte lo que necesite.').
respuesta(_, desconocida, 'No le entendí bien. Pregúnteme por dónde estaba, mi coartada, uniforme, llaves, motivos o qué vi.').

nombre(Id, N) :- ficha(Id, N, _), !.
nombre(Id, Id).
lugar(sala_trofeos, 'la sala de trofeos') :- !.
lugar(bodega, 'la bodega') :- !.
lugar(oficina, 'la oficina') :- !.
lugar(entrada, 'la entrada') :- !.
lugar(S, B) :- atomic_list_concat(Ps, '_', S), atomic_list_concat(Ps, ' ', B).

% ---------- 4. Punto de entrada ----------
responder(P, Texto, Intenciones, Respuesta) :-
    normalizar(Texto, Tokens),
    findall(I, phrase(pregunta(I), Tokens), L),
    list_to_set(L, Set),
    (   Set == [] -> Intenciones = [desconocida] ; Intenciones = Set ),
    findall(R, ( member(I, Intenciones), respuesta(P, I, R) ), Rs),
    atomic_list_concat(Rs, ' ', Respuesta).
