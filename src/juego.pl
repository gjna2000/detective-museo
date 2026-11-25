:- [hechos, reglas].

:- initialization(main).

main :-
    write('=== Detective del Museo ==='), nl,
    write('Escribe: ?- jugar.'), nl.


% ===== PASO 1: INTERROGAR =====
interrogar(P) :-
    persona(P), !,
    registrar(P),
    hora_robo(H),
    format('~n=== Interrogatorio a ~w ===~n', [P]),
    version_ubicacion(P, H),
    version_coartada(P),
    version_uniforme(P),
    testimonio_de(P).
interrogar(P) :-
    format('No conozco a ~w.~n', [P]),
    write('Sospechosos: director, guardia, restauradora, guia, donante, conserje.'), nl.

% Lo que la persona DICE (puede ser mentira)
version_ubicacion(P, H) :-
    declaro_estar(P, S, H), !,
    format('Dice que a las ~w:00 estaba en ~w.~n', [H, S]).
version_ubicacion(P, H) :-
    estuvo_en(P, S, H), !,
    format('Dice que a las ~w:00 estaba en ~w.~n', [H, S]).
version_ubicacion(_, _) :-
    write('Dice que no recuerda dónde estaba.'), nl.

version_coartada(P) :-
    coartada(P, T), !,
    format('Afirma que ~w puede confirmarlo.~n', [T]).
version_coartada(_) :-
    write('No tiene a nadie que confirme su versión.'), nl.

version_uniforme(P) :-
    uniforme(P), !,
    write('Hoy lleva el uniforme del museo.'), nl.
version_uniforme(_) :-
    write('Hoy no lleva uniforme.'), nl.

testimonio_de(P) :-
    testigo_vio(P, _, S, H), !,
    format('Cuenta: "A las ~w:00 vi a alguien con uniforme del museo en la ~w, pero no distinguí quién era."~n', [H, S]),
    ( testimonio(P, S, H) -> true ; assertz(testimonio(P, S, H)) ).
testimonio_de(_).


% ===== MEMORIA DEL JUEGO =====
:- dynamic interrogado/1, escena_revisada/0, huella_analizada/0, testimonio/3.
registrar(P) :- interrogado(P), !.
registrar(P) :- assertz(interrogado(P)).

% ===== REVISAR ESCENA (sin nombres) =====
revisar_escena :-
    nl, write('Revisas la sala de trofeos...'), nl,
    write('- La vitrina está abierta, sin señales de fuerza.'), nl,
    write('- Hay una huella parcial en el cristal (sin analizar).'), nl,
    write('- La puerta de la bodega estaba sin seguro.'), nl,
    ( escena_revisada -> true ; assertz(escena_revisada) ).

% ===== ANALIZAR HUELLA =====
analizar_huella :-
    escena_revisada, !,
    nl, write('El laboratorio compara la huella con el personal...'), nl,
    forall(huella(P, vitrina), format('- Coincide con ~w.~n', [P])),
    write('Una huella no prueba un robo: compara con las versiones.'), nl,
    ( huella_analizada -> true ; assertz(huella_analizada) ).
analizar_huella :-
    write('Primero debes revisar la escena.'), nl.

% ===== CUADERNO =====
pistas :-
    nl, write('=== Cuaderno del detective ==='), nl,
    (   escena_revisada
    ->  write('- Escena: vitrina abierta sin forzar, huella parcial y puerta de la bodega sin seguro.'), nl
    ;   write('Aún no has revisado la escena.'), nl
    ),
    forall(( huella_analizada, huella(P, vitrina) ),
           format('- Huella analizada: coincide con ~w.~n', [P])),
    forall(testimonio(T, S, H),
           format('- ~w vio a alguien con uniforme en ~w a las ~w:00 (sin identificar).~n', [T, S, H])),
    findall(Q, interrogado(Q), L),
    (   L == []
    ->  write('Aún no has interrogado a nadie.'), nl
    ;   forall(member(Q, L), resumen(Q))
    ).

resumen(P) :-
    hora_robo(H),
    (   declaro_estar(P, S, H) -> true
    ;   estuvo_en(P, S, H)     -> true
    ;   S = desconocido
    ),
    ( coartada(P, T) -> true ; T = nadie ),
    ( uniforme(P) -> U = si ; U = no ),
    format('- ~w: dice que estaba en ~w; coartada: ~w; uniforme: ~w.~n', [P, S, T, U]).

% ===== PASO 3: ACUSAR =====
acusar(P) :-
    persona(P), !,
    format('~nAcusas a ~w...~n', [P]),
    (   culpable(P)
    ->  format('¡Correcto! ~w es el culpable.~n', [P]),
        explicar(P)
    ;   format('Incorrecto: ~w no es el culpable.~n', [P]),
        write('Sigue investigando.'), nl
    ).
acusar(_) :- write('Esa persona no existe.'), nl.

explicar(P) :-
    write('Razones:'), nl,
    ( deuda_economica(P)   -> write('- Tenía una deuda (motivo).'), nl ; true ),
    ( tenia_acceso(P)      -> write('- Tenía acceso a la sala de trofeos.'), nl ; true ),
    ( conocia_el_valor(P)  -> write('- Conocía el valor de la copa.'), nl ; true ),
    ( estuvo_en_escena(P)  -> write('- Estuvo en la escena a la hora del robo.'), nl ; true ),
    ( mintio(P)            -> write('- Mintió sobre dónde estaba.'), nl ; true ),
    ( huella_en_vitrina(P) -> write('- Dejó su huella en la vitrina.'), nl ; true ),
    ( testigo_lo_vio(P)    -> write('- Un testigo lo vio en la sala.'), nl ; true ),
    puntaje_sospecha(P, N),
    format('Puntaje de sospecha: ~w~n', [N]).

% ===== AVATAR, MAPA E INTRO =====
avatar :-
    nl,
    write('    .-------.   '), nl,
    write('   | o     o |  '), nl,
    write('   |    ^    |  '), nl,
    write('   |  =====  |  '), nl,
    write('    ---------   '), nl,
    write('    DETECTIVE   '), nl.

intro :-
    nl,
    write('La Copa de Oro desapareció de la sala de trofeos a las 8:00 p. m.'), nl,
    write('Hay 6 sospechosos. Tú eres el detective.'), nl.

mapa :-
    nl,
    write('+-----------+-----------+'), nl,
    write('|  OFICINA  |  SALA DE  |'), nl,
    write('| (director)| TROFEOS   |'), nl,
    write('+-----------+  (copa)   |'), nl,
    write('|  BODEGA   |           |'), nl,
    write('+-----------+-----------+'), nl,
    write('|        ENTRADA        |'), nl,
    write('+-----------------------+'), nl,
    write('La bodega conecta con la sala de trofeos.'), nl.

% ===== PASO 4: MENÚ =====
jugar :-
    retractall(interrogado(_)),
    retractall(escena_revisada),
    retractall(huella_analizada),
    retractall(testimonio(_, _, _)),
    avatar, intro, menu.

leer_linea(Texto) :-
    read_line_to_string(user_input, S),
    (   S == end_of_file -> Texto = "0"
    ;   normalize_space(string(Texto), S)
    ).

menu :-
    nl, write('--- MENÚ ---'), nl,
    write('1. Revisar la escena'), nl,
    write('2. Interrogar a un sospechoso'), nl,
    write('3. Ver mi cuaderno de pistas'), nl,
    write('4. Ver el mapa del museo'), nl,
    write('5. Acusar'), nl,
    write('6. Analizar la huella'), nl,
    write('0. Salir'), nl,
    write('Elige una opción: '),
    leer_linea(Op),
    opcion(Op).

opcion("1") :- !, revisar_escena, menu.
opcion("2") :- !,
    write('¿A quién interrogas? (director, guardia, restauradora, guia, donante, conserje): '),
    leer_linea(T), downcase_atom(T, P),
    interrogar(P), menu.
opcion("3") :- !, pistas, menu.
opcion("4") :- !, mapa, menu.
opcion("5") :- !,
    write('¿A quién acusas? '),
    leer_linea(T), downcase_atom(T, P),
    acusar(P),
    (   culpable(P)
    ->  nl, write('Caso resuelto. ¡Buen trabajo, detective!'), nl
    ;   menu
    ).
opcion("6") :- !, analizar_huella, menu.
opcion("0") :- !, write('Caso cerrado. ¡Hasta pronto, detective!'), nl.
opcion(_) :- write('Opción no válida.'), nl, menu.